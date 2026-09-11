/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveQuay export recipes.
 */
#include "../internal/exportrecipestore.h"
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLockFile>
#include <QTemporaryDir>
#include <QUuid>
#include <cmath>
#include <gtest/gtest.h>

using namespace au::importexport;

namespace {
ExportRecipe spokenRecipe()
{
    ExportRecipe r;
    r.id = "12345678-1234-4567-8123-123456789abc";
    r.name = QString::fromUtf8("Voix — 日本語");
    r.format = "WAV (Microsoft)";
    r.sampleRate = 48000;
    r.channels = 1;
    r.channelType = ExportChannelsPref::ExportChannels::MONO;
    r.parameters = { { 1, true }, { 2, 16 }, { 3, 0.5 }, { 4, std::string("pcm") } };
    return r;
}
QByteArray read(const QString& path)
{
    QFile f(path);
    return f.open(QIODevice::ReadOnly) ? f.readAll() : QByteArray();
}
void write(const QString& path, const QByteArray& bytes)
{
    QFile f(path);
    ASSERT_TRUE(f.open(QIODevice::WriteOnly));
    ASSERT_EQ(f.write(bytes), bytes.size());
}
}

TEST(ExportRecipeStore, UnicodeAndAllOptionAlternativesSurviveReload)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    ExportRecipeStore store(path);
    const auto recipe = spokenRecipe();
    ASSERT_TRUE(store.save(recipe).ok());
    ExportRecipeStore reloaded(path);
    const auto result = reloaded.recipes();
    ASSERT_TRUE(result.status.ok());
    ASSERT_EQ(result.value.size(), 1);
    EXPECT_EQ(result.value.front(), recipe);
    EXPECT_EQ(std::get<bool>(result.value.front().parameters.at(1)), true);
    EXPECT_EQ(std::get<int>(result.value.front().parameters.at(2)), 16);
    EXPECT_DOUBLE_EQ(std::get<double>(result.value.front().parameters.at(3)), 0.5);
    EXPECT_EQ(std::get<std::string>(result.value.front().parameters.at(4)), "pcm");
}

TEST(ExportRecipeStore, UUIDReplacementIsDeterministicAndDeletionPersists)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    ExportRecipeStore store(path);
    auto r = spokenRecipe();
    ASSERT_TRUE(store.save(r).ok());
    const auto original = read(path);
    ASSERT_TRUE(store.save(r).ok());
    EXPECT_EQ(read(path), original);
    r.name = "Changed";
    ASSERT_TRUE(store.save(r).ok());
    EXPECT_EQ(store.recipes().value.size(), 1);
    EXPECT_EQ(store.recipe(r.id).value.name, "Changed");
    ASSERT_TRUE(store.remove(r.id).ok());
    EXPECT_TRUE(ExportRecipeStore(path).recipes().value.empty());
}

TEST(ExportRecipeStore, InvalidInputCannotReplacePriorFile)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    ExportRecipeStore store(path);
    const auto valid = spokenRecipe();
    ASSERT_TRUE(store.save(valid).ok());
    const auto original = read(path);
    for (int scenario = 0; scenario < 6; ++scenario) {
        auto r = valid;
        if (scenario == 0)
            r.name = "  ";
        if (scenario == 1)
            r.sampleRate = 0;
        if (scenario == 2)
            r.channels = 0;
        if (scenario == 3)
            r.schemaVersion = 2;
        if (scenario == 4)
            r.parameters[3] = std::nan("");
        if (scenario == 5)
            r.id = "not-a-uuid";
        EXPECT_FALSE(store.save(r).ok()) << scenario;
        EXPECT_EQ(read(path), original);
    }
}

TEST(ExportRecipeStore, CorruptFileIsPreservedAndCannotBeOverwrittenBySaveOrDelete)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    const QByteArray corrupt("{\"schemaVersion\":1,\"recipes\":[");
    write(path, corrupt);
    ExportRecipeStore store(path);
    const auto result = store.recipes();
    EXPECT_FALSE(result.status.ok());
    EXPECT_FALSE(result.status.recoveryPath.isEmpty());
    EXPECT_EQ(read(result.status.recoveryPath), corrupt);
    EXPECT_FALSE(store.save(spokenRecipe()).ok());
    EXPECT_FALSE(store.remove(spokenRecipe().id).ok());
    EXPECT_EQ(read(path), corrupt);
}

TEST(ExportRecipeStore, CancelledCommitKeepsPreviousBytesAndMemory)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    ExportRecipeStore store(path);
    auto r = spokenRecipe();
    ASSERT_TRUE(store.save(r).ok());
    const auto before = read(path);
    r.name = "Cancelled";
    EXPECT_EQ(store.save(r, [] { return true; }).code, RecipeError::Cancelled);
    EXPECT_EQ(read(path), before);
    EXPECT_EQ(store.recipe(r.id).value.name, spokenRecipe().name);
}

TEST(ExportRecipeStore, IndependentStoreInstancesPreserveEachOthersRecipes)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    ExportRecipeStore first(path), second(path);
    ASSERT_TRUE(first.save(spokenRecipe()).ok());
    auto another = spokenRecipe();
    another.id = "87654321-1234-4567-8123-123456789abc";
    ASSERT_TRUE(second.save(another).ok());
    EXPECT_EQ(first.recipes().value.size(), 2);
}

TEST(ExportRecipeValidation, UnavailableFormatAndInvalidParametersAreRejected)
{
    auto recipe = spokenRecipe();
    ExportRecipeFormat format;
    format.id = recipe.format;
    format.maxChannels = 2;
    format.sampleRates = { 44100, 48000 };
    format.values = recipe.parameters;
    format.options = { { 1, "Dither", 0, { }, { } }, { 2, "Depth", ExportOption::TypeEnum, { 16, 24 }, { } },
        { 3, "Quality", ExportOption::TypeRange, { 0.0, 1.0 }, { } }, { 4, "Encoding", 0, { }, { } } };
    EXPECT_TRUE(validateRecipeForFormat(recipe, format).ok());
    auto wrong = format;
    wrong.id = "FLAC";
    EXPECT_FALSE(validateRecipeForFormat(recipe, wrong).ok());
    recipe.parameters[99] = true;
    EXPECT_FALSE(validateRecipeForFormat(recipe, format).ok());
    recipe.parameters.erase(99);
    recipe.parameters[2] = 32;
    EXPECT_FALSE(validateRecipeForFormat(recipe, format).ok());
    recipe.parameters[2] = 16;
    recipe.parameters[3] = 2.0;
    EXPECT_FALSE(validateRecipeForFormat(recipe, format).ok());
    recipe.parameters[3] = 0.5;
    recipe.sampleRate = 12345;
    EXPECT_FALSE(validateRecipeForFormat(recipe, format).ok());
}

TEST(ExportRecipeStore, UnsupportedJsonSchemasTypesAndDuplicateIdsPreserveBytes)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    ExportRecipeStore store(path);
    ASSERT_TRUE(store.save(spokenRecipe()).ok());
    const auto valid = QJsonDocument::fromJson(read(path)).object();
    for (int scenario = 0; scenario < 5; ++scenario) {
        auto root = valid;
        auto recipes = root["recipes"].toArray();
        auto recipe = recipes[0].toObject();
        if (scenario == 0)
            root["schemaVersion"] = 2;
        if (scenario == 1)
            recipe["schemaVersion"] = 2;
        if (scenario == 2) {
            auto parameters = recipe["parameters"].toArray();
            auto value = parameters[0].toObject();
            value["type"] = 9;
            parameters[0] = value;
            recipe["parameters"] = parameters;
        }
        if (scenario == 3)
            recipes.append(recipe);
        if (scenario == 4)
            recipe["destination"] = "C:/should-not-exist.wav";
        recipes[0] = recipe;
        root["recipes"] = recipes;
        const auto bytes = QJsonDocument(root).toJson();
        write(path, bytes);
        EXPECT_FALSE(store.recipes().status.ok()) << scenario;
        EXPECT_FALSE(store.save(spokenRecipe()).ok()) << scenario;
        EXPECT_EQ(read(path), bytes) << scenario;
    }
}

TEST(ExportRecipeStore, LockContentionFailsWithoutWritingAndRecoveryAllowsRetry)
{
    QTemporaryDir dir;
    const auto path = dir.filePath("recipes.json");
    ExportRecipeStore store(path);
    ASSERT_TRUE(store.save(spokenRecipe()).ok());
    const auto original = read(path);
    QLockFile competing(path + ".lock");
    ASSERT_TRUE(competing.tryLock());
    auto recipe = spokenRecipe();
    recipe.name = "New name";
    EXPECT_EQ(store.save(recipe).code, RecipeError::Busy);
    EXPECT_EQ(read(path), original);
    competing.unlock();
    EXPECT_TRUE(store.save(recipe).ok());
    EXPECT_EQ(store.recipe(recipe.id).value.name, "New name");
}
