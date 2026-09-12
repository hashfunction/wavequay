import QtQuick
import QtQuick.Layouts
import Muse.Ui
import Muse.UiComponents

StyledDialogView {
    id: root
    title: qsTrc("export", "Save export recipe")
    objectName: "SaveExportRecipeDialog"
    contentWidth: 480
    contentHeight: body.implicitHeight
    margins: 16
    modal: true
    required property var recipeModel
    property string recipeName: ""
    property int duplicateIndex: 0
    property var duplicates: recipeModel.recipes.filter(function (r) { return r.name === recipeName.trim() })
    property alias panel: recipePanel
    onNavigationActivateRequested: nameField.navigation.requestActive()
    function save(id, allowDuplicate) {
        if (recipeModel.saveCurrentRecipe(recipeName, id, allowDuplicate)) root.accept()
    }
    ColumnLayout {
        id: body
        width: root.contentWidth
        spacing: 12
        // Muse resolves the window through the panel's visual QObject ancestor.
        NavigationPanel {
            id: recipePanel
            name: "SaveRecipePanel"
            section: root.navigationSection
            order: 1
        }
        StyledTextLabel {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignLeft
            text: qsTrc("export", "Save the current format, channels, sample rate and encoder settings. Recipes contain no audio or file locations.")
        }
        TextInputField {
            id: nameField
            Layout.fillWidth: true
            currentText: root.recipeName
            hint: qsTrc("export", "Recipe name")
            navigation.name: "RecipeName"
            navigation.panel: root.panel
            navigation.order: 1
            navigation.accessible.name: qsTrc("export", "Recipe name")
            onTextChanged: function (text) { root.recipeName = text; root.duplicateIndex = 0 }
        }
        StyledTextLabel {
            Layout.fillWidth: true
            visible: root.duplicates.length > 0
            wrapMode: Text.WordWrap
            text: qsTrc("export", "This name already exists. Choose a recipe to update, or create another.")
        }
        StyledDropdown {
            Layout.fillWidth: true
            visible: root.duplicates.length > 0
            model: root.duplicates.map(function (r) { return {name: r.format + " · " + r.id.slice(0, 8), id: r.id} })
            textRole: "name"
            valueRole: "id"
            currentIndex: root.duplicateIndex
            navigation.name: "RecipeToUpdate"
            navigation.panel: root.panel
            navigation.order: 2
            navigation.accessible.name: qsTrc("export", "Recipe to update")
            onActivated: function (index) { root.duplicateIndex = index }
        }
        StyledTextLabel {
            Layout.fillWidth: true
            visible: recipeModel.recipeError.length > 0
            text: recipeModel.recipeError
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignLeft
        }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            FlatButton {
                text: qsTrc("global", "Cancel")
                navigation.panel: root.panel
                navigation.order: 3
                onClicked: root.reject()
            }
            FlatButton {
                visible: root.duplicates.length > 0
                text: qsTrc("export", "Update existing")
                navigation.panel: root.panel
                navigation.order: 4
                onClicked: root.save(root.duplicates[root.duplicateIndex].id, false)
            }
            FlatButton {
                text: root.duplicates.length > 0 ? qsTrc("export", "Create another") : qsTrc("export", "Save recipe")
                enabled: root.recipeName.trim().length > 0
                accentButton: true
                navigation.panel: root.panel
                navigation.order: 5
                onClicked: root.save("", root.duplicates.length > 0)
            }
        }
    }
}
