# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Read explicit original notice/source members without extracting source trees.

Source archives may legitimately contain links, Unix paths and test fixtures.
Nothing is extracted or executed; only named regular members are read. A notice
excerpt retains an exact full source-member hash and an explicit byte range.
"""
import hashlib
import stat
import tarfile
import zipfile
from files import file_record, _checked_path, _regular_stream


def require(value,message):
    if not value:raise ValueError(message)


def digest(data):
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def read_members(path,expected,members):
    require(file_record(path)==expected,'Preferred-source archive differs from fixed size/hash')
    require(isinstance(members,list) and 0<len(members)<=1024 and len(set(members))==len(members),'No unique bounded source members selected')
    for name in members:_checked_path(name)
    wanted=set(members);found={};total=0
    def retain(name,size,regular,reader):
        nonlocal total
        if name not in wanted:return
        require(name not in found,'Duplicate selected source member: '+name)
        require(regular,'Selected source member is not regular: '+name)
        require(0<=size<=16*1024*1024,'Oversized selected source member: '+name)
        total+=size
        require(total<=64*1024*1024,'Selected source bytes exceed bound')
        with reader() as stream:data=stream.read(size+1)
        require(len(data)==size,'Truncated selected source member: '+name)
        found[name]=data
    with _regular_stream(path) as stream:
        if zipfile.is_zipfile(stream):
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                entries=archive.infolist()
                require(len(entries)<=100000,'Source archive member count exceeds bound')
                for entry in entries:
                    mode=stat.S_IFMT(entry.external_attr>>16)
                    retain(entry.filename,entry.file_size,not entry.is_dir() and mode in (0,stat.S_IFREG) and not entry.flag_bits&1,
                           lambda e=entry:archive.open(e))
        else:
            stream.seek(0)
            with tarfile.open(fileobj=stream,mode='r:*') as archive:
                for count,entry in enumerate(archive,1):
                    require(count<=100000,'Source archive member count exceeds bound')
                    retain(entry.name,entry.size,entry.isfile(),lambda e=entry:archive.extractfile(e))
    require(set(found)==wanted,'Missing exact preferred-source member')
    require(file_record(path)==expected,'Preferred-source archive changed during observation')
    return found


def notice_bytes(members,record):
    require(record['member'] in members,'Notice source member absent')
    data=members[record['member']]
    require(digest(data)==record['sourceMember'],'Notice original source member hash differs')
    offset,length=record['offset'],record['length']
    require(type(offset) is int and type(length) is int and offset>=0 and length>0 and offset+length<=len(data),'Invalid original notice byte range')
    notice=data[offset:offset+length]
    require(digest(notice)==record['notice'],'Original notice bytes differ')
    return notice
