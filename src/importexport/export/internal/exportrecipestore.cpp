/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveQuay export recipes.
 */
#include "exportrecipestore.h"
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLockFile>
#include <QSaveFile>
#include <QSet>
#include <algorithm>
#include <cmath>
#include <limits>

using namespace au::importexport;
namespace {
constexpr qint64 MAX_FILE_BYTES = 2 * 1024 * 1024;
constexpr size_t MAX_RECIPES = 200;
RecipeStatus invalid(const QString& message) { return { RecipeError::Invalid, message, { } }; }
RecipeStatus ioError(const QString& message) { return { RecipeError::Io, message, { } }; }
bool keys(const QJsonObject& object, const QStringList& expected)
{
    auto actual = object.keys();
    auto sorted = expected;
    sorted.sort();
    return actual == sorted;
}
bool integer(const QJsonValue& v)
{
    return v.isDouble() && std::isfinite(v.toDouble()) && std::floor(v.toDouble()) == v.toDouble()
        && v.toDouble() >= std::numeric_limits<int>::min() && v.toDouble() <= std::numeric_limits<int>::max();
}
QJsonObject encode(const ExportRecipe& r)
{
    QJsonArray parameters;
    for (const auto& [id, value] : r.parameters) {
        QJsonValue encoded;
        std::visit(
            [&encoded](const auto& v) {
                using T = std::decay_t<decltype(v)>;
                if constexpr (std::is_same_v<T, std::string>)
                    encoded = QString::fromStdString(v);
                else
                    encoded = QJsonValue(v);
            },
            value);
        parameters.append(QJsonObject { { "id", id }, { "type", int(value.index()) }, { "value", encoded } });
    }
    QJsonArray mapping;
    for (const auto& row : r.channelMapping) {
        QJsonArray columns;
        for (bool v : row)
            columns.append(v);
        mapping.append(columns);
    }
    return { { "schemaVersion", r.schemaVersion }, { "id", r.id }, { "name", r.name }, { "format", QString::fromStdString(r.format) },
        { "process", int(r.process) }, { "channelType", int(r.channelType) }, { "channels", r.channels }, { "sampleRate", r.sampleRate },
        { "trimBlankSpace", r.trimBlankSpace }, { "mapping", mapping }, { "parameters", parameters } };
}
RecipeResult<ExportRecipe> decode(const QJsonValue& value)
{
    const auto o = value.toObject();
    ExportRecipe r;
    if (!value.isObject()
        || !keys(o,
            { "schemaVersion", "id", "name", "format", "process", "channelType", "channels", "sampleRate", "trimBlankSpace", "mapping",
                "parameters" }))
        return { invalid("Invalid recipe object."), { } };
    for (const auto& name : { "schemaVersion", "process", "channelType", "channels", "sampleRate" })
        if (!integer(o[name]))
            return { invalid("Invalid integer field in recipe."), { } };
    for (const auto& name : { "id", "name", "format" })
        if (!o[name].isString())
            return { invalid("Invalid string field in recipe."), { } };
    if (!o["trimBlankSpace"].isBool() || !o["mapping"].isArray() || !o["parameters"].isArray())
        return { invalid("Invalid recipe settings."), { } };
    r.schemaVersion = o["schemaVersion"].toInt();
    r.id = o["id"].toString();
    r.name = o["name"].toString();
    r.format = o["format"].toString().toStdString();
    r.process = ExportProcessType(o["process"].toInt());
    r.channelType = ExportChannelsPref::ExportChannels(o["channelType"].toInt());
    r.channels = o["channels"].toInt();
    r.sampleRate = o["sampleRate"].toInt();
    r.trimBlankSpace = o["trimBlankSpace"].toBool();
    if (o["mapping"].toArray().size() > 256 || o["parameters"].toArray().size() > 256)
        return { invalid("Recipe exceeds settings limits."), { } };
    for (const auto& row : o["mapping"].toArray()) {
        if (!row.isArray() || row.toArray().size() > 64)
            return { invalid("Invalid channel mapping."), { } };
        std::vector<bool> columns;
        for (const auto& column : row.toArray()) {
            if (!column.isBool())
                return { invalid("Invalid mapping value."), { } };
            columns.push_back(column.toBool());
        }
        r.channelMapping.push_back(std::move(columns));
    }
    for (const auto& entry : o["parameters"].toArray()) {
        const auto p = entry.toObject();
        if (!entry.isObject() || !keys(p, { "id", "type", "value" }) || !integer(p["id"]) || !integer(p["type"]))
            return { invalid("Invalid encoder setting."), { } };
        OptionValue option;
        const auto v = p["value"];
        switch (p["type"].toInt()) {
        case 0:
            if (!v.isBool())
                return { invalid("Expected boolean encoder setting."), { } };
            option = v.toBool();
            break;
        case 1:
            if (!integer(v))
                return { invalid("Expected integer encoder setting."), { } };
            option = v.toInt();
            break;
        case 2:
            if (!v.isDouble() || !std::isfinite(v.toDouble()))
                return { invalid("Expected finite encoder setting."), { } };
            option = v.toDouble();
            break;
        case 3:
            if (!v.isString())
                return { invalid("Expected string encoder setting."), { } };
            option = v.toString().toStdString();
            break;
        default:
            return { invalid("Unknown encoder setting value type."), { } };
        }
        if (!r.parameters.emplace(p["id"].toInt(), std::move(option)).second)
            return { invalid("Duplicate encoder setting ID."), { } };
    }
    return { validateRecipe(r), r };
}
RecipeStatus prepare(const QString& path)
{
    if (QFileInfo(path).isSymLink())
        return ioError("Recipe store is a symbolic link; select a regular local store.");
    if (!QDir().mkpath(QFileInfo(path).absolutePath()))
        return ioError("Cannot create the local recipe folder.");
    return { };
}
}

RecipeResult<std::vector<ExportRecipe>> ExportRecipeStore::read()
{
    if (!QFileInfo::exists(m_path))
        return { };
    QFile f(m_path);
    if (!f.open(QIODevice::ReadOnly))
        return { ioError("Cannot read recipe store: " + f.errorString()), { } };
    if (f.size() > MAX_FILE_BYTES)
        return { invalid("Recipe store exceeds the 2 MiB safety limit; the file was preserved."), { } };
    const auto bytes = f.read(MAX_FILE_BYTES + 1);
    if (f.error() != QFileDevice::NoError)
        return { ioError("Cannot read the complete recipe store."), { } };
    auto corrupt = [&](const QString& reason) -> RecipeResult<std::vector<ExportRecipe>> {
        const QString recovery
            = m_path + ".corrupt-" + QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex()) + ".json";
        QString recoveryPath;
        if (QFile::copy(m_path, recovery))
            recoveryPath = recovery;
        else {
            QFile existing(recovery);
            if (existing.open(QIODevice::ReadOnly) && existing.readAll() == bytes)
                recoveryPath = recovery;
        }
        return { { RecipeError::Invalid, reason + " The original was preserved. Repair or move it before saving recipes.", recoveryPath },
            { } };
    };
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(bytes, &error);
    if (error.error != QJsonParseError::NoError || !document.isObject())
        return corrupt("Recipe JSON is truncated or invalid.");
    const auto root = document.object();
    if (!keys(root, { "schemaVersion", "recipes" }) || !integer(root["schemaVersion"]) || root["schemaVersion"].toInt() != 1
        || !root["recipes"].isArray())
        return corrupt("Unsupported recipe store schema.");
    const auto entries = root["recipes"].toArray();
    if (entries.size() > int(MAX_RECIPES))
        return corrupt("Recipe store exceeds 200 recipes.");
    QSet<QString> ids;
    std::vector<ExportRecipe> recipes;
    for (const auto& value : entries) {
        auto result = decode(value);
        if (!result.status.ok())
            return corrupt(result.status.message);
        if (ids.contains(result.value.id))
            return corrupt("Duplicate recipe UUID.");
        ids.insert(result.value.id);
        recipes.push_back(std::move(result.value));
    }
    return { { }, std::move(recipes) };
}

RecipeResult<std::vector<ExportRecipe>> ExportRecipeStore::recipes()
{
    if (const auto status = prepare(m_path); !status.ok())
        return { status, { } };
    QLockFile lock(m_path + ".lock");
    if (!lock.tryLock(100))
        return { { RecipeError::Busy, "Another WaveQuay window is updating recipes. Try again.", { } }, { } };
    return read();
}
RecipeResult<ExportRecipe> ExportRecipeStore::recipe(const QString& id)
{
    const auto result = recipes();
    if (!result.status.ok())
        return { result.status, { } };
    for (const auto& r : result.value)
        if (r.id == id)
            return { { }, r };
    return { { RecipeError::NotFound, "Recipe no longer exists. Refresh the recipe list.", { } }, { } };
}
RecipeStatus ExportRecipeStore::write(const std::vector<ExportRecipe>& recipes, const std::function<bool()>& cancelled)
{
    auto sorted = recipes;
    std::sort(sorted.begin(), sorted.end(), [](const auto& a, const auto& b) { return a.id < b.id; });
    QJsonArray entries;
    for (const auto& r : sorted)
        entries.append(encode(r));
    const auto bytes = QJsonDocument(QJsonObject { { "schemaVersion", 1 }, { "recipes", entries } }).toJson(QJsonDocument::Compact);
    if (bytes.size() > MAX_FILE_BYTES || recipes.size() > MAX_RECIPES)
        return invalid("Recipe collection exceeds its safety limit.");
    QSaveFile output(m_path);
    output.setDirectWriteFallback(false);
    if (!output.open(QIODevice::WriteOnly) || output.write(bytes) != bytes.size())
        return ioError("Could not stage recipe changes: " + output.errorString());
    if (cancelled && cancelled()) {
        output.cancelWriting();
        return { RecipeError::Cancelled, "Recipe change cancelled.", { } };
    }
    if (!output.commit())
        return ioError("Could not commit recipe changes: " + output.errorString());
    return { };
}
RecipeStatus ExportRecipeStore::save(const ExportRecipe& recipe, const std::function<bool()>& cancelled)
{
    if (const auto status = validateRecipe(recipe); !status.ok())
        return status;
    if (const auto status = prepare(m_path); !status.ok())
        return status;
    QLockFile lock(m_path + ".lock");
    if (!lock.tryLock(100))
        return { RecipeError::Busy, "Recipe store is busy. Try again.", { } };
    auto existing = read();
    if (!existing.status.ok())
        return existing.status;
    auto found = std::find_if(existing.value.begin(), existing.value.end(), [&](const auto& r) { return r.id == recipe.id; });
    if (found == existing.value.end())
        existing.value.push_back(recipe);
    else
        *found = recipe;
    return write(existing.value, cancelled);
}
RecipeStatus ExportRecipeStore::remove(const QString& id)
{
    if (const auto status = prepare(m_path); !status.ok())
        return status;
    QLockFile lock(m_path + ".lock");
    if (!lock.tryLock(100))
        return { RecipeError::Busy, "Recipe store is busy. Try again.", { } };
    auto existing = read();
    if (!existing.status.ok())
        return existing.status;
    auto found = std::find_if(existing.value.begin(), existing.value.end(), [&](const auto& r) { return r.id == id; });
    if (found == existing.value.end())
        return { RecipeError::NotFound, "Recipe no longer exists.", { } };
    existing.value.erase(found);
    return write(existing.value, { });
}
