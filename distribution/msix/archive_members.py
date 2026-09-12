# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Compare exact original binary-archive members using the existing CMake tool.

Only metadata and explicitly named regular files are read. Nothing in an
archive is executed. These archive facts alone are not source/license clearance.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata

from files import file_record, inventory_tree, _checked_path


def require(value, message):
    if not value:
        raise ValueError(message)


def quote(value):
    value=str(value)
    require(not any(c in value for c in ('\0', '\r', '\n', ']====]')), 'Unsafe CMake data argument')
    return '[====['+value+']====]'


def headers(text):
    require(len(text.encode('utf-8')) <= 8*1024*1024, 'Oversized original archive listing')
    entries={};aliases={}
    for line in text.splitlines():
        # CMake's LibArchive verbose list: mode links user group size day month
        # time-or-year path. A regular binary archive never needs link/device entries.
        row=re.fullmatch(r'([-dlhspcb][rwxStTs-]{9})\s+\d+\s+\S+\s+\S+\s+(\d+)\s+\d+\s+\S+\s+\S+\s+(.+)',line)
        require(row is not None, 'Unrecognized original archive member header: '+line[:240])
        mode,size,name=row.groups();is_directory=mode[0]=='d'
        require(mode[0] in ('-', 'd'), 'Original binary archive contains a link or special member')
        if is_directory and name.endswith('/'):
            name=name[:-1]
        _checked_path(name)
        require(';' not in name, 'Archive member is not a literal CMake pattern')
        key=unicodedata.normalize('NFC',name).casefold()
        require(key not in aliases, 'Duplicate or Windows-aliased original archive member')
        aliases[key]=name
        entries[name]=dict(directory=is_directory,bytes=int(size))
        require(len(entries)<=50000, 'Original binary archive member count exceeds bound')
    require(entries, 'Empty original binary archive listing')
    for name in entries:
        parts=name.split('/')
        for i in range(1,len(parts)):
            parent='/'.join(parts[:i]);key=unicodedata.normalize('NFC',parent).casefold()
            if key in aliases:
                actual=aliases[key]
                require(actual==parent and entries[actual]['directory'], 'Archive parent is a file or Windows alias')
    return entries


def cmake_record(path):
    path=Path(path)
    require(path.is_absolute() and path.name.lower() in ('cmake','cmake.exe'), 'Exact absolute CMake tool required')
    return dict(path=str(path),**file_record(path))


def invoke(cmake, tool, script, archive, expected_archive):
    require(cmake_record(cmake)==tool, 'CMake changed before original archive observation')
    require(file_record(archive)==expected_archive, 'Original archive changed before member observation')
    result=subprocess.run([str(cmake),'-P',str(script)],capture_output=True,text=True,encoding='utf-8',timeout=120)
    require(result.returncode==0, 'CMake original archive observation failed: '+result.stderr[-2000:])
    require(cmake_record(cmake)==tool and file_record(archive)==expected_archive, 'Original archive/tool changed during observation')
    return result.stdout


def verify_members(archive, expected_archive, members, cmake):
    archive,cmake=Path(archive),Path(cmake)
    require(file_record(archive)==expected_archive, 'Original archive hash/size differs from fixed input')
    require(isinstance(members,dict) and 0<len(members)<=2000, 'No bounded exact original members selected')
    require(sum(v['bytes'] for v in members.values())<=512*1024*1024, 'Selected original member bytes exceed bound')
    for name in members:
        _checked_path(name)
        require(';' not in name, 'Nonliteral original member pattern')
    tool=cmake_record(cmake)
    with tempfile.TemporaryDirectory(prefix='waveweft-member-') as td:
        temporary=Path(td).resolve();script=temporary/'read.cmake';output=temporary/'members'
        script.write_text('file(ARCHIVE_EXTRACT INPUT '+quote(archive.as_posix())+' LIST_ONLY VERBOSE)\n',encoding='utf-8')
        listing=headers(invoke(cmake,tool,script,archive,expected_archive))
        for name,value in members.items():
            require(name in listing and not listing[name]['directory'] and listing[name]['bytes']==value['bytes'],
                    'Exact original archive member absent/wrong size: '+name)
        script.write_text('file(ARCHIVE_EXTRACT INPUT '+quote(archive.as_posix())+' DESTINATION '+quote(output.as_posix())
                          +' PATTERNS '+' '.join(quote(name) for name in sorted(members))+')\n',encoding='utf-8')
        invoke(cmake,tool,script,archive,expected_archive)
        actual=inventory_tree(output)
        require(actual==members, 'Original archive member bytes/file set differ from current resolved inputs')
    return dict(archive=expected_archive,members=actual,tool=tool,listedMembers=len(listing))
