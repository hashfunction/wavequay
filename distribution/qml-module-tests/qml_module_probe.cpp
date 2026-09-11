// SPDX-License-Identifier: GPL-3.0-only
// Compile the selected real QML using QCoreApplication; no native windows open.
#include <QCoreApplication>
#include <QDebug>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QVariant>

// Test-only registration boundary for the enabled upstream module. No model is
// registered in the offline case, matching the actual Muse extensions stub.
class EnabledExtensionsModel : public QObject
{
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE QVariantList extensionsList() { return {}; }
    Q_INVOKABLE void clicked(const QString&) {}
};

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    if (app.arguments().contains(QStringLiteral("--enabled-model"))) {
        qmlRegisterType<EnabledExtensionsModel>("Muse.Extensions", 1, 0, "DevExtensionsListModel");
    }
    QQmlEngine engine;
    QQmlComponent view(&engine,
        QUrl(QStringLiteral("qrc:/qt/qml/Audacity/AppShell/DevTools/Extensions/ExtensionsListView.qml")));
    if (!view.isReady()) {
        for (const auto& error : view.errors()) {
            qCritical().noquote() << error.toString();
        }
        return 1;
    }
    QQmlComponent namedView(&engine);
    namedView.setData("import Audacity.AppShell 1.0\nExtensionsListView {}", QUrl());
    if (!namedView.isReady()) {
        for (const auto& error : namedView.errors()) {
            qCritical().noquote() << error.toString();
        }
        return 1;
    }
    qInfo() << "Production ExtensionsListView QML compiled";
    return 0;
}

#include "qml_module_probe.moc"
