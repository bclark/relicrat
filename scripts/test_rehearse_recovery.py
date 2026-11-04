"""Replacement rehearsal refuses existing/online environments before mutation."""
import importlib.util
from pathlib import Path
import unittest
import subprocess
from unittest.mock import patch
s=importlib.util.spec_from_file_location('rehearsal',Path(__file__).with_name('rehearse-recovery.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)


class RecoveryGuardTests(unittest.TestCase):
    def probe(self,args):
        if args[-1]=='{{.ID}}':return 'fresh-id'
        if args[-1]=='{{.Name}}':return 'fresh-recovery'
        if args[0]=='ip':return '[]'
        return ''

    def test_wrong_identity_and_live_worker_are_rejected(self):
        with patch.object(r,'output',side_effect=self.probe),self.assertRaises(ValueError):r.guard('different-id')
        with patch.object(r,'output',side_effect=lambda a:'relicrat-worker' if a[-1]=='{{.Name}}' else self.probe(a)),self.assertRaises(ValueError):r.guard('fresh-id')

    def test_any_existing_image_container_or_volume_is_rejected(self):
        for target in [['image','ls','-aq'],['ps','-aq'],['volume','ls','-q']]:
            with self.subTest(target=target),patch.object(r,'output',side_effect=lambda a:'existing' if a[-len(target):]==target else self.probe(a)),self.assertRaises(ValueError):r.guard('fresh-id')

    def test_either_external_default_route_is_rejected(self):
        for family in ['v4','v6']:
            def probe(args):
                if args[0]=='ip' and (('-6' in args)==(family=='v6')):return '[{"dst":"default"}]'
                return self.probe(args)
            with self.subTest(family=family),patch.object(r,'output',side_effect=probe),self.assertRaises(ValueError):r.guard('fresh-id')

    def test_unhealthy_database_blocks_api_and_web_startup(self):
        with patch.object(r.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['synthetic-db-health'])) as run,self.assertRaises(subprocess.CalledProcessError):
            r.start_private_services(['synthetic-compose'])
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0],['synthetic-compose','up','-d','--wait','db'])

    def test_empty_offline_replacement_is_accepted(self):
        with patch.object(r,'output',side_effect=self.probe):self.assertIsNone(r.guard('fresh-id'))


if __name__=='__main__':unittest.main()
