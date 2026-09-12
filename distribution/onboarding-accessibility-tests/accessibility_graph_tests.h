// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <QFile>
#include <QDir>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QQmlComponent>
#include <QRegularExpression>
#include <QTemporaryDir>
#include <QUuid>
#include "src/appshell/internal/accessibilitygraphdiagnostics.h"

// Deliberately inconsistent interfaces test the real bounded graph reader.
// The normal probe below also supplies the actual Qt/Muse graph in both orders.
struct GraphFixtureInterface : QAccessibleInterface {
    QObject objectValue;
    QWindow windowValue;
    GraphFixtureInterface* parentValue = nullptr;
    QList<QAccessibleInterface*> children;
    mutable int reads = 0;
    bool valid = true;
    bool isValid() const override { ++reads; return valid; }
    QObject* object() const override { return const_cast<QObject*>(&objectValue); }
    QWindow* window() const override { return const_cast<QWindow*>(&windowValue); }
    QAccessibleInterface* parent() const override { return parentValue; }
    QAccessibleInterface* child(int index) const override { ++reads; return children.value(index); }
    int childCount() const override { return children.size(); }
    int indexOfChild(const QAccessibleInterface* child) const override { return children.indexOf(const_cast<QAccessibleInterface*>(child)); }
    QAccessibleInterface* childAt(int, int) const override { std::abort(); }
    QRect rect() const override { std::abort(); }
    QAccessible::Role role() const override { return QAccessible::StaticText; }
    QAccessible::State state() const override { return {}; }
    QString text(QAccessible::Text) const override { std::abort(); }
    void setText(QAccessible::Text, const QString&) override { std::abort(); }
};

static QString graphFixturePath(QTemporaryDir& temporary) {
    const QString root = QFileInfo(temporary.path()).canonicalFilePath() + "/private-environment";
    require(QDir().mkpath(root + "/Temp"), "graph fixture directory");
    QFile marker(root + "/.waveweft-consumer-owner");
    require(marker.open(QIODevice::WriteOnly | QIODevice::NewOnly), "graph fixture exclusive marker");
    marker.write(QUuid::createUuid().toString(QUuid::WithoutBraces).toUtf8()); marker.close();
    return root + "/Temp/accessibility-graph.jsonl";
}
static QList<QJsonObject> graphRecords(const QString& path) {
    QFile file(path); require(file.open(QIODevice::ReadOnly), "graph fixture output exists");
    const auto bytes = file.readAll();
    require(bytes.size() <= 8 * 1024 * 1024 && bytes.endsWith('\n'), "graph byte/newline cap");
    QList<QJsonObject> rows;
    for (auto line : bytes.split('\n')) if (!line.isEmpty()) {
        QJsonParseError error; auto doc = QJsonDocument::fromJson(line, &error);
        require(error.error == QJsonParseError::NoError && doc.isObject(), "graph JSONL parses");
        rows.append(doc.object());
    }
    return rows;
}
// Uses actual Qt filename-generated metaobjects and the exact QObject parenting
// statement in WindowView::initView. It does not substitute a Muse provider.
struct GraphFixtureView : QQuickView {
    QAccessibleInterface* root = nullptr;
    mutable int rootReads = 0;
    QAccessibleInterface* accessibleRoot() const override { ++rootReads; return root; }
};
static void graphTargetTimerTests(QAccessibleInterface* actualRoot) {
    using au::appshell::AccessibilityGraphDiagnostics;
    require(actualRoot && actualRoot->window(), "actual Muse popup required");
    QQmlEngine ownerEngine;
    const auto owner = [&](const char* filename) {
        QQmlComponent component(&ownerEngine);
        component.setData("import QtQml\nQtObject { property int scene: 1 }", QUrl::fromLocalFile(filename));
        auto result = std::unique_ptr<QObject>(component.create());
        require(bool(result), "Qt generates actual QML owner class");
        return result;
    };
    auto mainOwner = owner("/graph-fixture/Main.qml");
    auto exportOwner = owner("/graph-fixture/ExportDialog.qml");
    auto similarOwner = owner("/graph-fixture/ExportDialogExtra.qml");
    const QString generatedClass = exportOwner->metaObject()->className();
    require(QRegularExpression("^ExportDialog_QMLTYPE_[0-9]+$").match(generatedClass).hasMatch(),
            "actual ExportDialog filename generates the selected owner class");
    QList<GraphFixtureInterface*> nodes;
    QList<QAccessible::Id> ids;
    for (int index = 0; index < 300; ++index) {
        nodes.append(new GraphFixtureInterface);
        ids.append(QAccessible::registerAccessibleInterface(nodes.back()));
        if (index) { nodes.front()->children.append(nodes.back()); nodes.back()->parentValue = nodes.front(); }
    }
    {
        QTemporaryDir broadDirectory;
        const auto broadPath = graphFixturePath(broadDirectory);
        AccessibilityGraphDiagnostics broad(broadPath);
        for (int tick = 0; tick < 8 && broad.isOpen(); ++tick) broad.snapshot({nodes.front()});
        require(!broad.isOpen(), "eight large pre-export graphs exhaust the original byte budget");
        const auto broadRows = graphRecords(broadPath);
        require(broadRows[broadRows.size()-2]["reason"] == "byte-limit", "large graph stops at the original byte cap");
    }
    GraphFixtureView mainView, similarView, hiddenView, uncreatedView;
    mainView.root = similarView.root = hiddenView.root = uncreatedView.root = nodes.front();
    mainView.QObject::setParent(mainOwner.get());
    mainView.setTitle("Export audio"); mainOwner->setObjectName(generatedClass);
    similarView.QObject::setParent(similarOwner.get());
    hiddenView.QObject::setParent(exportOwner.get());
    uncreatedView.QObject::setParent(exportOwner.get());
    QWindow wrongWindowType;
    wrongWindowType.QObject::setParent(exportOwner.get());
    mainView.show(); similarView.show(); hiddenView.show(); hiddenView.hide(); wrongWindowType.show();
    require(mainView.handle() && hiddenView.handle() && !uncreatedView.handle(), "native fixture window states");
    QTemporaryDir temporary;
    const auto path = graphFixturePath(temporary);
    qputenv("WAVEWEFT_ACCESSIBILITY_GRAPH", path.toUtf8()); qputenv("CI", "true");
    AccessibilityGraphDiagnostics::startFromEnvironment();
    AccessibilityGraphDiagnostics* reader = nullptr;
    for (auto* child : qApp->children())
        if (auto* diagnostic = dynamic_cast<AccessibilityGraphDiagnostics*>(child)) reader = diagnostic;
    require(reader && reader->isOpen(), "explicit environment starts the production timer");
    // Eight real timer ticks precede the target. The original 300-node main
    // graph would consume the original 8 MiB cap before this observation ends.
    for (int tick = 1; tick <= 8; ++tick) {
        require(waitUntil([&] {
            for (const auto& row : graphRecords(path))
                if (row["kind"] == "snapshot-end" && row["snapshot"].toInt() >= tick) return true;
            return false;
        }), "production QTimer records bounded pre-export window metadata");
        require(mainView.rootReads == 0 && similarView.rootReads == 0,
                "pre-export and similarly named windows must not query accessibleRoot");
        require(reader->isOpen(), "late export retains the graph budget");
    }
    bool mainMetadata = false, wrongTypeMetadata = false;
    for (const auto& row : graphRecords(path)) {
        require(row["kind"] != "query" && row["kind"] != "node", "pre-export records contain metadata only");
        if (row["kind"] != "window") continue;
        require(row["selected"] == false, "pre-export metadata reports unselected windows");
        const auto chain = row["ownerClassChain"].toArray();
        require(chain.size() <= 8, "owner superclass metadata bounded");
        mainMetadata |= row["window"].toDouble() == double(mainView.winId())
            && row["ownerClass"] == mainOwner->metaObject()->className();
        wrongTypeMetadata |= row["window"].toDouble() == double(wrongWindowType.winId())
            && row["ownerClass"] == generatedClass;
    }
    require(mainMetadata && wrongTypeMetadata && QFileInfo(path).size() < 128 * 1024,
            "all observed owner classes are retained without large graph queries");
    auto* target = actualRoot->window();
    auto* previousParent = target->QObject::parent();
    target->QObject::setParent(exportOwner.get()); // exact WindowView::initView relationship
    require(target->QObject::parent() == exportOwner.get() && !target->parent(),
            "QObject controller ownership is distinct from QWindow native parenting");
    for (int capture = 1; capture <= 3; ++capture) {
        require(waitUntil([&] {
            int starts = 0;
            for (const auto& row : graphRecords(path))
                if (row["kind"] == "query" && row["operation"] == "window-root" && row["phase"] == "begin") ++starts;
            return starts >= capture;
        }), "late actual Muse export-owned popup is queried by the production timer");
    }
    require(!reader->isOpen(), "three target captures stop the timer");
    target->QObject::setParent(previousParent);
    delete reader;
    int selected = 0, rootReads = 0; bool museSeen = false;
    const auto records = graphRecords(path);
    for (const auto& row : records) {
        if (row["kind"] == "window" && row["selected"].toBool()) {
            ++selected;
            require(row["window"].toDouble() == double(target->winId()) && row["ownerClass"] == generatedClass,
                    "only the exact actual export-owned QQuickView is selected");
        }
        rootReads += row["kind"] == "query" && row["operation"] == "window-root" && row["phase"] == "begin";
        museSeen |= row["kind"] == "node" && row["objectClass"] == "muse::accessibility::AccessibleObject";
    }
    require(selected == 3 && rootReads == 3 && museSeen, "three target graphs retain actual Muse providers");
    require(records[records.size()-2]["reason"] == "capture-limit" && records.back()["kind"] == "end",
            "capture limit terminates explicitly without claiming success");
    require(mainView.rootReads == 0 && similarView.rootReads == 0 && hiddenView.rootReads == 0
            && uncreatedView.rootReads == 0 && !uncreatedView.handle(), "unselected and hidden windows stay unqueried");
    QFile file(path); require(file.open(QIODevice::ReadOnly), "read targeted graph bytes"); const auto bytes = file.readAll();
    require(!bytes.contains("Export audio"), "window titles remain omitted");
    if (qEnvironmentVariableIsSet("WAVE_GRAPH_TARGET_TEST_RECORD")) {
        QFile retained(qEnvironmentVariable("WAVE_GRAPH_TARGET_TEST_RECORD"));
        require(retained.open(QIODevice::WriteOnly | QIODevice::NewOnly), "exclusive target replay output");
        require(retained.write(bytes) == bytes.size(), "target replay retains original writer bytes");
    }
    // Stack windows must relinquish QObject ownership before their owners die.
    mainView.QObject::setParent(nullptr); similarView.QObject::setParent(nullptr);
    hiddenView.QObject::setParent(nullptr); uncreatedView.QObject::setParent(nullptr); wrongWindowType.QObject::setParent(nullptr);
    for (auto id : ids) QAccessible::deleteAccessibleInterface(id);
    qInfo() << "Accessibility graph delayed export target fixture passed";
}
static void graphDiagnosticTests(QAccessibleInterface* actualRoot = nullptr) {
    using au::appshell::AccessibilityGraphDiagnostics;
    QTemporaryDir temporary;
    const auto path = graphFixturePath(temporary);
    const auto oldPath = qgetenv("WAVEWEFT_ACCESSIBILITY_GRAPH"), oldCI = qgetenv("CI");
    qunsetenv("WAVEWEFT_ACCESSIBILITY_GRAPH");
    const auto childrenBefore = qApp->children().size();
    AccessibilityGraphDiagnostics::startFromEnvironment();
    require(qApp->children().size() == childrenBefore && !QFile::exists(path), "dormant mode performs no allocation or output");
    qputenv("WAVEWEFT_ACCESSIBILITY_GRAPH", path.toUtf8()); qputenv("CI", "false");
    AccessibilityGraphDiagnostics::startFromEnvironment();
    require(!QFile::exists(path), "diagnostic path without explicit disposable CI is dormant");
    if (oldPath.isNull()) qunsetenv("WAVEWEFT_ACCESSIBILITY_GRAPH"); else qputenv("WAVEWEFT_ACCESSIBILITY_GRAPH", oldPath);
    if (oldCI.isNull()) qunsetenv("CI"); else qputenv("CI", oldCI);
    graphTargetTimerTests(actualRoot);
    if (oldPath.isNull()) qunsetenv("WAVEWEFT_ACCESSIBILITY_GRAPH"); else qputenv("WAVEWEFT_ACCESSIBILITY_GRAPH", oldPath);
    if (oldCI.isNull()) qunsetenv("CI"); else qputenv("CI", oldCI);
    auto* first = new GraphFixtureInterface;
    auto* second = new GraphFixtureInterface;
    first->objectValue.setObjectName("private-object-name-must-not-be-read");
    first->windowValue.setTitle("private-window-title-must-not-be-read");
    first->children = {second, first, second}; // self cycle and duplicate edge
    second->parentValue = second; // wrong reciprocal parent/index
    second->children = {first};
    const auto firstId = QAccessible::registerAccessibleInterface(first);
    const auto secondId = QAccessible::registerAccessibleInterface(second);
    {
        AccessibilityGraphDiagnostics reader(path);
        require(reader.isOpen(), "exclusive owned graph output opens");
        require(!first->windowValue.handle(), "fixture starts without native window");
        reader.snapshot({first});
        const auto firstReads = first->reads;
        reader.snapshot({first});
        require(first->reads > firstReads, "each snapshot has a fresh visited set");
        require(first->reads < 50 && second->reads < 50, "cycles terminate without recursive reads");
        require(!first->windowValue.handle(), "diagnostics do not create native windows");
        if (actualRoot) reader.snapshot({actualRoot});
        reader.finish();
    }
    const auto rows = graphRecords(path);
    bool repeated = false, mismatch = false, actual = !actualRoot;
    for (const auto& row : rows) {
        if (row["kind"] == "edge") {
            repeated |= row["repeated"].toBool();
            mismatch |= row["childParent"].toDouble() != row["id"].toDouble();
        }
        actual |= row["kind"] == "node" && row["objectClass"] == "muse::accessibility::AccessibleObject";
    }
    require(rows.front()["kind"] == "started" && rows.back()["kind"] == "end", "graph start/end records");
    require(repeated && mismatch && actual, "real graph records preserve repeated and malformed edges and Muse objects");
    QFile original(path); require(original.open(QIODevice::ReadOnly), "read original graph"); const auto before = original.readAll(); original.close();
    require(!before.contains("private-object") && !before.contains("private-window"), "graph omits object names and window titles");
    AccessibilityGraphDiagnostics refused(path);
    require(!refused.isOpen(), "existing graph output is refused");
    require(original.open(QIODevice::ReadOnly), "read preserved graph"); require(original.readAll() == before, "refused output remains unchanged"); original.close();
    if (qEnvironmentVariableIsSet("WAVE_GRAPH_TEST_RECORD")) {
        QFile retained(qEnvironmentVariable("WAVE_GRAPH_TEST_RECORD"));
        require(retained.open(QIODevice::WriteOnly | QIODevice::NewOnly), "exclusive actual writer replay output");
        require(retained.write(before) == before.size(), "actual writer replay bytes");
    }
    AccessibilityGraphDiagnostics relative("relative.jsonl");
    require(!relative.isOpen(), "relative graph output refused");
    QTemporaryDir unownedDirectory;
    auto unownedPath = graphFixturePath(unownedDirectory);
    require(QFile::remove(QFileInfo(unownedPath).dir().filePath("../.waveweft-consumer-owner")), "remove test owner");
    AccessibilityGraphDiagnostics unowned(unownedPath);
    require(!unowned.isOpen(), "unowned graph output refused");
    QTemporaryDir cappedDirectory;
    const auto cappedPath = graphFixturePath(cappedDirectory);
    {
        AccessibilityGraphDiagnostics capped(cappedPath);
        first->children.clear();
        for (int index = 0; index < 10000 && capped.isOpen(); ++index) capped.snapshot({first});
        require(!capped.isOpen(), "byte cap stops collecting");
    }
    const auto cappedRows = graphRecords(cappedPath);
    require(cappedRows[cappedRows.size()-2]["kind"] == "truncated"
            && cappedRows[cappedRows.size()-2]["reason"] == "byte-limit"
            && cappedRows.back()["kind"] == "end", "byte cap has explicit terminal truncation/end");
    for (bool deep : {false, true}) {
        QTemporaryDir boundDirectory;
        const auto boundPath = graphFixturePath(boundDirectory);
        QList<GraphFixtureInterface*> nodes;
        QList<QAccessible::Id> ids;
        for (int index = 0; index < (deep ? 40 : 300); ++index) {
            nodes.append(new GraphFixtureInterface);
            ids.append(QAccessible::registerAccessibleInterface(nodes.back()));
            if (index) {
                auto* parent = nodes[deep ? index-1 : 0];
                parent->children.append(nodes.back()); nodes.back()->parentValue = parent;
            }
        }
        {
            AccessibilityGraphDiagnostics bounded(boundPath);
            bounded.snapshot({nodes.front()}); bounded.finish();
        }
        bool limitSeen = false;
        for (const auto& row : graphRecords(boundPath)) {
            if (row["kind"] == "truncated" && row["reason"] == (deep ? "depth-limit" : "node-limit")) limitSeen = true;
            if (row["kind"] == "snapshot-end") require(row["nodes"].toInt() <= 256, "node budget enforced");
        }
        require(limitSeen, "depth/node limit emits actual truncation");
        for (auto id : ids) QAccessible::deleteAccessibleInterface(id);
    }
    QAccessible::deleteAccessibleInterface(secondId);
    QAccessible::deleteAccessibleInterface(firstId);
    qInfo() << "Accessibility graph production reader fixture passed";
}
