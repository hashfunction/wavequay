# SPDX-License-Identifier: GPL-3.0-only
import copy
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'distribution/msix'))
from source_archives import digest


class SourceDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('source_delivery'), 'Exact current preferred-source acquisition absent')
        import source_delivery
        self.m=source_delivery
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.data=b'original preferred-source fixture archive'
        self.row=dict(component='owned',subdir='owned',filename='owned.tar.gz',origin='https://original.example/owned.tar.gz',
                      url=self.m.ASSET_BASE+'owned.tar.gz',**digest(self.data))
        self.calls=[]

    def opener(self,request,timeout):
        self.calls.append((request,timeout))
        class Response(io.BytesIO):
            status=200
            def geturl(self):return 'https://release-assets.githubusercontent.com/owned?opaque-download-token'
        return Response(self.data)

    def test_exact_anonymous_bounded_download_and_subsequent_no_network_cache_reuse(self):
        path=self.m.acquire_one(self.root,self.row,opener=self.opener)
        self.assertEqual(path.read_bytes(),self.data)
        self.assertEqual(len(self.calls),1)
        self.assertNotIn('Authorization',self.calls[0][0].headers)
        self.assertEqual(self.m.acquire_one(self.root,self.row,opener=self.opener),path)
        self.assertEqual(len(self.calls),1)

    def test_existing_owned_consumed_download_is_reused_without_copying_or_network(self):
        original=self.root/'.ci-dependency-cache/downloads/owned/owned.tar.gz';original.parent.mkdir(parents=True);original.write_bytes(self.data)
        self.assertEqual(self.m.acquire_one(self.root,self.row,opener=self.opener),original)
        self.assertEqual(self.calls,[])
        original.write_bytes(b'wrong cached current input')
        with self.assertRaises(ValueError):self.m.acquire_one(self.root,self.row,opener=self.opener)

    def test_foreign_url_alias_changed_truncated_or_oversized_source_is_never_retained_as_valid(self):
        original=copy.deepcopy(self.row)
        for mutation in (lambda r:r.update(url='https://example.org/foreign.tar.gz'),lambda r:r.update(filename='../owned.tar.gz'),
                         lambda r:r.update(component='../foreign'),lambda r:r.update(sha256='a'*64),
                         lambda r:r.update(bytes=r['bytes']-1),lambda r:r.update(bytes=r['bytes']+1)):
            self.row=copy.deepcopy(original);mutation(self.row)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.m.acquire_one(self.root,self.row,opener=self.opener)
        self.assertFalse((self.root/'.ci-dependency-cache/corresponding-source/owned.tar.gz').exists())

    def test_http_or_foreign_final_response_is_rejected(self):
        for url in ('http://release-assets.githubusercontent.com/owned','https://example.org/owned'):
            class Response(io.BytesIO):
                status=200
                def geturl(self):return url
            with self.subTest(url=url),self.assertRaises(ValueError):
                self.m.acquire_one(self.root,self.row,opener=lambda *args,**kwargs:Response(self.data))


if __name__=='__main__':unittest.main()
