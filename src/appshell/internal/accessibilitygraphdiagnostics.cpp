// SPDX-License-Identifier: GPL-3.0-only
#include "accessibilitygraphdiagnostics.h"
#include <QDir>
#include <QFileInfo>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QScopedValueRollback>
#include <QThread>
#include <QUuid>
#include <QWindow>
#include "framework/accessibility/internal/accessibleobject.h"

using namespace au::appshell;
namespace {
constexpr qint64 maxBytes = 8 * 1024 * 1024;
constexpr int maxNodes = 256;
constexpr int maxDepth = 32;
constexpr int maxDurationMs = 90000;
constexpr int maxTargetSnapshots = 3;
constexpr int maxOwnerClasses = 8;

QString metaClassName(const QMetaObject* meta)
{
    if (!meta) return {};
    static const QRegularExpression allowed(QStringLiteral("^[A-Za-z_][A-Za-z0-9_:]{0,127}$"));
    const auto text = QString::fromLatin1(meta->className());
    return allowed.match(text).hasMatch() ? text : QStringLiteral("InvalidClass");
}
}

AccessibilityGraphDiagnostics::AccessibilityGraphDiagnostics(const QString& path, QObject* parent) : QObject(parent), m_file(QDir::fromNativeSeparators(path))
{
    // Exact fresh private root is also checked by the native observer before
    // launch. NewOnly preserves even a file created between these checks.
    const auto normalized = QDir::fromNativeSeparators(path);
    const QFileInfo output(normalized), directory(output.absolutePath());
    if (!output.isAbsolute() || QDir::cleanPath(normalized) != normalized
        || output.fileName() != "accessibility-graph.jsonl" || directory.fileName() != "Temp"
        || directory.canonicalFilePath() != directory.absoluteFilePath()
        || directory.dir().dirName() != "private-environment") return;
    QFile marker(directory.dir().filePath(".waveweft-consumer-owner"));
    const QFileInfo markerInfo(marker);
    if (markerInfo.isSymLink() || !markerInfo.isFile() || markerInfo.size() != 36
        || !marker.open(QIODevice::ReadOnly)) return;
    const auto token = marker.read(37);
    if (QUuid(QString::fromLatin1(token)).toString(QUuid::WithoutBraces).toLatin1() != token) return;
    if (!m_file.open(QIODevice::WriteOnly | QIODevice::NewOnly)) return;
    m_clock.start();
    write({{"kind", "started"}, {"diagnosticOnly", true}, {"maxBytes", double(maxBytes)},
           {"maxNodes", maxNodes}, {"maxDepth", maxDepth}, {"maxDurationMs", maxDurationMs}});
    connect(&m_timer, &QTimer::timeout, this, [this] { captureWindows(); });
    connect(qApp, &QCoreApplication::aboutToQuit, this, [this] { finish(); });
}

AccessibilityGraphDiagnostics::~AccessibilityGraphDiagnostics() { finish(); }

void AccessibilityGraphDiagnostics::startFromEnvironment()
{
    // No graph inspection, allocation or timer in ordinary product runs.
    const auto path = qEnvironmentVariable("WAVEWEFT_ACCESSIBILITY_GRAPH");
    if (path.isEmpty()) return;
    if (qEnvironmentVariable("CI") != "true") return;
    auto* diagnostic = new AccessibilityGraphDiagnostics(path, qApp);
    if (diagnostic->isOpen()) diagnostic->m_timer.start(1000);
    else delete diagnostic;
}

qint64 AccessibilityGraphDiagnostics::existingWindowId(QWindow* window)
{
    // winId() can create a platform window: never call it without a handle.
    return window && window->handle() ? qint64(window->winId()) : 0;
}

QString AccessibilityGraphDiagnostics::className(QObject* object)
{
    return metaClassName(object ? object->metaObject() : nullptr);
}

bool AccessibilityGraphDiagnostics::write(QJsonObject row, bool terminal)
{
    if (!m_file.isOpen() || (m_stopped && !terminal)) return false;
    row["schemaVersion"] = 1;
    row["pid"] = double(QCoreApplication::applicationPid());
    row["sequence"] = ++m_sequence;
    row["snapshot"] = m_snapshot;
    row["elapsedMs"] = double(m_clock.elapsed());
    const auto bytes = QJsonDocument(row).toJson(QJsonDocument::Compact) + '\n';
    if (!terminal && m_file.pos() + bytes.size() + 1024 > maxBytes) {
        --m_sequence;
        truncate("byte-limit"); finish(); return false;
    }
    if (m_file.pos() + bytes.size() > maxBytes || m_file.write(bytes) != bytes.size() || !m_file.flush()) {
        m_stopped = true; m_timer.stop(); m_file.close(); return false;
    }
    return true;
}

void AccessibilityGraphDiagnostics::truncate(const char* reason)
{
    write({{"kind", "truncated"}, {"reason", reason}}, true);
}

void AccessibilityGraphDiagnostics::finish()
{
    m_timer.stop();
    if (m_file.isOpen()) {
        write({{"kind", "end"}}, true);
        m_file.close();
    }
    m_stopped = true;
}

void AccessibilityGraphDiagnostics::captureWindows()
{
    if (!isOpen() || m_inSnapshot || QThread::currentThread() != qApp->thread()) return;
    if (m_clock.elapsed() >= maxDurationMs) { truncate("time-limit"); finish(); return; }
    // QTimer runs on the GUI thread after the current event callback returns.
    // Observe only visible windows that already have a platform window.
    // WindowView::initView makes the controller the QQuickView's QObject
    // parent; QWindow::parent() instead describes native window parenting.
    // Never infer the target from a title, object name or accessible text.
    static const QRegularExpression exportOwner(QStringLiteral("^ExportDialog_QMLTYPE_[0-9]+$"));
    QScopedValueRollback<bool> guard(m_inSnapshot, true);
    ++m_snapshot;
    m_visited.clear();
    write({{"kind", "snapshot-start"}});
    bool targetCaptured = false;
    try {
        for (auto* window : QGuiApplication::topLevelWindows()) {
            if (!window->isVisible() || !window->handle()) continue;
            const auto handle = existingWindowId(window);
            auto* owner = window->QObject::parent();
            const auto windowClass = className(window), ownerClass = className(owner);
            QJsonArray ownerClasses;
            for (auto* meta = owner ? owner->metaObject() : nullptr;
                 meta && ownerClasses.size() < maxOwnerClasses; meta = meta->superClass()) {
                ownerClasses.append(metaClassName(meta));
            }
            const bool selected = windowClass == QStringLiteral("QQuickView") && exportOwner.match(ownerClass).hasMatch();
            if (!write({{"kind", "window"}, {"window", double(handle)}, {"objectClass", windowClass},
                        {"ownerClass", ownerClass}, {"ownerClassChain", ownerClasses}, {"selected", selected}})) return;
            if (!selected) continue;
            targetCaptured = true;
            auto* root = read("window-root", 0, -1, [window] { return window->accessibleRoot(); });
            if (root) visit(root, 0);
            if (m_visited.size() == maxNodes) { truncate("node-limit"); break; }
        }
        write({{"kind", "snapshot-end"}, {"nodes", m_visited.size()}});
        if (isOpen() && targetCaptured && ++m_targetSnapshots == maxTargetSnapshots) {
            truncate("capture-limit"); finish();
        }
    } catch (const Stopped&) { }
}

void AccessibilityGraphDiagnostics::snapshot(const QList<QAccessibleInterface*>& roots)
{
    if (!isOpen() || m_inSnapshot || QThread::currentThread() != qApp->thread()) return;
    if (m_clock.elapsed() >= maxDurationMs) { truncate("time-limit"); finish(); return; }
    QScopedValueRollback<bool> guard(m_inSnapshot, true);
    ++m_snapshot;
    m_visited.clear();
    write({{"kind", "snapshot-start"}});
    try {
        for (auto* root : roots) visit(root, 0);
        write({{"kind", "snapshot-end"}, {"nodes", m_visited.size()}});
    } catch (const Stopped&) { }
}

void AccessibilityGraphDiagnostics::visit(QAccessibleInterface* iface, int depth)
{
    if (!iface || m_visited.contains(iface)) return;
    if (m_clock.elapsed() >= maxDurationMs) { truncate("time-limit"); finish(); throw Stopped{}; }
    if (depth > maxDepth || m_visited.size() >= maxNodes) {
        truncate(depth > maxDepth ? "depth-limit" : "node-limit"); return;
    }
    m_visited.insert(iface);
    const auto id = read("unique-id", 0, -1, [iface] { return QAccessible::uniqueId(iface); });
    const bool valid = read("valid", id, -1, [iface] { return iface->isValid(); });
    if (!valid) { write({{"kind", "node"}, {"id", double(id)}, {"valid", false}, {"depth", depth}}); return; }
    auto* object = read("object", id, -1, [iface] { return iface->object(); });
    const auto role = read("role", id, -1, [iface] { return iface->role(); });
    const auto state = read("state", id, -1, [iface] { return iface->state(); });
    auto* parent = read("parent", id, -1, [iface] { return iface->parent(); });
    auto* window = read("window", id, -1, [iface] { return iface->window(); });
    const auto count = read("child-count", id, -1, [iface] { return iface->childCount(); });
    const auto parentId = parent ? read("parent-id", id, -1, [parent] { return QAccessible::uniqueId(parent); }) : 0;
    const bool parentValid = parent && read("parent-valid", id, -1, [parent] { return parent->isValid(); });
    const int parentIndex = parentValid ? read("parent-index", id, -1, [parent, iface] { return parent->indexOfChild(iface); }) : -1;
    auto* parentWindow = parentValid ? read("parent-window", id, -1, [parent] { return parent->window(); }) : nullptr;
    auto* windowRoot = window && window->handle() ? read("fragment-root", id, -1, [window] { return window->accessibleRoot(); }) : nullptr;
    const auto windowRootId = windowRoot ? read("fragment-root-id", id, -1, [windowRoot] { return QAccessible::uniqueId(windowRoot); }) : 0;
    QJsonObject row{{"kind", "node"}, {"id", double(id)}, {"depth", depth}, {"valid", valid},
        {"role", int(role)}, {"invisible", bool(state.invisible)}, {"disabled", bool(state.disabled)},
        {"parent", double(parentId)}, {"parentIndex", parentIndex}, {"childCount", count},
        {"parentWindow", double(existingWindowId(parentWindow))}, {"windowRoot", double(windowRootId)},
        {"window", double(existingWindowId(window))}, {"objectClass", className(object)}};
    if (auto* museObject = qobject_cast<muse::accessibility::AccessibleObject*>(object)) {
        auto* item = museObject->item();
        row["itemClass"] = className(dynamic_cast<QObject*>(item));
        row["itemOwnerClass"] = className(dynamic_cast<QObject*>(item) ? dynamic_cast<QObject*>(item)->parent() : nullptr);
        row["itemRole"] = int(read("item-role", id, -1, [item] { return item->accessibleRole(); }));
        row["ignored"] = read("item-ignored", id, -1, [item] { return item->accessibleIgnored(); });
        row["itemWindow"] = double(existingWindowId(read("item-window", id, -1, [item] { return item->accessibleWindow(); })));
    }
    write(row);
    if (count > maxNodes) truncate("child-count-limit");
    for (int index = 0; index < qMin(count, maxNodes); ++index) {
        auto* child = read("child", id, index, [iface, index] { return iface->child(index); });
        const auto childId = child ? read("child-id", id, index, [child] { return QAccessible::uniqueId(child); }) : 0;
        const bool childValid = child && read("child-valid", id, index, [child] { return child->isValid(); });
        auto* childParent = childValid ? read("child-parent", id, index, [child] { return child->parent(); }) : nullptr;
        const auto childParentId = childParent ? read("child-parent-id", id, index, [childParent] { return QAccessible::uniqueId(childParent); }) : 0;
        write({{"kind", "edge"}, {"id", double(id)}, {"index", index}, {"child", double(childId)},
               {"childParent", double(childParentId)}, {"valid", childValid}, {"repeated", m_visited.contains(child)}});
        if (childValid) visit(child, depth + 1);
    }
}
