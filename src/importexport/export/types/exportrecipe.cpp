/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveQuay export recipes.
 */
#include "exportrecipe.h"
#include <QUuid>
#include <algorithm>
#include <cmath>

using namespace au::importexport;
namespace {
RecipeStatus invalid(const QString& message) { return { RecipeError::Invalid, message, { } }; }
bool finiteValue(const OptionValue& v)
{
    if (auto d = std::get_if<double>(&v))
        return std::isfinite(*d);
    if (auto s = std::get_if<std::string>(&v))
        return s->size() <= 4096;
    return true;
}
double numeric(const OptionValue& value)
{
    if (const auto i = std::get_if<int>(&value))
        return *i;
    return std::get<double>(value);
}
}

bool ExportRecipe::operator==(const ExportRecipe& r) const
{
    return schemaVersion == r.schemaVersion && id == r.id && name == r.name && format == r.format && process == r.process
        && channelType == r.channelType && channels == r.channels && sampleRate == r.sampleRate && trimBlankSpace == r.trimBlankSpace
        && channelMapping == r.channelMapping && parameters == r.parameters;
}

RecipeStatus au::importexport::validateRecipe(const ExportRecipe& r)
{
    if (r.schemaVersion != 1)
        return invalid("Unsupported recipe schema; recreate this recipe with this version of WaveQuay.");
    if (QUuid(r.id).isNull() || QUuid(r.id).toString(QUuid::WithoutBraces) != r.id)
        return invalid("Recipe ID is not a canonical UUID.");
    if (r.name.trimmed().isEmpty() || r.name.size() > 128 || r.name.contains(QChar::Null))
        return invalid("Use a recipe name of 1–128 characters.");
    if (r.format.empty() || r.format.size() > 512)
        return invalid("Recipe has no supported format identifier.");
    if (r.sampleRate < 1000 || r.sampleRate > 768000)
        return invalid("Recipe sample rate is outside 1000–768000 Hz.");
    if (r.channels < 1 || r.channels > 64)
        return invalid("Recipe channel count is outside 1–64.");
    if (r.process < ExportProcessType::FULL_PROJECT_AUDIO || r.process > ExportProcessType::AUDIO_IN_LOOP_REGION)
        return invalid("Recipe process is not implemented by this exporter.");
    if (r.channelType < ExportChannelsPref::ExportChannels::MONO || r.channelType > ExportChannelsPref::ExportChannels::CUSTOM)
        return invalid("Recipe channel mode is invalid.");
    if ((r.channelType == ExportChannelsPref::ExportChannels::MONO && r.channels != 1)
        || (r.channelType == ExportChannelsPref::ExportChannels::STEREO && r.channels != 2))
        return invalid("Recipe channel count conflicts with its mode.");
    if (r.channelMapping.size() > 256)
        return invalid("Recipe channel mapping exceeds 256 inputs.");
    if (r.channelType == ExportChannelsPref::ExportChannels::CUSTOM && r.channelMapping.empty())
        return invalid("Custom-channel recipes require a mapping.");
    for (const auto& row : r.channelMapping)
        if (row.size() != size_t(r.channels))
            return invalid("Recipe channel mapping has an invalid width.");
    if (r.parameters.size() > 256)
        return invalid("Recipe contains too many encoder settings.");
    for (const auto& [id, value] : r.parameters)
        if (id < 0 || !finiteValue(value))
            return invalid("Recipe contains an invalid encoder setting.");
    return { };
}

RecipeStatus au::importexport::validateRecipeForFormat(const ExportRecipe& r, const ExportRecipeFormat& f)
{
    if (const auto status = validateRecipe(r); !status.ok())
        return status;
    if (r.format != f.id || f.maxChannels < 1)
        return invalid("Recipe format is unavailable. Edit or recreate the recipe.");
    if (r.channels > f.maxChannels)
        return invalid("Recipe requests more channels than this format supports.");
    if (!f.sampleRates.empty() && std::find(f.sampleRates.begin(), f.sampleRates.end(), r.sampleRate) == f.sampleRates.end())
        return invalid("Recipe sample rate is unavailable for this format.");
    if (r.parameters.size() != f.values.size())
        return invalid("The encoder's settings changed. Recreate this recipe.");
    for (const auto& [id, value] : r.parameters) {
        const int parameterId = id;
        const auto option = std::find_if(f.options.begin(), f.options.end(), [parameterId](const auto& o) { return o.id == parameterId; });
        const auto current = f.values.find(id);
        const QString setting = QString("Encoder setting %1").arg(id);
        if (option == f.options.end() || current == f.values.end())
            return invalid(setting + " is unavailable.");
        if (current->second.index() != value.index())
            return invalid(setting + " has changed its value type.");
        if ((option->flags & ExportOption::ReadOnly) && current->second != value)
            return invalid(setting + " is read-only.");
        if ((option->flags & ExportOption::TypeMask) == ExportOption::TypeEnum
            && std::find(option->values.begin(), option->values.end(), value) == option->values.end())
            return invalid(setting + " has an unavailable choice.");
        if ((option->flags & ExportOption::TypeMask) == ExportOption::TypeRange) {
            if (option->values.size() != 2 || (value.index() != 1 && value.index() != 2) || option->values[0].index() != value.index()
                || option->values[1].index() != value.index())
                return invalid(setting + " has an unsupported range.");
            if (numeric(value) < numeric(option->values.front()) || numeric(value) > numeric(option->values.back()))
                return invalid(setting + " is outside the allowed range.");
        }
    }
    return { };
}
