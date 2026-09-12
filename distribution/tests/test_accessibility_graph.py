# SPDX-License-Identifier: GPL-3.0-only
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collect_accessibility_graph as graph


class GraphCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name).resolve()
        self.private = self.output / 'private-environment'
        self.path = self.private / 'Temp/accessibility-graph.jsonl'
        self.path.parent.mkdir(parents=True)
        self.token = str(uuid.uuid4())
        self.marker = self.private / '.waveweft-consumer-owner'
        self.marker.write_text(self.token)
        self.report = dict(diagnosticAccessibilityGraph=True, sourceCommit='a'*40, processId=123,
            cleanup=dict(ownedJobClosed=True, processExited=True), ownedJobEmptyBeforeClose=True,
            environment={'WAVEWEFT_ACCESSIBILITY_GRAPH': str(self.path)}, consumerProfileClaim=dict(token=self.token),
            errors=['Original UIA E_FAIL retained'])
        self.report_path = self.output / 'gui-observations.json'
        self.rows = [dict(kind='started', diagnosticOnly=True, maxBytes=graph.MAX_BYTES, maxNodes=256, maxDepth=32, maxDurationMs=90000),
                     dict(kind='query', operation='child', phase='begin', id=2147484444, index=0), dict(kind='end')]
        for index, row in enumerate(self.rows):
            row.update(schemaVersion=1, pid=123, sequence=index+1, elapsedMs=index, snapshot=0)
        self.save()

    def save(self):
        self.path.write_bytes(b''.join(json.dumps(row).encode()+b'\n' for row in self.rows))
        self.report_path.write_text(json.dumps(self.report))

    def test_stopped_original_failure_keeps_exact_bytes_and_primary(self):
        original = self.path.read_bytes()
        result = graph.collect(self.report_path)
        self.assertEqual(result['errors'], [])
        self.assertFalse(result['accepted'])
        self.assertTrue(result['diagnosticOnly'])
        self.assertEqual((self.output / 'accessibility-graph.jsonl').read_bytes(), original)
        self.assertEqual(json.loads(self.report_path.read_text())['errors'], ['Original UIA E_FAIL retained'])

    def test_abrupt_owned_process_stop_retains_last_query_without_claiming_complete(self):
        self.rows.pop(); self.save()
        result = graph.collect(self.report_path)
        self.assertEqual(result['errors'], [])
        self.assertFalse(result['files'][0]['completed'])
        self.assertEqual(result['files'][0]['lastRecord']['operation'], 'child')

    def test_bad_graph_refused(self):
        original = copy.deepcopy(self.rows)
        cases = [(0, 'pid', 999), (1, 'sequence', 1), (1, 'operation', 'user typed text'),
                 (1, 'value', 'private'), (1, 'phase', 'unknown'), (0, 'maxNodes', 512),
                 (0, 'diagnosticOnly', False), (1, 'objectClass', 'private text')]
        for index, key, value in cases:
            with self.subTest(key=key):
                self.rows = copy.deepcopy(original); self.rows[index][key] = value; self.save()
                with self.assertRaises(ValueError): graph.validate(self.path.read_bytes(), 123)
        with self.assertRaises(ValueError): graph.validate(b'x' * (graph.MAX_BYTES+1), 123)
        with self.assertRaises(ValueError): graph.validate(self.path.read_bytes().rstrip(b'\n'), 123)

    def test_capture_ownership_and_explicit_mode_refusals(self):
        original = copy.deepcopy(self.report)
        mutations = [lambda r: r.update(diagnosticAccessibilityGraph=False), lambda r: r.update(installedLaunch={}),
                     lambda r: r.update(ownedJobEmptyBeforeClose=False), lambda r: r['cleanup'].update(processExited=False),
                     lambda r: r['environment'].update(WAVEWEFT_ACCESSIBILITY_GRAPH='/foreign'),
                     lambda r: r['consumerProfileClaim'].update(token=str(uuid.uuid4()))]
        for change in mutations:
            self.report = copy.deepcopy(original); change(self.report); self.save()
            result = graph.collect(self.report_path)
            self.assertTrue(result['errors']); self.assertFalse(result['accepted'])
            self.assertFalse((self.output / 'accessibility-graph.jsonl').exists())
            (self.output / 'accessibility-graph-capture.json').unlink()
        self.report = original; self.save(); self.marker.unlink()
        self.assertTrue(graph.collect(self.report_path)['errors'])

    def test_existing_destination_is_preserved(self):
        target = self.output / 'accessibility-graph.jsonl'; target.write_bytes(b'foreign')
        self.assertTrue(graph.collect(self.report_path)['errors'])
        self.assertEqual(target.read_bytes(), b'foreign')

    def test_duplicate_json_fields_cannot_hide_unretained_text(self):
        data = self.path.read_bytes().replace(b'"operation": "child"', b'"operation": "private typed text", "operation": "child"')
        with self.assertRaises(ValueError): graph.validate(data, 123)

    def test_target_window_metadata_and_capture_limit_preserve_diagnostic_only(self):
        self.rows[1] = dict(kind='window', window=1234, objectClass='QQuickView',
            ownerClass='ExportDialog_QMLTYPE_12', ownerClassChain=['ExportDialog_QMLTYPE_12', 'DialogView', 'QObject'],
            selected=True, schemaVersion=1, pid=123, sequence=2, elapsedMs=1, snapshot=1)
        self.rows.insert(2, dict(kind='truncated', reason='capture-limit', schemaVersion=1, pid=123,
            sequence=3, elapsedMs=2, snapshot=3))
        self.rows[-1].update(sequence=4, elapsedMs=3, snapshot=3)
        self.save()
        original = self.path.read_bytes()
        result = graph.collect(self.report_path)
        self.assertEqual(result['errors'], [])
        self.assertFalse(result['accepted'])
        self.assertTrue(result['files'][0]['completed'])  # stream ended, not product acceptance
        self.assertTrue(result['files'][0]['truncated'])
        self.assertEqual((self.output / 'accessibility-graph.jsonl').read_bytes(), original)

    def test_window_owner_metadata_refuses_unbounded_or_text_payload(self):
        row = dict(kind='window', window=1234, objectClass='QQuickView', ownerClass='QObject',
            ownerClassChain=['QObject'], selected=False, schemaVersion=1, pid=123, sequence=2, elapsedMs=1, snapshot=1)
        self.rows[1] = row
        for key, value in [('ownerClassChain', ['QObject'] * 9), ('ownerClassChain', 'QObject'),
                           ('ownerClassChain', ['private text']), ('ownerClassChain', [123]),
                           ('ownerClass', 'private text'), ('selected', 1), ('selected', 'true')]:
            with self.subTest(key=key, value=value):
                self.rows[1] = {**row, key: value}; self.save()
                with self.assertRaises(ValueError): graph.validate(self.path.read_bytes(), 123)

    @unittest.skipUnless(os.environ.get('WAVE_GRAPH_TARGET_TEST_RECORD'), 'optional actual targeted native writer replay')
    def test_actual_targeted_native_writer_record(self):
        data = Path(os.environ['WAVE_GRAPH_TARGET_TEST_RECORD']).read_bytes()
        rows = [json.loads(line) for line in data.splitlines()]
        parsed = graph.validate(data, rows[0]['pid'])
        self.assertTrue(parsed['completed'])
        self.assertTrue(parsed['truncated'])
        self.assertEqual(rows[-2]['reason'], 'capture-limit')
        self.assertEqual(sum(row['kind'] == 'window' and row.get('selected') is True for row in rows), 3)
        first_query = next(row for row in rows if row['kind'] == 'query')
        self.assertGreaterEqual(first_query['snapshot'], 9)

    @unittest.skipUnless(os.environ.get('WAVE_GRAPH_TEST_RECORD'), 'optional actual native writer replay')
    def test_actual_native_writer_record(self):
        data = Path(os.environ['WAVE_GRAPH_TEST_RECORD']).read_bytes()
        pid = json.loads(data.splitlines()[0])['pid']
        parsed = graph.validate(data, pid)
        self.assertTrue(parsed['completed'])
        self.assertGreater(parsed['records'], 50)


if __name__ == '__main__': unittest.main()
