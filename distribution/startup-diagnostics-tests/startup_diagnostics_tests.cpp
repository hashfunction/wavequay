// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
#include "startupdiagnostics.h"
#include "logdefdest.h"
#include <QCoreApplication>
#include <QDebug>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

using namespace kors::logger;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
int main(int argc, char** argv)
{
    try {
        QCoreApplication application(argc, argv);
        Logger& logger = *Logger::instance();
        logger.clearDests();
        if (argc == 2 && std::string(argv[1]) == "--real-pipe") {
            require(wavequay::installStartupDiagnostics(logger, "configured/native/logs", "true", "1"), "No real stderr pipe");
            logger.write(LogMsg(Logger::ERRR, "GuiApplication::loadMainWindow", Color::None, "Actual logger QML failure fixture"));
            return 0;
        }
        std::string captured;
        auto writer = [&](std::string_view value) { captured.append(value); return true; };
        for (const auto& flags : {std::pair{"", ""}, {"true", ""}, {"", "1"}, {"false", "1"}, {"true", "true"}}) {
            require(!wavequay::installStartupDiagnostics(logger, "never/read/profile", flags.first, flags.second, writer), "Unrequested capture enabled");
        }
        require(captured.empty() && logger.dests().empty(), "Disabled mode touched diagnostics");
        require(argc == 2, "Expected an owned temporary log fixture path");
        const std::filesystem::path originalFile(argv[1]);
        logger.addDest(new FileLogDest(originalFile.string(), LogLayout("${message}")));
        const std::size_t originalCount = logger.dests().size();
        require(wavequay::installStartupDiagnostics(logger, "exact-configured-\xC3\xA9/logs", "true", "1", writer), "Requested capture missing");
        require(captured.find("exact-configured-\xC3\xA9/logs") != std::string::npos, "Configured destination changed");
        require(logger.dests().size() == originalCount + 1, "Original logger destination was replaced");
        const auto before = captured;
        logger.write(LogMsg(Logger::INFO, "settings", Color::None, "PRIVATE_PROFILE_CONTENT"));
        logger.write(LogMsg(Logger::DEBG, "settings", Color::None, "PRIVATE_DEBUG_CONTENT"));
        require(captured == before, "Info/debug profile contents copied");
        logger.write(LogMsg(Logger::WARN, "Qt", Color::None, "qrc:/main.qml: missing property"));
        logger.write(LogMsg(Logger::ERRR, "GuiApplication::loadMainWindow", Color::None, "Failed to load main qml file, err: missing type"));
        require(captured.find("qrc:/main.qml: missing property") != std::string::npos, "Qt warning lost");
        require(captured.find("Failed to load main qml file, err: missing type") != std::string::npos, "Actual logger error lost");
        std::ifstream originalStream(originalFile);
        const std::string originalBytes((std::istreambuf_iterator<char>(originalStream)), std::istreambuf_iterator<char>());
        require(originalBytes.find("PRIVATE_PROFILE_CONTENT") != std::string::npos, "Original logger behavior changed");
        require(originalBytes.find("Failed to load main qml file, err: missing type") != std::string::npos, "Original file lost logger error");
        Logger::setIsCatchQtMsg(true);
        qWarning("qrc:/actual-qt-handler.qml: runtime warning fixture");
        qCritical("qrc:/actual-qt-handler.qml: runtime error fixture");
        Logger::setIsCatchQtMsg(false);
        require(captured.find("qrc:/actual-qt-handler.qml: runtime warning fixture") != std::string::npos, "Actual Qt warning handler lost output");
        require(captured.find("qrc:/actual-qt-handler.qml: runtime error fixture") != std::string::npos, "Actual Qt critical handler lost output");
        const auto count = logger.dests().size();
        require(wavequay::installStartupDiagnostics(logger, "same", "true", "1", writer), "Duplicate install failed");
        require(logger.dests().size() == count, "Duplicate logger destination installed");
        for (int i=0; i<600; ++i) logger.write(LogMsg(Logger::ERRR, "Qt", Color::None, std::string(16000, 'x')));
        require(captured.size() <= wavequay::StartupDiagnosticByteLimit, "Diagnostic budget exceeded");
        require(captured.find("diagnostic byte limit reached") != std::string::npos, "Truncation unreported");
        logger.clearDests();
        int attempts = 0;
        require(!wavequay::installStartupDiagnostics(logger, "configured", "true", "1", [&](std::string_view) { ++attempts; return false; }), "Broken pipe accepted");
        require(logger.dests().empty() && attempts == 1, "Failed writer registered a sink");
        std::cout << "PASS: explicit opt-in, configured destination, actual logger errors, privacy filter, duplicate/budget/broken-pipe checks\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
