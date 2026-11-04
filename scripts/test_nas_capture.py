"""Fail-closed capture guards; no SSH or live data used."""
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).parent))
s=importlib.util.spec_from_file_location('nas',Path(__file__).with_name('nas-capture.py'));nas=importlib.util.module_from_spec(s);s.loader.exec_module(nas)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.root.chmod(0o700)
        (self.root/'archives').mkdir();(self.root/'runs').mkdir();(self.root/'certificate').write_bytes(b'synthetic public certificate')
        self.config={'root':str(self.root),'certificate':str(self.root/'certificate'),'certificate_sha256':nas.digest(self.root/'certificate'),'minimum_free_bytes':0,'source_commit':'a'*40}
        run=datetime.now(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')+'-aaaaaa'
        archive=self.root/'archives'/(run+'.tar.cms');archive.write_bytes(b'synthetic encrypted bytes')
        self.receipt={'run':run,'local_date':datetime.now(ZoneInfo('America/New_York')).date().isoformat(),'source_commit':'a'*40,'status':'encrypted-capture-awaiting-copied-restore','archive':archive.name,'sha256':nas.digest(archive)}
        (self.root/'LATEST.json').write_text(json.dumps(self.receipt))

    def test_same_day_reuses_only_exact_verified_capture_bytes(self):
        with patch.object(nas.subprocess,'run') as run:
            self.assertEqual(nas.capture(self.config),self.receipt)
        run.assert_not_called()

    def test_changed_bytes_source_certificate_or_receipt_refuse(self):
        for change in ['bytes','source','certificate','receipt']:
            with self.subTest(change=change):
                c=dict(self.config);r=dict(self.receipt)
                if change=='bytes':r['sha256']='0'*64
                if change=='source':c['source_commit']='b'*40
                if change=='certificate':c['certificate_sha256']='0'*64
                if change=='receipt':r['status']='failed'
                (self.root/'LATEST.json').write_text(json.dumps(r))
                with patch.object(nas.subprocess,'run') as run, self.assertRaises(ValueError):nas.capture(c)
                run.assert_not_called()

    def test_capacity_and_permissions_fail_before_worker_contact(self):
        c={**self.config,'minimum_free_bytes':10**30}
        with self.assertRaises(ValueError):nas.capture(c)
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):nas.capture(self.config)

    def test_concurrent_capture_is_rejected(self):
        with nas.lock(self.root):
            with self.assertRaises(BlockingIOError):
                with nas.lock(self.root):pass

    def test_wrong_worker_engine_and_bad_run_identity_fail_before_mutation(self):
        with patch.object(nas,'output',return_value='wrong-engine'), self.assertRaises(ValueError):nas.preflight({'engine':'expected'})
        with patch.object(nas,'preflight') as preflight, self.assertRaises(ValueError):nas.worker_capture({},'../../escape')
        preflight.assert_not_called()


if __name__=='__main__':unittest.main()
