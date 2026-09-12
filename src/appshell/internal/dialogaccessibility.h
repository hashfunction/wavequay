// SPDX-License-Identifier: GPL-3.0-only
#pragma once

#include "framework/accessibility/iqaccessibleinterfaceregister.h"

namespace au::appshell {
inline void registerDialogAccessibility(muse::accessibility::IQAccessibleInterfaceRegister& registry)
{
    // WindowView creates QQuickView popups. Register that concrete class so
    // Qt's later QQuickWindow factory cannot replace Muse's tree/focus route.
    // Reuse the provider already installed by the accessibility module.
    if (auto windowGetter = registry.interfaceGetter("QQuickWindow")) {
        registry.registerInterfaceGetter("QQuickView", windowGetter);
    }
}
}
