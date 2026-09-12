# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Compare preferred Qt source with its original Windows source SPDX inventory.

The only content transformation observed is lossless LF to Windows CRLF; archive
bytes remain unchanged. Explicit release-generated/VCS metadata exceptions are
reported individually and cannot cover implementation, build or license files.
"""
import hashlib
from pathlib import PurePosixPath
import re
import tarfile
from files import file_record, _checked_path, _regular_stream
from source_archives import digest, require


def inventory(data):
    require(len(data)<=32*1024*1024,'Oversized original Qt source SPDX')
    text=data.decode('utf-8-sig')
    require(text.startswith('SPDXVersion: SPDX-2.1'),'Unrecognized original Qt source SPDX format')
    files={};current=None
    for line in text.splitlines():
        if line.startswith('FileName: '):
            name=line[10:].replace('\\','/')
            require(name.startswith('./'),'Original source inventory requires relative paths')
            name=name[2:];_checked_path(name)
            require(name not in files,'Duplicate original source inventory member')
            files[name]=None;current=name
        elif line.startswith('FileChecksum: '):
            match=re.fullmatch(r'FileChecksum: SHA1: ([0-9a-f]{40})',line)
            require(current is not None and files[current] is None and match,'Missing/duplicate/invalid original source hash')
            files[current]=match.group(1)
    require(0<len(files)<=100000 and all(files.values()),'Incomplete original source inventory')
    return files


def compare(archive,expected,prefix,spdx,exceptions):
    require(file_record(archive)==expected,'Preferred Qt source archive differs')
    _checked_path(prefix);require('/' not in prefix,'Expected one original source root')
    originals=inventory(spdx)
    require(isinstance(exceptions,dict),'Exact metadata exceptions required')
    for name,reason in exceptions.items():
        require(name in originals,'Unobserved source metadata exception')
        require((name=='.tag' and reason=='release-generated-tag') or
                (PurePosixPath(name).name in ('.gitignore','.gitattributes') and reason=='omitted-vcs-control'),
                'A metadata exception cannot hide source/build/license files')
    found={};total=0
    with _regular_stream(archive) as stream,tarfile.open(fileobj=stream,mode='r|*') as source:
        for count,entry in enumerate(source,1):
            require(count<=100000,'Qt source archive member count exceeds bound')
            if not entry.name.startswith(prefix+'/'):continue
            name=entry.name[len(prefix)+1:]
            if name not in originals:continue
            require(name not in found,'Duplicate original source archive member')
            require(entry.isfile() and 0<=entry.size<=64*1024*1024,'Original Qt source member is not bounded/regular')
            total+=entry.size;require(total<=1024*1024*1024,'Original Qt source comparison byte bound exceeded')
            with source.extractfile(entry) as member:data=member.read(entry.size+1)
            require(len(data)==entry.size,'Truncated original Qt source member')
            sha=originals[name]
            form='exact' if hashlib.sha1(data).hexdigest()==sha else (
                'lf-to-crlf' if b'\r' not in data and hashlib.sha1(data.replace(b'\n',b'\r\n')).hexdigest()==sha else 'different')
            found[name]=form
    actual={}
    for name in originals:
        if name not in found:
            require(exceptions.get(name)=='omitted-vcs-control','Required original source member missing: '+name)
            actual[name]=exceptions[name]
        elif found[name]=='different':
            require(exceptions.get(name)=='release-generated-tag','Original source member bytes differ: '+name)
            actual[name]=exceptions[name]
    require(actual==exceptions,'Source metadata exceptions differ from reviewed observations')
    exact=sum(v=='exact' for v in found.values());crlf=sum(v=='lf-to-crlf' for v in found.values())
    require(exact+crlf>0,'No original source files compared')
    require(file_record(archive)==expected,'Preferred Qt source archive changed during comparison')
    return dict(archive=expected,originalSourceSpdx=digest(spdx),comparedFiles=exact+crlf,
                exactFiles=exact,lfToCrlfFiles=crlf,exceptions=actual)
