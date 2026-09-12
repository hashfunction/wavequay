// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <QAccessible>
#include <QElapsedTimer>
#include <QFile>
#include <QJsonObject>
#include <QSet>
#include <QTimer>

namespace au::appshell {
// Opt-in observations only. Never installed as an accessibility callback.
class AccessibilityGraphDiagnostics final : public QObject {
public:
    explicit AccessibilityGraphDiagnostics(const QString& path, QObject* parent = nullptr);
    ~AccessibilityGraphDiagnostics() override;
    static void startFromEnvironment();
    bool isOpen() const { return m_file.isOpen() && !m_stopped; }
    void snapshot(const QList<QAccessibleInterface*>& roots);
    void finish();
private:
    struct Stopped {};
    void captureWindows();
    bool write(QJsonObject row, bool terminal = false);
    void truncate(const char* reason);
    void visit(QAccessibleInterface* iface, int depth);
    static qint64 existingWindowId(QWindow* window);
    static QString className(QObject* object);
    template<class Function> auto read(const char* operation, QAccessible::Id id, int index, Function function) {
        if (!isOpen()) throw Stopped{};
        if (m_clock.elapsed() >= 90000) { truncate("time-limit"); finish(); throw Stopped{}; }
        QJsonObject row{{"kind", "query"}, {"operation", operation}, {"id", double(id)}, {"index", index}, {"phase", "begin"}};
        if (!write(row)) throw Stopped{};
        auto result = function();
        row["phase"] = "end";
        if (!write(row)) throw Stopped{};
        return result;
    }
    QFile m_file;
    QTimer m_timer;
    QElapsedTimer m_clock;
    QSet<QAccessibleInterface*> m_visited;
    int m_snapshot = 0;
    int m_sequence = 0;
    bool m_stopped = false;
    bool m_inSnapshot = false;
};
}
