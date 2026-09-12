import QtQuick
import QtQuick.Layouts
import Muse.Ui
import Muse.UiComponents

StyledDialogView {
    id: root
    objectName: "ManageExportRecipesDialog"
    title: qsTrc("export", "Manage export recipes")
    contentWidth: 480
    contentHeight: body.implicitHeight
    margins: 16
    modal: true
    required property var recipeModel
    property string selectedId: ""
    property bool confirming: false
    property alias panel: recipePanel
    onNavigationActivateRequested: chooser.navigation.requestActive()
    ColumnLayout {
        id: body
        width: root.contentWidth
        spacing: 12
        // Muse resolves the window through the panel's visual QObject ancestor.
        NavigationPanel {
            id: recipePanel
            name: "ManageRecipesPanel"
            section: root.navigationSection
            order: 1
        }
        StyledDropdown {
            id: chooser
            Layout.fillWidth: true
            model: recipeModel.recipes
            textRole: "name"
            valueRole: "id"
            currentIndex: indexOfValue(root.selectedId)
            indeterminateText: qsTrc("export", "Choose a recipe")
            navigation.name: "ManagedRecipe"
            navigation.panel: root.panel
            navigation.order: 1
            navigation.accessible.name: qsTrc("export", "Recipe to delete")
            onActivated: function (index, value) { root.selectedId = value; root.confirming = false }
        }
        StyledTextLabel {
            Layout.fillWidth: true
            text: root.confirming ? qsTrc("export", "Delete “%1”? Your project and audio files will remain unchanged.").arg(chooser.currentText)
                                 : qsTrc("export", "Deleting a recipe removes only its saved export settings.")
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignLeft
        }
        StyledTextLabel {
            Layout.fillWidth: true
            visible: recipeModel.recipeError.length > 0
            text: recipeModel.recipeError
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            FlatButton {
                text: root.confirming ? qsTrc("global", "Cancel") : qsTrc("global", "Close")
                navigation.panel: root.panel
                navigation.order: 2
                onClicked: { if (root.confirming) root.confirming = false; else root.reject() }
            }
            FlatButton {
                text: root.confirming ? qsTrc("export", "Confirm delete") : qsTrc("export", "Delete recipe")
                enabled: root.selectedId.length > 0
                navigation.name: "DeleteRecipe"
                navigation.panel: root.panel
                navigation.order: 3
                onClicked: {
                    if (!root.confirming) { root.confirming = true; return }
                    if (recipeModel.removeRecipe(root.selectedId)) { root.selectedId = ""; root.confirming = false }
                }
            }
        }
    }
}
