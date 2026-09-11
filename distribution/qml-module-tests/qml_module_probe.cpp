// SPDX-License-Identifier: GPL-3.0-only
// Instantiate the selected real QML offscreen; no native windows open.
#include <QDebug>
#include <QCryptographicHash>
#include <QFile>
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
    // The two counterfactual probes intentionally use the same executable and
    // qrc URL. Never allow one process's compiled-QML cache to satisfy the
    // other process from different embedded source bytes.
    qputenv("QML_DISABLE_DISK_CACHE", "1");
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);
    QFile selected(QStringLiteral(":/qt/qml/Audacity/AppShell/DevTools/Extensions/ExtensionsListView.qml"));
    if (!selected.open(QIODevice::ReadOnly)) {
        std::fputs("Selected QML resource cannot be opened\n", stderr);
        return 1;
    }
    const auto selectedHash = QCryptographicHash::hash(selected.readAll(), QCryptographicHash::Sha256).toHex();
    if (selectedHash != QByteArrayLiteral(WAVEQUAY_SELECTED_VIEW_SHA256)) {
        std::fprintf(stderr, "Selected QML resource hash mismatch: %s\n", selectedHash.constData());
        return 1;
    }
    std::fprintf(stderr, "Selected QML SHA256 %s\n", selectedHash.constData());
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
            std::fprintf(stderr, "%s\n", qPrintable(error.toString()));
        }
        return 1;
    }
    QQmlComponent namedView(&engine);
    namedView.setData("import Audacity.AppShell 1.0\nExtensionsListView {}", QUrl());
    if (!namedView.isReady()) {
        for (const auto& error : namedView.errors()) {
            std::fprintf(stderr, "%s\n", qPrintable(error.toString()));
        }
        return 1;
    }
    std::unique_ptr<QObject> instance(namedView.create());
    if (!instance) {
        for (const auto& error : namedView.errors()) {
            std::fprintf(stderr, "%s\n", qPrintable(error.toString()));
        }
        return 1;
    }
    std::fputs("Production ExtensionsListView QML instantiated\n", stderr);
    return 0;
}

#include "qml_module_probe.moc"
