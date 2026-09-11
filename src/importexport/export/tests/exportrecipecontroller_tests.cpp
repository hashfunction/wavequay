/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveQuay export recipes.
 */
#include "../internal/exportrecipecontroller.h"
#include "../internal/exportrecipestore.h"
#include <QTemporaryDir>
#include <gtest/gtest.h>
using namespace au::importexport;

namespace {
class State : public IRecipeExportState {
public:
    ExportRecipe current;
    ExportRecipeFormat format;
    int mutations = 0;
    State()
    {
        current.format = "WAV";
        current.name = "Spoken";
        current.id = "12345678-1234-4567-8123-123456789abc";
        current.parameters = { { 1, 16 } };
        format.id = "WAV";
        format.maxChannels = 8;
        format.sampleRates = { 48000 };
        format.options = { { 1, "Depth", ExportOption::TypeEnum, { 16, 24 }, { } } };
        format.values = { { 1, 16 } };
    }
    ExportRecipe capture() const override { return current; }
    RecipeResult<ExportRecipeFormat> describe(const ExportRecipe&) const override { return { { }, format }; }
    void applyValidated(const ExportRecipe& r) override
    {
        current = r;
        ++mutations;
    }
};
}
TEST(ExportRecipeController, CapturePersistAndApplyExactSettingsWithoutDestinationOrExport)
{
    QTemporaryDir dir;
    ExportRecipeStore store(dir.filePath("recipes.json"));
    State state;
    ExportRecipeController controller(store, state);
    state.current.process = ExportProcessType::SELECTED_AUDIO;
    state.current.channelType = ExportChannelsPref::ExportChannels::CUSTOM;
    state.current.channels = 3;
    state.current.channelMapping = { { true, false, true }, { false, true, false } };
    state.current.trimBlankSpace = true;
    state.current.parameters[1] = 24;
    auto saved = controller.saveCurrent("Voix 日本語");
    ASSERT_TRUE(saved.status.ok());
    auto expected = state.current;
    expected.id = saved.value;
    expected.name = "Voix 日本語";
    state.current = State().current;
    ASSERT_TRUE(controller.apply(saved.value).ok());
    EXPECT_EQ(state.current, expected);
    EXPECT_EQ(state.mutations, 1);
}
TEST(ExportRecipeController, MissingFormatAndChangedParametersCannotMutateCurrentState)
{
    QTemporaryDir dir;
    ExportRecipeStore store(dir.filePath("recipes.json"));
    State state;
    ExportRecipeController controller(store, state);
    const auto saved = controller.saveCurrent("Spoken");
    ASSERT_TRUE(saved.status.ok());
    const auto original = state.current;
    state.format.id = "FLAC";
    EXPECT_FALSE(controller.apply(saved.value).ok());
    EXPECT_EQ(state.current, original);
    EXPECT_EQ(state.mutations, 0);
    state.format.id = "WAV";
    state.format.options.clear();
    EXPECT_FALSE(controller.apply(saved.value).ok());
    EXPECT_EQ(state.mutations, 0);
}
TEST(ExportRecipeController, SavingFailureDoesNotMutateExportState)
{
    QTemporaryDir dir;
    ExportRecipeStore store(dir.path());
    State state;
    ExportRecipeController controller(store, state);
    EXPECT_FALSE(controller.saveCurrent("Spoken").status.ok());
    EXPECT_EQ(state.mutations, 0);
}
TEST(ExportRecipeController, DuplicateNameRequiresExplicitChoiceAndUUIDUpdate)
{
    QTemporaryDir dir;
    ExportRecipeStore store(dir.filePath("recipes.json"));
    State state;
    ExportRecipeController controller(store, state);
    auto first = controller.saveCurrent("Spoken");
    ASSERT_TRUE(first.status.ok());
    auto duplicate = controller.saveCurrent("Spoken");
    EXPECT_FALSE(duplicate.status.ok());
    EXPECT_EQ(store.recipes().value.size(), 1);
    ASSERT_TRUE(controller.saveCurrent("Spoken", first.value).status.ok());
    EXPECT_EQ(store.recipes().value.size(), 1);
    ASSERT_TRUE(controller.saveCurrent("Spoken", { }, true).status.ok());
    EXPECT_EQ(store.recipes().value.size(), 2);
}
