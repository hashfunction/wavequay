// Test rendering leaf; preserves the real dropdown's inner-item/navigation ownership.
import QtQuick
import Muse.Ui
Item {
    id: root
    property var model: []
    property string textRole: "name"
    property string valueRole: "id"
    property int currentIndex: -1
    property string indeterminateText: ""
    property string currentText: currentIndex >= 0 && currentIndex < model.length ? model[currentIndex][textRole] : indeterminateText
    property alias navigation: nav
    implicitHeight: 30
    implicitWidth: 200
    signal activated(int index, var value)
    function indexOfValue(value) {
        for (let i = 0; i < model.length; ++i) if (model[i][valueRole] === value) return i
        return -1
    }
    Item {
        id: mainItem
        anchors.fill: parent
        NavigationControl {
            id: nav
            enabled: mainItem.enabled && mainItem.visible
            accessible.role: MUAccessible.ComboBox
        }
    }
}
