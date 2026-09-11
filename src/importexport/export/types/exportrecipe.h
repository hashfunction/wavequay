/* WaveQuay additions, GPL-3.0-or-later. */
#pragma once
#include "exporttypes.h"
#include <QString>
#include <functional>
#include <map>

namespace au::importexport {
enum class RecipeError { None, NotFound, Invalid, Io, Busy, Cancelled };
struct RecipeStatus {
    RecipeError code = RecipeError::None;
    QString message;
    QString recoveryPath;
    bool ok() const { return code == RecipeError::None; }
};
template <typename T> struct RecipeResult {
    RecipeStatus status;
    T value { };
};

struct ExportRecipe {
    int schemaVersion = 1;
    QString id;
    QString name;
    std::string format;
    ExportProcessType process = ExportProcessType::FULL_PROJECT_AUDIO;
    ExportChannelsPref::ExportChannels channelType = ExportChannelsPref::ExportChannels::STEREO;
    int channels = 2;
    int sampleRate = 48000;
    bool trimBlankSpace = false;
    std::vector<std::vector<bool>> channelMapping;
    std::map<int, OptionValue> parameters;
    bool operator==(const ExportRecipe& r) const;
};

// A snapshot built from a temporary live encoder editor; obtaining it must not
// change configuration, global encoder preferences, or start encoding.
struct ExportRecipeFormat {
    std::string id;
    int maxChannels = 0;
    std::vector<int> sampleRates;
    std::vector<ExportOption> options;
    std::map<int, OptionValue> values;
};
RecipeStatus validateRecipe(const ExportRecipe& recipe);
RecipeStatus validateRecipeForFormat(const ExportRecipe& recipe, const ExportRecipeFormat& format);
}
