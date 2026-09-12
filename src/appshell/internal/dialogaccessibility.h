// SPDX-License-Identifier: GPL-3.0-only
#pragma once

#include "framework/accessibility/iqaccessibleinterfaceregister.h"
#include "framework/accessibility/internal/accessiblewindowinterface.h"

namespace au::appshell {
class DialogAccessibleWindow final : public muse::accessibility::AccessibleWindowInterface
{
public:
    explicit DialogAccessibleWindow(QObject* window)
        : AccessibleWindowInterface(window) {}

    int childCount() const override { return static_cast<int>(windowChildren().size()); }
    QAccessibleInterface* child(int index) const override { return windowChildren().value(index, nullptr); }
    int indexOfChild(const QAccessibleInterface* child) const override
    {
        const auto children = windowChildren();
        for (int index = 0; index < children.size(); ++index)
            if (children[index] == child) return index;
        return -1;
    }
    QAccessibleInterface* focusChild() const override
    {
        for (auto child : windowChildren()) {
            auto object = qobject_cast<muse::accessibility::AccessibleObject*>(child->object());
            if (!child->isValid() || (object && object->item()->accessibleIgnored())) continue;
            if (child->state().focused) return child;
            auto focused = child->focusChild();
            if (focused && focused->window() == window()) return focused;
        }
        return nullptr;
    }

private:
    QList<QAccessibleInterface*> windowChildren() const
    {
        // Muse resolves a transient dialog through the main controller. Its
        // root holds controls from both windows. UIA finds siblings via each
        // child's parent(), so borrowing main-window children breaks traversal.
        QList<QAccessibleInterface*> children;
        for (int index = 0; index < AccessibleWindowInterface::childCount(); ++index) {
            auto child = AccessibleWindowInterface::child(index);
            if (child && child->window() == window() && child->parent() == this) children.append(child);
        }
        return children;
    }
};

inline QAccessibleInterface* applicationWindowAccessibleFactory(const QString& className, QObject* object)
{
    // Qt Templates registers its own QQuickApplicationWindow getter after Muse.
    // Resolve the actual derived QML class first, without generated type numbers.
    if (!object || !object->inherits("QQuickApplicationWindow")
        || className != QLatin1String(object->metaObject()->className())
        || className == QLatin1String("QQuickApplicationWindow")) return nullptr;
    return new DialogAccessibleWindow(object);
}

inline void registerDialogAccessibility(muse::accessibility::IQAccessibleInterfaceRegister& registry)
{
    // WindowView creates QQuickView popups. Register that concrete class so
    // Qt's later QQuickWindow factory cannot replace Muse's tree/focus route.
    // Extend the existing Muse provider without changing the pinned framework.
    if (registry.interfaceGetter("QQuickWindow")) {
        registry.registerInterfaceGetter("QQuickView", [](QObject* window) -> QAccessibleInterface* {
            return new DialogAccessibleWindow(window);
        });
        QAccessible::installFactory(applicationWindowAccessibleFactory);
    }
}
}
