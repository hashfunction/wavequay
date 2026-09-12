// Test rendering leaf; production recipe layout and Muse navigation/providers are loaded unchanged.
import QtQuick
import Muse.Ui
Item {
    id: root
    property string currentText: ""
    property string hint: ""
    property alias navigation: nav
    implicitHeight: 30
    implicitWidth: 200
    signal textChanged(var value)
    NavigationControl {
        id: nav
        enabled: root.enabled && root.visible
        accessible.role: MUAccessible.EditableText
        accessible.visualItem: root
    }
    // The production input also owns a hidden clear button in the same panel.
    FlatButton {
        visible: false
        navigation.panel: nav.panel
        navigation.order: nav.order + 1
    }
}
