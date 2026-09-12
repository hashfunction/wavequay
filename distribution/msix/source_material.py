# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Generate exact unchanged notices and source instructions for both identities.

Package generation identifies source locations without claiming that current
application source, original binaries or installed workflows already passed the
independent final release gate.
"""
import json
from pathlib import Path
import re

from files import file_record, inventory_tree, _register_path
from source_archives import digest
from source_catalog import CATALOG, read_owned, require
from source_publication import verify_publication
from microsoft_notices import verify as verify_microsoft

SUBMODULES = {
    'muse': dict(repository='https://github.com/musescore/muse_framework',commit='3c5512eb8ee1a863a6123e62bd75a6ab55045752'),
    'muse_deps': dict(repository='https://github.com/musescore/muse_deps',commit='b915e6703a2a9839b2a98d4ca2468a88e361929f'),
}


def generate(root, source_commit):
    require(isinstance(source_commit,str) and re.fullmatch('[0-9a-f]{40}',source_commit),'Exact application source revision required')
    root=Path(root);base=root/'distribution/corresponding-source'
    publication=verify_publication(root);microsoft=verify_microsoft(root)
    raw=read_owned(root,CATALOG,8*1024**2);catalog=json.loads(raw)
    notices={};files={};seen={}
    rows=[notice for archive in catalog['archives'] for notice in archive['notices']]+catalog['repositoryNotices']
    for row in rows:
        path=row['path'];require(path.startswith('notices/'),'Original notice escapes exact source tree')
        relative=path.removeprefix('notices/');_register_path(relative,seen)
        data=read_owned(base,path,16*1024**2)
        require(digest(data)==row['notice'],'Package notice differs from original bytes: '+path)
        notices[relative]=row['notice'];files['Notices/'+relative]=data
    require(len(notices)==532 and inventory_tree(base/'notices')==notices,'Missing/untracked original package notices')
    for name,expected in microsoft['documents'].items():
        data=read_owned(base,'microsoft-notices/'+name,1024**2)
        require(digest(data)==expected,'Original Microsoft terms changed during package generation')
        files['Notices/Microsoft/'+name]=data
    application=dict(repository='https://github.com/hashfunction/wavequay',commit=source_commit,
        sourceUrl='https://github.com/hashfunction/wavequay/tree/'+source_commit,
        archiveUrl='https://github.com/hashfunction/wavequay/archive/'+source_commit+'.tar.gz',
        submodules={name:dict(row,archiveUrl=row['repository']+'/archive/'+row['commit']+'.tar.gz') for name,row in SUBMODULES.items()})
    info=dict(schemaVersion=1,product='WaveWeft',version='1.0.1',application=application,
        preferredSources=publication['archives'],dependencyPublication=dict(releaseUrl=publication['releaseUrl'],
            tagCommit=publication['publicationTagCommit'],originalRecords=publication['originalRecords']),
        originalCatalog=digest(raw),notices=notices,microsoftDocuments=microsoft['documents'],microsoftOwners=microsoft['owners'])
    files['SOURCE-INFO.json']=(json.dumps(info,indent=2,sort_keys=True)+'\n').encode()
    files['SOURCE-README.txt']=('''WaveWeft 1.0.1 source and component notices

The application source for this exact build is:
'''+application['sourceUrl']+'''
Its commit-pinned source archive is:
'''+application['archiveUrl']+'''

The top-level archive does not recursively contain its Git submodules. Fetch
the exact Muse and muse_deps commits and archive URLs in SOURCE-INFO.json too.
Alternatively, clone the application repository, check out the stated commit,
and run git submodule update --init --recursive. All source modifications,
local dependency recipe overrides and build/packaging scripts are in that tree.
The complete original dependency source archives are listed with exact sizes,
SHA-256 hashes, original origins and public WaveWeft delivery URLs in that file.
The dependency publication tag is historical and separate from this build's
application source commit. It does not identify a current application binary.

For the native Windows build, follow README.md and the pinned dependencies,
Qt version and CMake settings in .github/workflows/windows.yml and
buildscripts/ci/windows/wavequay-release.cmake. The source recipe overrides are
in distribution/recipes. The workflow's installed acceptance tools observe the
application externally; they do not add test-only runtime behavior. Microsoft's
licensed build tools are used for building and packaging, not redistributed as
part of this application.

Original application and component copyrights/licenses are retained unchanged
under Notices/Repository and Notices/ThirdParty. Modified application files
identify their changes in the source repository. Qt and other shared libraries
can be rebuilt from their stated source. A CMake-installed unpackaged directory
can be used with replacement compatible libraries or a rebuilt executable; the
release qualification checks are not a restriction on modifying that source.
Build a package from your modified output with your own signing certificate if
you choose to install it as a package. Preserve the component license notices.

The separately licensed Microsoft object-code files and their original license
terms/distributable lists are under Notices/Microsoft and explicitly scoped in
SOURCE-INFO.json. Those terms apply only to the identified Microsoft runtime
components. They do not relicense WaveWeft or its open-source components.
Redistribution and recipient conditions remain those in the original documents.
Microsoft is not the publisher of WaveWeft.

Product, support and privacy information: https://waveweft.trieflow.com
''').encode()
    require(file_record(root/CATALOG)==digest(raw),'Original source catalog changed during package generation')
    return files
