"""Synthetic status/incident and private HTTP boundary checks."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

s = importlib.util.spec_from_file_location('operations', Path(__file__).with_name('operations.py'))
ops = importlib.util.module_from_spec(s)
s.loader.exec_module(ops)


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.current = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)

    def receipt(self, **extra):
        r = {'status': 'verified-offhost-copy-and-disposable-restore', 'source_commit': 'a'*40, 'sha256':'b'*64, 'completed_at_utc': self.current.isoformat(), 'restore_verified': True, 'member_checksums_verified': True, 'saved_image_ids_verified': True, **extra}
        p = self.root/'receipt.json'
        p.write_text(json.dumps(r))
        return p

    def test_receipts_require_evidence_and_expire(self):
        p = self.receipt()
        self.assertEqual(ops.receipt_check('mac-backup', 'Mac', p, self.current)['state'], 'ok')
        self.assertEqual(ops.receipt_check('mac-backup', 'Mac', p, self.current+timedelta(hours=37))['state'], 'action')
        self.assertEqual(ops.receipt_check('mac-backup', 'Mac', p, self.current-timedelta(hours=1))['state'], 'unknown')
        for change in [{'restore_verified': False}, {'status': 'captured'}, {'completed_at_utc': 'invalid'}]:
            p = self.receipt(**change)
            self.assertEqual(ops.receipt_check('mac-backup', 'Mac', p, self.current)['state'], 'unknown')

    def test_cloud_copy_needs_actual_readback_not_just_an_upload(self):
        p = self.receipt(status='verified-offsite-parts')
        self.assertEqual(ops.receipt_check('cloud-backup', 'Drive', p, self.current)['state'], 'unknown')
        r = json.loads(p.read_text())
        r.update({k: True for k in ['all_downloaded_parts_verified', 'downloaded_manifest_verified', 'full_archive_sha256_verified', 'owner_only_metadata_verified', 'cms_authenticated_decryption_verified']})
        p.write_text(json.dumps(r))
        self.assertEqual(ops.receipt_check('cloud-backup', 'Drive', p, self.current)['state'], 'ok')

    def test_remote_snapshot_staleness_and_failed_probe_never_recover_a_check(self):
        remote = {'checked_at_utc': (self.current-timedelta(hours=1)).isoformat(), 'checks': [ops.check('app-services','App','ok','private')]}
        with patch.object(ops.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(remote).encode())):
            result = ops.collect({'remote_snapshot':['synthetic']}, self.current)
        self.assertEqual(result['checks'][0]['state'], 'action')
        self.assertEqual(result['checks'][1]['state'], 'unknown')
        out = self.root/'status.json'
        ops.record({'checked_at_utc':self.current.isoformat(),'checks':[ops.check('app-services','App','action','down')]}, out)
        ops.record({'checked_at_utc':self.current.isoformat(),'checks':[]}, out)
        self.assertEqual(ops.read_json(self.root/'incidents.json')['open']['app-services']['state'], 'unknown')

    def test_incidents_deduplicate_and_record_one_recovery(self):
        out = self.root/'status.json'
        def put(state):
            ops.record({'checked_at_utc':self.current.isoformat(),'checks':[ops.check('space','Storage',state,'changing detail')]}, out)
        put('action'); put('action')
        self.assertEqual(len(ops.read_json(self.root/'incidents.json')['changes']), 1)
        put('ok'); put('ok')
        self.assertEqual([x['state'] for x in ops.read_json(self.root/'incidents.json')['changes']], ['action', 'recovered'])
        self.assertEqual(out.stat().st_mode & 0o777, 0o600)

    def test_private_config_rejects_symlink_and_broad_permissions(self):
        p = self.root/'config.json'; p.write_text('{}'); p.chmod(0o644)
        with self.assertRaises(ValueError): ops.private_config(p)
        p.chmod(0o600)
        q = self.root/'link'; q.symlink_to(p)
        with self.assertRaises(ValueError): ops.private_config(q)

    def test_capture_receipt_cannot_hide_a_missing_or_changed_archive(self):
        (self.root/'archives').mkdir();p=self.root/'LATEST.json';r={'status':'encrypted-capture-awaiting-copied-restore','sha256':'a'*64,'archive':'synthetic.cms','bytes':9,'captured_at_utc':self.current.isoformat()};p.write_text(json.dumps(r))
        c={'capture_latest':str(p)}
        self.assertEqual(ops.collect(c,self.current)['checks'][0]['state'],'unknown')
        (self.root/'archives/synthetic.cms').write_bytes(b'synthetic')
        self.assertEqual(ops.collect(c,self.current)['checks'][0]['state'],'ok')
        (self.root/'archives/synthetic.cms').write_bytes(b'changed')
        self.assertEqual(ops.collect(c,self.current)['checks'][0]['state'],'unknown')

    def test_local_evidence_overrides_remote_copy_without_duplicate_rows(self):
        p=self.receipt(restore_verified=False)
        remote={'checked_at_utc':self.current.isoformat(),'checks':[ops.check('mac-backup','Old Mac proof','ok','older proof')]}
        with patch.object(ops.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(remote).encode())):
            result=ops.collect({'remote_snapshot':['synthetic'],'receipts':{'mac-backup':{'path':str(p),'label':'Mac'}}},self.current)
        rows=[c for c in result['checks'] if c['id']=='mac-backup']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['state'],'unknown')

    def test_latest_pointer_cannot_escape_approved_receipt_root(self):
        pointer=self.root/'latest.json';pointer.write_text(json.dumps({'receipt':'../outside.json'}))
        with self.assertRaises(ValueError):ops.receipt_path({'latest':str(pointer),'root':str(self.root)})
        target=self.receipt();pointer.write_text(json.dumps({'receipt':target.name}))
        self.assertEqual(ops.receipt_path({'latest':str(pointer),'root':str(self.root)}),target.resolve())

    def test_sync_excludes_personal_contents_paths_and_extra_fields(self):
        p=self.receipt(collection_contents='secret-data',owner_password='never-transfer')
        cloud=self.root/'cloud.json';r=json.loads(p.read_text());r['status']='verified-offsite-parts';r.update({k:True for k in ['all_downloaded_parts_verified','downloaded_manifest_verified','full_archive_sha256_verified','owner_only_metadata_verified','cms_authenticated_decryption_verified']});cloud.write_text(json.dumps(r))
        config={'receipts':{'mac-backup':{'path':str(p),'label':'Mac'},'cloud-backup':{'path':str(cloud),'label':'Drive'}},'evidence_root':'/private/synthetic','evidence_ssh':['synthetic']}
        with patch.object(ops.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run:
            ops.sync_evidence(config)
        code=run.call_args.kwargs['input'].decode()
        self.assertNotIn('secret-data',code);self.assertNotIn('never-transfer',code);self.assertNotIn('collection_contents',code)

    def test_http_has_only_fixed_routes_host_guard_and_no_config_disclosure(self):
        config = self.root/'config.json'; config.write_text('{}'); config.chmod(0o600)
        report = self.root/'report.html'; report.write_text('<h1>Synthetic report</h1>')
        output = self.root/'status.json'
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('operations.py')), 'serve', '--config',str(config),'--output',str(output),'--report',str(report)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.poll() is None and process.terminate())
        try:
            url = process.stdout.readline().strip().split('#')[0]
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url) as response: self.assertIn(b'Synthetic report', response.read())
            for suffix, code in [('config.json',404), ('../config.json',404)]:
                with self.assertRaises(urllib.error.HTTPError) as error: opener.open(url+suffix)
                self.assertEqual(error.exception.code, code)
                error.exception.close()
            request = urllib.request.Request(url, headers={'Host':'untrusted.invalid'})
            with self.assertRaises(urllib.error.HTTPError) as error: opener.open(request)
            self.assertEqual(error.exception.code,403)
            error.exception.close()
        finally:
            process.terminate(); process.wait(timeout=5)
            process.stdout.close(); process.stderr.close()


if __name__ == '__main__':
    unittest.main()
