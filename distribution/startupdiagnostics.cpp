// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
#ifdef _WIN32
#include <Windows.h>
#else
#include <sys/stat.h>
#include <unistd.h>
#endif
#include "startupdiagnostics.h"
#include <algorithm>
#include <memory>

namespace wavequay {
namespace {
using namespace kors::logger;
constexpr const char* SinkName = "WaveWeftStartupStderr";
constexpr std::string_view LimitMessage = "[WaveWeft startup] diagnostic byte limit reached\n";

bool writeRedirectedStderr(std::string_view text)
{
#ifdef _WIN32
    const HANDLE pipe = GetStdHandle(STD_ERROR_HANDLE);
    // GUI-subsystem CRT stderr can be unopened even with redirected Win32
    // handles. Use only the pipe supplied by our observer, never a file path.
    if (pipe == INVALID_HANDLE_VALUE || !pipe || GetFileType(pipe) != FILE_TYPE_PIPE) return false;
    while (!text.empty()) {
        DWORD written = 0;
        const DWORD size = static_cast<DWORD>(std::min<std::size_t>(text.size(), 4096));
        if (!WriteFile(pipe, text.data(), size, &written, nullptr) || written == 0) return false;
        text.remove_prefix(written);
    }
#else
    struct stat info {};
    if (fstat(STDERR_FILENO, &info) != 0 || !S_ISFIFO(info.st_mode)) return false;
    while (!text.empty()) {
        const auto written = ::write(STDERR_FILENO, text.data(), text.size());
        if (written <= 0) return false;
        text.remove_prefix(static_cast<std::size_t>(written));
    }
#endif
    return true;
}

class StartupStderrDest final : public LogDest {
public:
    explicit StartupStderrDest(DiagnosticWriter writer)
        : LogDest(LogLayout("${message}")), m_writer(std::move(writer)) {}
    std::string name() const override { return SinkName; }
    bool begin(const std::string& directory) noexcept
    {
        try { return writeBounded("[WaveWeft startup] configured-log-directory: " + directory.substr(0, 4096) + "\n"); }
        catch (...) { m_disabled = true; return false; }
    }
    void write(const LogMsg& message) override
    {
        // Do not mirror info/debug settings, project contents or profiler dumps.
        // The source guard limits this sink to a fresh, no-media CI launch.
        if (message.type != Logger::ERRR && message.type != Logger::WARN) return;
        try {
            std::string value = "[WaveWeft startup] " + std::string(message.type) + " | "
                + std::string(message.tag.substr(0, 128)) + " | " + message.message.substr(0, 8192);
            if (message.message.size() > 8192) value += " [message truncated]";
            writeBounded(value + "\n");
        } catch (...) { m_disabled = true; }
    }
private:
    bool writeBounded(std::string_view value) noexcept
    {
        if (m_disabled) return false;
        try {
            if (value.size() > StartupDiagnosticByteLimit - LimitMessage.size() - m_written) {
                m_writer(LimitMessage);
                m_disabled = true;
                return false;
            }
            if (!m_writer(value)) { m_disabled = true; return false; }
            m_written += value.size();
            return true;
        } catch (...) { m_disabled = true; return false; }
    }
    DiagnosticWriter m_writer;
    std::size_t m_written = 0;
    bool m_disabled = false;
};
}

bool installStartupDiagnostics(kors::logger::Logger& logger, const std::string& configuredLogDirectory,
                               std::string_view ci, std::string_view requested, DiagnosticWriter writer) noexcept
{
    if (ci != "true" || requested != "1") return false;
    try {
        for (const auto* dest : logger.dests()) if (dest->name() == SinkName) return true;
        auto dest = std::make_unique<StartupStderrDest>(writer ? std::move(writer) : writeRedirectedStderr);
        if (!dest->begin(configuredLogDirectory)) return false;
        logger.addDest(dest.get());
        dest.release(); // Logger owns and destroys destinations.
        return true;
    } catch (...) { return false; }
}
}
