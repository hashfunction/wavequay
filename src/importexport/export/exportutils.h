/*
 * Audacity: A Digital Audio Editor
 */
#pragma once

#include "types/val.h"
#include "iexporter.h"

namespace au::importexport::utils {
muse::Val matrixToVal(const std::vector<std::vector<bool> >& matrix);
std::vector<std::vector<bool> > valToMatrix(const muse::Val& val);
bool resolveTrimBlankSpace(const IExporter::Options& options, bool defaultValue);
// The persisted mapping describes all inputs; only exported inputs reach the mixer.
std::optional<std::vector<std::vector<bool> > > exportChannelMapping(
    const std::vector<std::vector<bool> >& matrix, const std::vector<bool>& exportedInputs, int outputChannels);
}
