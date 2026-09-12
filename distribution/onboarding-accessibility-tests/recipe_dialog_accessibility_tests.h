// SPDX-License-Identifier: GPL-3.0-only
// Uses both production recipe QML files, StyledDialogView/FlatButton and Muse
// providers. The fixture attaches their content to real QQuickViews as
// WindowView::componentComplete does; it does not simulate Windows UIA success.
static void recipeDialogAccessibilityTests(QQmlEngine& engine, QQuickWindow& mainWindow)
{
    QQuickView outer(&engine, nullptr);
    outer.setTransientParent(&mainWindow);
    outer.resize(700, 700);
    outer.show();
    auto outerRoot = QAccessible::queryAccessibleInterface(&outer);
    require(outerRoot, "export fixture uses the actual registered window provider");
    const auto model = engine.evaluate("({recipes: [], recipeError: '', saveCurrentRecipe: function(){return true}, removeRecipe: function(){return true}})");
    for (const QString& name : {QStringLiteral("ManageExportRecipesDialog"), QStringLiteral("SaveExportRecipeDialog")}) {
        QQmlComponent component(&engine, QUrl::fromLocalFile(QStringLiteral(WAVEQUAY_TEST_IMPORTS "/RecipeDialogs/") + name + ".qml"));
        std::unique_ptr<QObject> dialog(component.createWithInitialProperties({{"recipeModel", QVariant::fromValue(model)}, {"isOpened", false}}));
        if (!dialog) qCritical() << component.errors();
        require(dialog != nullptr, "production recipe QML must load");
        // ExportDialog places both nonvisual DialogView objects inside its
        // default contentData. QObject ownership stays at this outer item.
        dialog->setParent(outer.contentItem());
        QQuickView nested(&engine, nullptr);
        nested.QObject::setParent(dialog.get());
        auto content = dialog->property("contentItem").value<QQuickItem*>();
        require(content, "recipe has its production StyledDialogView content");
        nested.setContent(QUrl(), nullptr, content);
        auto panel = qobject_cast<ui::NavigationPanel*>(dialog->property("panel").value<QObject*>());
        require(panel && panel->controls().size() == (name.startsWith("Manage") ? 3u : 6u), "all original recipe controls belong to the exposed panel alias");
        process();
        auto item = panel->accessible();
        qInfo().noquote() << "Recipe ownership" << name << "panelIsOuter" << (item->accessibleWindow() == &outer)
                         << "panelIsNested" << (item->accessibleWindow() == &nested)
                         << "nestedHasHandle" << bool(nested.handle()) << "children" << panel->controls().size();
        for (auto control : panel->controls()) {
            auto navigation = dynamic_cast<ui::NavigationControl*>(control);
            require(navigation && navigation->accessible()->accessibleWindow() == &nested,
                    "recipe controls resolve their own real QQuickView before it is opened");
        }
        require(!nested.isVisible() && !nested.handle(), "closed recipe has a QWindow but no native handle");
        require(item->accessibleWindow() == &nested && panel->window() == &nested,
                "closed recipe panel must resolve its own content window, not the outer export window");
        auto containsPanel = [item](QAccessibleInterface* root) {
            for (int i = 0; i < root->childCount(); ++i) {
                auto object = qobject_cast<AccessibleObject*>(root->child(i)->object());
                if (object && object->item() == item) return true;
            }
            return false;
        };
        require(!containsPanel(outerRoot), "closed recipe panel must not leak into the outer export tree");
        // WindowView resolves the transient parent when opening, not constructing.
        nested.setTransientParent(&outer);
        nested.show();
        dialog->setProperty("isOpened", true);
        QMetaObject::invokeMethod(dialog.get(), "opened");
        process();
        auto nestedRoot = QAccessible::queryAccessibleInterface(&nested);
        require(nestedRoot && containsPanel(nestedRoot) && !containsPanel(outerRoot),
                "opened recipe panel remains reachable only from its own window");
        const auto expected = name.startsWith("Manage") ? QStringLiteral("Recipe to delete") : QStringLiteral("Recipe name");
        auto control = namedBySibling(nestedRoot, expected);
        require(control && control->window() == &nested && control->parent()->window() == &nested,
                "real sibling traversal reaches the recipe input with consistent fragment ownership");
        auto focus = nestedRoot->focusChild();
        require(focus && focus->window() == &nested, "opened recipe requests focus within its own window");
        require(namedBySibling(nestedRoot, name.startsWith("Manage") ? QStringLiteral("Close") : QStringLiteral("Cancel")),
                "the original enabled recipe close control stays accessible");
        nested.hide();
        dialog->setProperty("isOpened", false);
        process();
        require(!containsPanel(outerRoot) && item->accessibleWindow() == &nested,
                "closing a previously shown recipe cannot move its panel to the export window");
        // The QQuickView is a stack object; do not leave it owned by dialog.
        nested.QObject::setParent(nullptr);
        qInfo().noquote() << "Recipe dialog closed/open/closed ownership passed" << name;
    }
}
