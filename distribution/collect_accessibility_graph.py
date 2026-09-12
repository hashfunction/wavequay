# SPDX-License-Identifier: GPL-3.0-only
"""Copy only a bounded, owned, stopped-process diagnostic graph; never acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid
from collect_application_logs import no_redirect

MAX_BYTES = 8 * 1024 * 1024
COMMON = {'kind', 'schemaVersion', 'pid', 'sequence', 'snapshot', 'elapsedMs'}
FIELDS = {
    'started': {'diagnosticOnly', 'maxBytes', 'maxNodes', 'maxDepth', 'maxDurationMs'},
    'query': {'operation', 'id', 'index', 'phase'},
    'window': {'window', 'objectClass'},
    'node': {'id', 'depth', 'valid', 'role', 'invisible', 'disabled', 'parent', 'parentIndex', 'childCount',
             'window', 'parentWindow', 'windowRoot', 'objectClass', 'itemClass', 'itemOwnerClass', 'itemRole', 'ignored', 'itemWindow'},
    'edge': {'id', 'index', 'child', 'childParent', 'valid', 'repeated'},
    'snapshot-start': set(), 'snapshot-end': {'nodes'}, 'truncated': {'reason'}, 'end': set(),
}
OPERATIONS = {'window-root', 'unique-id', 'valid', 'object', 'role', 'state', 'parent', 'window', 'child-count',
              'parent-id', 'parent-valid', 'parent-index', 'item-role', 'item-ignored', 'item-window',
              'child', 'child-id', 'child-valid', 'child-parent', 'child-parent-id', 'parent-window', 'fragment-root', 'fragment-root-id'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(data, pid):
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate graph field')
            result[key] = value
        return result
    require(0 < len(data) <= MAX_BYTES and data.endswith(b'\n'), 'Graph bytes/newline differ')
    rows = []
    elapsed = -1
    for line in data.splitlines():
        require(len(line) <= 4096, 'Graph row exceeds bound')
        row = json.loads(line.decode('utf-8'), object_pairs_hook=unique_fields)
        require(isinstance(row, dict) and row.get('kind') in FIELDS, 'Graph row kind differs')
        require(set(row) <= COMMON | FIELDS[row['kind']] and COMMON <= set(row), 'Unexpected graph fields')
        require(type(row['pid']) is int and row['pid'] == pid and type(row['schemaVersion']) is int and row['schemaVersion'] == 1
                and type(row['sequence']) is int and row['sequence'] == len(rows) + 1
                and type(row['snapshot']) is int and row['snapshot'] >= 0, 'Graph process/schema/sequence differs')
        require(type(row['elapsedMs']) is int and row['elapsedMs'] >= elapsed, 'Graph clock differs')
        elapsed = row['elapsedMs']
        for key, value in row.items():
            if key.endswith('Class'):
                require(isinstance(value, str) and (value == '' or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_:]{0,127}', value)), 'Invalid class metadata')
            elif key in {'kind', 'operation', 'phase', 'reason'}:
                continue
            else:
                require(type(value) in (int, bool) and -(2**31) <= value < 2**53, 'Unexpected graph data type')
        if row['kind'] == 'query':
            require(row['operation'] in OPERATIONS and row['phase'] in {'begin', 'end'}, 'Graph query differs')
        if row['kind'] == 'truncated':
            require(row['reason'] in {'byte-limit', 'node-limit', 'depth-limit', 'child-count-limit', 'time-limit'}, 'Graph truncation differs')
        rows.append(row)
    require(rows[0]['kind'] == 'started' and rows[0]['diagnosticOnly'] is True
            and [rows[0][key] for key in ('maxBytes', 'maxNodes', 'maxDepth', 'maxDurationMs')] == [MAX_BYTES, 256, 32, 90000], 'Graph start limits differ')
    return dict(records=len(rows), completed=rows[-1]['kind'] == 'end',
                truncated=any(row['kind'] == 'truncated' for row in rows), lastRecord=rows[-1])


def collect(report_path):
    output = report_path.absolute().parent
    result = dict(schemaVersion=1, diagnosticOnly=True, accepted=False, files=[], errors=[])
    try:
        no_redirect(report_path)
        report = json.loads(report_path.read_text(encoding='utf-8-sig'))
        require(report.get('diagnosticAccessibilityGraph') is True and 'installedLaunch' not in report, 'Explicit staged graph diagnostic is required')
        require(isinstance(report.get('sourceCommit'), str) and re.fullmatch(r'[0-9a-f]{40}', report['sourceCommit']), 'Invalid exact source commit')
        result['sourceCommit'] = report['sourceCommit']
        require(report['cleanup'] == dict(ownedJobClosed=True, processExited=True)
                and report['ownedJobEmptyBeforeClose'] is True, 'Original owned process/job cleanup not proved')
        pid = report['processId']
        require(type(pid) is int and pid > 0, 'Missing retained process ID')
        private = output / 'private-environment'
        path = private / 'Temp/accessibility-graph.jsonl'
        require(report['environment']['WAVEWEFT_ACCESSIBILITY_GRAPH'] == str(path), 'Graph output differs from owned private path')
        token = report['consumerProfileClaim']['token']
        require(str(uuid.UUID(token)) == token, 'Invalid owner token')
        marker = private / '.waveweft-consumer-owner'
        no_redirect(marker)
        require(marker.stat().st_size == 36 and marker.read_text() == token, 'Graph owner changed')
        no_redirect(path)
        before = path.stat()
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_BYTES, 'Graph is not a bounded regular file')
        with path.open('rb') as source:
            opened = os.fstat(source.fileno())
            require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'Graph changed before read')
            data = source.read(MAX_BYTES + 1)
            after = os.fstat(source.fileno())
        require((opened.st_size, opened.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Graph changed during read')
        metadata = validate(data, pid)
        destination = output / 'accessibility-graph.jsonl'
        with destination.open('xb') as target:
            target.write(data)
        result['files'].append(dict(path=destination.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), **metadata))
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['errors'].append(str(error))
    with (output / 'accessibility-graph-capture.json').open('x', encoding='utf-8') as target:
        json.dump(result, target, indent=2)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    result = collect(parser.parse_args().report)
    print('Graph diagnostic capture errors:', len(result['errors']))
    raise SystemExit(bool(result['errors']))
