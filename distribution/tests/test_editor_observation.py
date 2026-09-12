"""Compile the actual editor observation predicate; this is not native GUI evidence."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class EditorObservationTests(unittest.TestCase):
    def test_actual_predicate_handles_muse_panel_context_and_rejects_invalid_controls(self):
        code = (ROOT / 'distribution/windows-gui/GuiProbe.cs').read_text()
        start = code.index('private static bool Has(')
        brace = code.index('{', start)
        depth, end = 1, brace + 1
        while depth:
            depth += (code[end] == '{') - (code[end] == '}')
            end += 1
        method = code[start:end]
        conditions = re.findall(r'if \(([^\n]*Has\(tree, "Playback toolbar"[^\n]*)\) continue;', code)
        self.assertEqual(len(conditions), 1, 'Expected the actual main editor predicate exactly once')
        replay = r'''
using System;
using System.Collections.Generic;
static class EditorReplay {
    // ACTUAL_HAS_METHOD
    static bool Observe(List<Dictionary<string, object>> tree) {
        var process = new { Id = 1744 };
        return !(ACTUAL_EDITOR_REJECTION);
    }
    static Dictionary<string, object> Node(string name, string role) {
        return new Dictionary<string, object> {
            {"name", name}, {"controlType", role}, {"processId", 1744},
            {"enabled", true}, {"offscreen", false}, {"invoke", false}
        };
    }
    static void Check(bool result, string reason) { if (!result) throw new Exception(reason); }
    static int Main() {
        foreach (string label in new[] {"Add track", "Add track panel, Add track"}) {
            var toolbar = Node("Playback toolbar", "Text");
            var panel = Node("Add track", "Text");
            var button = Node(label, "Button");
            var tree = new List<Dictionary<string, object>> { toolbar, panel, button };
            Check(Observe(tree), "Rejected actual editor button name: " + label);
            foreach (var pair in new[] {
                new KeyValuePair<string, object>("processId", 999),
                new KeyValuePair<string, object>("enabled", false),
                new KeyValuePair<string, object>("offscreen", true),
                new KeyValuePair<string, object>("controlType", "Text"),
                new KeyValuePair<string, object>("controlType", "Pane") }) {
                var original = button[pair.Key]; button[pair.Key] = pair.Value;
                Check(!Observe(tree), "Accepted invalid button " + pair.Key);
                button[pair.Key] = original;
            }
            foreach (string invalid in new[] {"Other panel, Add track", "Add track panel, Add track extra", "Add track panel, Add track ", "prefix Add track", "Add track panel"}) {
                button["name"] = invalid;
                Check(!Observe(tree), "Accepted near-match label: " + invalid);
            }
            button["name"] = label;
            tree.Remove(button);
            Check(!Observe(tree), "Text panel substituted for actual Add track Button");
            tree.Add(button); tree.Remove(toolbar);
            Check(!Observe(tree), "Accepted missing Playback toolbar");
            tree.Add(toolbar);
            foreach (var pair in new[] {
                new KeyValuePair<string, object>("processId", 999),
                new KeyValuePair<string, object>("enabled", false),
                new KeyValuePair<string, object>("offscreen", true) }) {
                var original = toolbar[pair.Key]; toolbar[pair.Key] = pair.Value;
                Check(!Observe(tree), "Accepted invalid toolbar " + pair.Key);
                toolbar[pair.Key] = original;
            }
        }
        Console.WriteLine("PASS: actual editor predicate; two exact labels and 30 role/ownership/visibility/name/missing-control rejections");
        return 0;
    }
}
'''
        replay = replay.replace('// ACTUAL_HAS_METHOD', method).replace('ACTUAL_EDITOR_REJECTION', conditions[0])
        dotnet = os.environ.get('WAVEQUAY_TEST_DOTNET') or shutil.which('dotnet')
        self.assertTrue(dotnet, 'A .NET SDK is required for the actual C# editor replay')
        major = int(subprocess.check_output([dotnet, '--version'], text=True).strip().split('.')[0])
        self.assertGreaterEqual(major, 8)
        with tempfile.TemporaryDirectory(prefix='waveweft-editor-predicate-') as directory:
            project = Path(directory)
            (project / 'Replay.cs').write_text(replay)
            (project / 'Replay.csproj').write_text(
                '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
                f'<TargetFramework>net{major}.0</TargetFramework><Nullable>disable</Nullable>'
                '<LangVersion>5</LangVersion></PropertyGroup></Project>')
            result = subprocess.run([dotnet, 'run', '--project', str(project / 'Replay.csproj'), '--verbosity', 'quiet'],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS: actual editor predicate', result.stdout)


if __name__ == '__main__': unittest.main()
