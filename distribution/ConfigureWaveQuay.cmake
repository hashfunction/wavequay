# Apply before dependency acquisition; explicitly conflicting options are errors.
option(AU_TRIEFLOW_DISTRIBUTION "Build the offline WaveQuay distribution" OFF)
if(AU_TRIEFLOW_DISTRIBUTION)
    foreach(_option IN ITEMS AU_BUILD_CLOUD_AUDIOCOM AU_BUILD_USAGEINFO_MODULE
            AU_USE_LIBCURL MUSE_MODULE_CLOUD MUSE_MODULE_CLOUD_MUSESCORECOM
            MUSE_MODULE_NETWORK MUSE_MODULE_UPDATE MUSE_MODULE_EXTENSIONS
            MUSE_MODULE_DIAGNOSTICS_CRASHPAD_CLIENT MUSE_MODULE_AUDIO_ASIO
            has_sentry_reporting audacity_has_sentry_reporting has_crashreports audacity_has_crashreports)
        if(DEFINED ${_option} AND ${_option})
            message(FATAL_ERROR "WaveQuay forbids ${_option}=ON; use a clean offline build directory")
        endif()
        set(${_option} OFF CACHE BOOL "Disabled for WaveQuay" FORCE)
    endforeach()
    foreach(_url IN ITEMS MUSE_MODULE_DIAGNOSTICS_CRASHREPORT_URL CRASH_REPORT_URL SENTRY_DSN_KEY SENTRY_HOST SENTRY_PROJECT)
        if(DEFINED ${_url} AND NOT "${${_url}}" STREQUAL "")
            message(FATAL_ERROR "WaveQuay forbids ${_url}")
        endif()
        set(${_url} "" CACHE STRING "Disabled for WaveQuay" FORCE)
    endforeach()
endif()
