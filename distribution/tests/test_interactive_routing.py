"""Bind startup floating-window routing to the real QML dialog properties."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class InteractiveRoutingTests(unittest.TestCase):
    def test_startup_floating_dialogs_accept_the_routing_property(self):
        scenario = (ROOT / 'src/appshell/internal/startupscenario.cpp').read_text(encoding='utf-8')
        self.assertIn(
            'FIRST_LAUNCH_SETUP_URI("audacity://firstLaunchSetup?floating=true")',
            scenario,
        )
        self.assertRegex(
            scenario,
            re.compile(
                r'UriQuery query\(WELCOME_DIALOG_URI\);.*?query\.set\("floating", true\);',
                re.S,
            ),
        )

        for relative in (
            'src/appshell/qml/Audacity/AppShell/FirstLaunchSetup/FirstLaunchSetupDialog.qml',
            'src/appshell/qml/Audacity/AppShell/WelcomeDialog.qml',
        ):
            qml = (ROOT / relative).read_text(encoding='utf-8')
            self.assertRegex(qml, r'(?m)^\s*property bool floating: false\s*$')
            self.assertNotRegex(qml, r'(?m)^\s*readonly property bool floating\b')


if __name__ == '__main__':
    unittest.main()
