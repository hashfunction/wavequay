// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
#pragma once

#include "thirdparty/kors_logger/src/logger.h"
#include <functional>
#include <string_view>

namespace wavequay {
inline constexpr std::size_t StartupDiagnosticByteLimit = 2 * 1024 * 1024;
using DiagnosticWriter = std::function<bool(std::string_view)>;
// Explicit disposable-CI opt-in. Does not read settings or change logger levels.
bool installStartupDiagnostics(kors::logger::Logger& logger, const std::string& configuredLogDirectory,
                               std::string_view ci, std::string_view requested,
                               DiagnosticWriter writer = {}) noexcept;
}
