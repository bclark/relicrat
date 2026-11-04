"""Generated capsules only; no collection data or working recovery keys."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

s=importlib.util.spec_from_file_location('capsule',Path(__file__).with_name('recovery-capsule.py'))
c=importlib.util.module_from_spec(s);s.loader.exec_module(c)


def archive(path, files):
    with tarfile.open(path,'w') as t:
        for name, data in files.items():
            item=tarfile.TarInfo(name);item.size=len(data);t.addfile(item,io.BytesIO(data))


class CapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.keys=Path(cls.temp.name)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=Synthetic test','-keyout',str(cls.keys/'key'),'-out',str(cls.keys/'cert')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.cap=self.root/'cap';self.cap.mkdir();(self.cap/'backup').mkdir()
        for name in ['database.dump','media.tar','state.json']:(self.cap/'backup'/name).write_bytes(b'synthetic')
        archive(self.cap/'source.tar',{'README.md':b'Synthetic source'})
        blob=b'{}';ident='sha256:'+hashlib.sha256(blob).hexdigest();self.images=dict.fromkeys(['api','db','web'],ident)
        archive(self.cap/'images.tar.gz',{'index.json':json.dumps({'manifests':[{'digest':ident}]}).encode(),'blobs/sha256/'+ident.split(':')[1]:blob})
        (self.cap/'image-ids.json').write_text(json.dumps(self.images));(self.cap/'backup/manifest.json').write_text(json.dumps({'api_image':ident,'db_image':ident,'files':{n:c.digest(self.cap/'backup'/n) for n in ['database.dump','media.tar','state.json']}}))
        self.seal()

    def seal(self):
        (self.cap/'capsule.json').write_text(json.dumps({'format':1,'source_commit':'a'*40,'owner_credentials_included':False,'files':{n:c.digest(self.cap/n) for n in c.MEMBERS-{'capsule.json'}}}))

    def encrypt(self, extra=None, cipher='-aes-256-gcm'):
        plain=self.root/'plain.tar';files={n:(self.cap/n).read_bytes() for n in c.MEMBERS};files.update(extra or {});archive(plain,files)
        encrypted=self.root/'encrypted.cms';subprocess.run(['openssl','cms','-encrypt','-binary',cipher,'-stream','-outform','DER','-in',str(plain),'-out',str(encrypted),str(self.keys/'cert')],check=True)
        return encrypted

    def decrypt(self, path):
        return c.decrypt(path,self.keys/'cert',self.keys/'key',self.root/'verified','a'*40)

    def test_authenticated_fixed_members_source_and_image_checks(self):
        path=self.encrypt();r=self.decrypt(path);self.assertEqual(r['images'],self.images);self.assertFalse((self.root/'verified/authenticated.tar').exists())

    def test_authentication_failure_never_opens_or_extracts_plaintext(self):
        path=self.encrypt();raw=bytearray(path.read_bytes());raw[-25]^=1;path.write_bytes(raw)
        with self.assertRaises(ValueError):self.decrypt(path)
        self.assertFalse((self.root/'verified/capsule').exists())

    def test_non_authenticated_encryption_is_refused_before_plaintext_staging(self):
        path=self.encrypt(cipher='-aes256')
        with self.assertRaisesRegex(ValueError,'authenticated CMS'):self.decrypt(path)
        self.assertFalse((self.root/'verified').exists())

    def test_broad_key_permissions_are_refused_before_decryption(self):
        path=self.encrypt();key=self.root/'public-key-copy';key.write_bytes((self.keys/'key').read_bytes());key.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'must be private'):
            c.decrypt(path,self.keys/'cert',key,self.root/'verified','a'*40)
        self.assertFalse((self.root/'verified').exists())

    def test_traversal_extra_files_and_symlinks_are_rejected(self):
        for name in ['../outside','owner.env']:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):self.decrypt(self.encrypt({name:b'never write'}))
                self.assertFalse((self.root/'outside').exists())
                import shutil
                shutil.rmtree(self.root/'verified')
        path=self.root/'links.tar'
        with tarfile.open(path,'w') as t:
            m=tarfile.TarInfo('link');m.type=tarfile.SYMTYPE;m.linkname='/tmp/never';t.addfile(m)
        with tarfile.open(path) as t:
            with self.assertRaises(ValueError):c.members(t)

    def test_inner_oci_digest_and_reviewed_source_are_independent_checks(self):
        with self.assertRaises(ValueError):c.validate(self.cap,'a'*40,'0'*64)
        ident=self.images['api'];archive(self.cap/'images.tar.gz',{'index.json':json.dumps({'manifests':[{'digest':ident}]}).encode(),'blobs/sha256/'+ident.split(':')[1]:b'corrupt'})
        self.seal()
        with self.assertRaisesRegex(ValueError,'OCI blob'):c.validate(self.cap,'a'*40)

    def test_checksum_or_missing_member_prevents_verification(self):
        (self.cap/'backup/database.dump').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'checksum'):c.validate(self.cap,'a'*40)
        (self.cap/'source.tar').unlink()
        with self.assertRaises(ValueError):c.validate(self.cap,'a'*40)


if __name__=='__main__':unittest.main()
