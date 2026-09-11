/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow LLC
 */
import QtQuick
import Muse.UiComponents

Rectangle {
    color: ui.theme.backgroundSecondaryColor

    StyledTextLabel {
        anchors.centerIn: parent
        text: qsTrc("appshell", "Extensions are not available in this build.")
    }
}
