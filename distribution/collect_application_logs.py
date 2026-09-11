# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Trieflow LLC
"""Retain bounded startup logs from the observer's previously absent app roots.

Muse sends Windows console/Qt messages to OutputDebugString and its own log
file, so redirected stdout/stderr alone do not retain startup failures. This
collector runs after owned-process cleanup. It never copies preferences or
changes application state and its output is not proof of GUI success.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

APP_NAMES = {'Audacity4', 'Audacity4Development', 'WaveQuay', 'WaveQuay4', 'WaveQuay 4'}
ORGANIZATIONS = {'Trieflow', 'Trieflow LLC'}
LOG_NAME = re.compile(r'(?:WaveQuay|Audacity)_\d{6}_\d{6}\.log\Z')
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_LOGS = 8


def no_redirect(path):
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError(f'Redirected diagnostic path: {item}')


def collect(report_path):
    output = report_path.parent
    result = dict(schemaVersion=1, files=[], roots=[], errors=[])
    try:
        no_redirect(output)
        observation = json.loads(report_path.read_text(encoding='utf-8-sig'))
        state = observation.get('userStateBefore')
        if not isinstance(state, list) or not state or len(state) > 200:
            raise ValueError('Missing bounded fresh-profile preflight evidence')
        if any(entry.get('exists') is not False for entry in state):
            raise ValueError('Refusing logs from a profile not proven absent before launch')
        roots = []
        for entry in state:
            root = Path(entry['path'])
            if root.name in APP_NAMES and root.parent.name in ORGANIZATIONS:
                if not root.is_absolute() or '..' in root.parts:
                    raise ValueError('Invalid application diagnostic root')
                if root not in roots:
                    roots.append(root)
        if not roots:
            raise ValueError('No recognized fresh application data roots')
        for root in sorted(roots):
            logs = root / 'logs'
            result['roots'].append(dict(path=str(logs), exists=logs.exists()))
            if not logs.exists():
                continue
            try:
                no_redirect(logs)
                for source in sorted(logs.iterdir()):
                    if not LOG_NAME.fullmatch(source.name):
                        continue
                    if len(result['files']) >= MAX_LOGS:
                        raise ValueError('Application log count exceeded bounded capture')
                    no_redirect(source)
                    before = source.stat()
                    if not stat.S_ISREG(before.st_mode):
                        raise ValueError('Application diagnostic is not a regular file')
                    with source.open('rb') as stream:
                        opened = os.fstat(stream.fileno())
                        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                            raise ValueError('Application diagnostic changed before reading')
                        offset = max(0, opened.st_size - MAX_LOG_BYTES)
                        stream.seek(offset)
                        data = stream.read(MAX_LOG_BYTES)
                        after = os.fstat(stream.fileno())
                    if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise ValueError('Application diagnostic changed during capture')
                    filename = f'application-startup-{len(result["files"]) + 1:02}.log'
                    with (output / filename).open('xb') as destination:
                        destination.write(data)
                    result['files'].append(dict(path=filename, sourcePath=str(source), sourceBytes=opened.st_size,
                        capturedBytes=len(data), offset=offset, truncated=offset > 0,
                        sha256=hashlib.sha256(data).hexdigest()))
            except (OSError, ValueError) as error:
                result['errors'].append(f'{logs}: {error}')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        result['errors'].append(str(error))
    (output / 'application-logs.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    metadata = collect(args.report)
    print(f'Application startup logs retained: {len(metadata["files"])}; capture errors: {len(metadata["errors"])}')
    raise SystemExit(1 if metadata['errors'] else 0)
