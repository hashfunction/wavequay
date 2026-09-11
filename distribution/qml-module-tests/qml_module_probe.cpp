// SPDX-License-Identifier: GPL-3.0-only
// Instantiate the selected real QML offscreen; no native windows open.
#include <QDebug>
#include <QGuiApplication>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
#include <QVariant>
#include <cstdio>
#include <memory>

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
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);
    if (app.arguments().contains(QStringLiteral("--enabled-model"))) {
        qmlRegisterType<EnabledExtensionsModel>("Muse.Extensions", 1, 0, "DevExtensionsListModel");
    }
    QQmlEngine engine;
    const QVariantMap theme {
        { QStringLiteral("backgroundSecondaryColor"), QStringLiteral("#ffffff") },
    };
    const QVariantMap ui {
        { QStringLiteral("theme"), theme },
    };
    engine.rootContext()->setContextProperty(QStringLiteral("ui"), ui);
    engine.globalObject().setProperty(QStringLiteral("qsTrc"),
        engine.evaluate(QStringLiteral("(function(context, text) { return text; })")));
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
    std::unique_ptr<QObject> instance(namedView.create());
    if (!instance) {
        for (const auto& error : namedView.errors()) {
            qCritical().noquote() << error.toString();
        }
        return 1;
    }
    std::fputs("Production ExtensionsListView QML instantiated\n", stderr);
    return 0;
}

#include "qml_module_probe.moc"
