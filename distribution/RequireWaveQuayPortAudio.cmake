# The pinned resolver explicitly supports per-library resolve overrides. Keep
# its target/install registration but build PortAudio from our owned recipe.
function(portaudio_resolve_override mode local_path os arch version config)
    set(_EXTDEPS_ROOT "${PROJECT_SOURCE_DIR}/distribution")
    _extdeps_build(portaudio "${local_path}" "${os}" "${arch}" "${config}")
    _extdeps_resolve_installed(portaudio "${local_path}" "${os}" "${config}")
endfunction()

function(wavequay_require_portaudio)
    set(EXTDEPS_OVERRIDE_PORTAUDIO REBUILD)
    require_dep(portaudio REBUILD)
    foreach(field INCLUDE_DIRS LIBRARIES INSTALL_LIBRARIES)
        set(portaudio_${field} "${portaudio_${field}}" PARENT_SCOPE)
    endforeach()
endfunction()
