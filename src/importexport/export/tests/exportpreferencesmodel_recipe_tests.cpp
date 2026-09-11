/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow. Real model/settings integration; no audio or GUI. */
#include <gmock/gmock.h>
#include <QCoreApplication>
#include <QSettings>
#include <QTemporaryDir>
#include <QUuid>
#include "../view/exportpreferencesmodel.h"
#include "../internal/exportconfiguration.h"
#include "../internal/exportrecipestore.h"
#include "../exportutils.h"
#include "emptyrealtimeeffects.h"
#include "appshell/tests/mocks/appshellconfigurationmock.h"
#include "context/tests/mocks/globalcontextmock.h"
#include "project/tests/mocks/audacityprojectmock.h"
#include "trackedit/tests/mocks/trackeditprojectmock.h"
#include "trackedit/tests/mocks/selectioncontrollermock.h"
#include "playback/tests/mocks/playbackcontrollermock.h"
#include "framework/global/tests/mocks/filesystemmock.h"
#include "framework/global/tests/mocks/globalconfigurationmock.h"
#include "framework/interactive/tests/mocks/interactivemock.h"
#include "framework/global/settings.h"
#include "testing/testcontext.h"

using namespace au::importexport;
using namespace testing;
namespace
{
class ExporterMock : public IExporter
{
public:
    MOCK_METHOD(void, init, (), (override));
    MOCK_METHOD(muse::Ret, exportData,
        (const muse::io::path_t&, const Options&, muse::ProgressPtr, au::project::IAudacityProjectPtr), (override));
    MOCK_METHOD(std::vector<std::string>, formatsList, (), (const, override));
    MOCK_METHOD(int, formatIndex, (const std::string&), (const, override));
    MOCK_METHOD(std::vector<std::string>, formatExtensions, (const std::string&), (const, override));
    MOCK_METHOD(std::vector<std::string>, cloudPreferredAudioFormats, (), (const, override));
    MOCK_METHOD(ExportParameters, cloudExportParameters, (const std::string&), (const, override));
    MOCK_METHOD(bool, isCustomFFmpegExportFormat, (), (const, override));
    MOCK_METHOD(bool, isOggExportFormat, (), (const, override));
    MOCK_METHOD(bool, hasMetadata, (), (const, override));
    MOCK_METHOD(int, maxChannels, (), (const, override));
    MOCK_METHOD(std::vector<int>, sampleRateList, (), (const, override));
    MOCK_METHOD(int, optionsCount, (), (const, override));
    MOCK_METHOD(std::optional<ExportOption>, option, (int), (const, override));
    MOCK_METHOD(std::optional<OptionValue>, value, (int), (const, override));
    MOCK_METHOD(void, setValue, (int, const OptionValue&), (override));
    MOCK_METHOD(std::optional<ExportRecipeFormat>, recipeFormat, (const std::string&, (const std::map<int, OptionValue>&)),
        (const, override));
};

class ExportModelRecipes : public Test
{
protected:
    inline static std::shared_ptr<ExportConfiguration> configuration;
    inline static std::shared_ptr<NiceMock<muse::GlobalConfigurationMock>> globalConfiguration;
    static void SetUpTestSuite()
    {
        globalConfiguration = std::make_shared<NiceMock<muse::GlobalConfigurationMock>>();
        muse::modularity::globalIoc()->registerExport<muse::IGlobalConfiguration>("recipe-tests", globalConfiguration);
        configuration = std::make_shared<ExportConfiguration>();
        configuration->init();
    }
    QTemporaryDir directory;
    muse::modularity::ContextPtr context = au::testutils::makeTestContext();
    std::shared_ptr<NiceMock<ExporterMock>> exporter = std::make_shared<NiceMock<ExporterMock>>();
    std::shared_ptr<NiceMock<muse::io::FileSystemMock>> fs = std::make_shared<NiceMock<muse::io::FileSystemMock>>();
    std::shared_ptr<NiceMock<muse::InteractiveMock>> interactive = std::make_shared<NiceMock<muse::InteractiveMock>>();
    std::shared_ptr<NiceMock<au::appshell::AppShellConfigurationMock>> shell
        = std::make_shared<NiceMock<au::appshell::AppShellConfigurationMock>>();
    std::shared_ptr<NiceMock<au::context::GlobalContextMock>> global
        = std::make_shared<NiceMock<au::context::GlobalContextMock>>();
    std::shared_ptr<NiceMock<au::project::AudacityProjectMock>> project
        = std::make_shared<NiceMock<au::project::AudacityProjectMock>>();
    std::shared_ptr<NiceMock<au::trackedit::TrackeditProjectMock>> tracks
        = std::make_shared<NiceMock<au::trackedit::TrackeditProjectMock>>();
    std::shared_ptr<NiceMock<au::trackedit::SelectionControllerMock>> selection
        = std::make_shared<NiceMock<au::trackedit::SelectionControllerMock>>();
    std::shared_ptr<NiceMock<au::playback::PlaybackControllerMock>> playback
        = std::make_shared<NiceMock<au::playback::PlaybackControllerMock>>();
    std::shared_ptr<ExportRecipeStore> store;
    std::unique_ptr<ExportPreferencesModel> model;
    std::map<int, OptionValue> parameters;
    ExportRecipeFormat format;
    std::vector<au::trackedit::Track> trackList;
    void SetUp() override
    {
        muse::modularity::globalIoc()->registerExport<IExportConfiguration>("recipe-tests", configuration);
        muse::modularity::globalIoc()->registerExport<au::appshell::IAppShellConfiguration>("recipe-tests", shell);
        muse::modularity::globalIoc()->registerExport<muse::io::IFileSystem>("recipe-tests", fs);
        store = std::make_shared<ExportRecipeStore>(directory.filePath("recipes.json"));
        muse::modularity::globalIoc()->registerExport<IExportRecipeStore>("recipe-tests", store);
        auto ioc = muse::modularity::ioc(context);
        ioc->registerExport<IExporter>("recipe-tests", exporter);
        ioc->registerExport<muse::IInteractive>("recipe-tests", interactive);
        ioc->registerExport<au::context::IGlobalContext>("recipe-tests", global);
        ioc->registerExport<au::trackedit::ISelectionController>("recipe-tests", selection);
        ioc->registerExport<au::playback::IPlaybackController>("recipe-tests", playback);
        ioc->registerExport<au::effects::IRealtimeEffectService>(
            "recipe-tests", std::make_shared<au::effects::EmptyRealtimeEffects>());
        ON_CALL(*global, currentProject()).WillByDefault(Return(project));
        ON_CALL(*global, currentTrackeditProject()).WillByDefault(Return(tracks));
        ON_CALL(*project, displayName()).WillByDefault(Return(QString("source.aup4")));
        au::trackedit::Track stereo;
        stereo.type = au::trackedit::TrackType::Stereo;
        trackList = { stereo };
        ON_CALL(*tracks, trackList()).WillByDefault([this] { return trackList; });
        ON_CALL(*shell, startEditSettings()).WillByDefault([] { muse::settings()->beginTransaction(false); });
        ON_CALL(*shell, rollbackSettings()).WillByDefault([] { muse::settings()->rollbackTransaction(false); });
        ON_CALL(*shell, applySettings()).WillByDefault([] { muse::settings()->commitTransaction(false); });
        parameters = { { 1, true }, { 2, 24 }, { 3, 0.75 }, { 4, std::string("pcm") } };
        format = { "WAV", 8, { 44100, 48000 },
            { { 1, "Dither", 0, { }, { } }, { 2, "Depth", ExportOption::TypeEnum, { 16, 24 }, { } },
                { 3, "Quality", ExportOption::TypeRange, { 0.0, 1.0 }, { } }, { 4, "Encoding", 0, { }, { } } },
            parameters };
        ON_CALL(*exporter, formatsList()).WillByDefault(Return(std::vector<std::string> { "WAV", "FLAC" }));
        ON_CALL(*exporter, maxChannels()).WillByDefault(Return(8));
        ON_CALL(*exporter, sampleRateList()).WillByDefault(Return(std::vector<int> { 44100, 48000 }));
        ON_CALL(*exporter, optionsCount()).WillByDefault(Return(4));
        ON_CALL(*exporter, option(_)).WillByDefault([this](int i) { return format.options.at(i); });
        ON_CALL(*exporter, value(_)).WillByDefault([this](int id) -> std::optional<OptionValue> { return parameters.at(id); });
        ON_CALL(*exporter, setValue(_, _)).WillByDefault([this](int id, const OptionValue& v) { parameters[id] = v; });
        ON_CALL(*exporter, recipeFormat(_, _)).WillByDefault([this](const std::string&, const std::map<int, OptionValue>&) {
            return std::optional<ExportRecipeFormat>(format);
        });
        ON_CALL(*exporter, formatExtensions(_)).WillByDefault(Return(std::vector<std::string> { "wav" }));
        ON_CALL(*fs, exists(_)).WillByDefault(Return(muse::Ret(false)));
        ON_CALL(*interactive, buttonData(_)).WillByDefault([](muse::IInteractive::Button button) {
            return muse::IInteractive::ButtonData(int(button), "Cancel");
        });
        configuration->setCurrentFormat("WAV");
        configuration->setProcessType(ExportProcessType::FULL_PROJECT_AUDIO);
        configuration->setExportSampleRate(44100);
        configuration->setTrimBlankSpace(false);
        configuration->setDirectoryPath(directory.path());
        model = std::make_unique<ExportPreferencesModel>();
        model->setContext(context);
        model->init();
        model->setFilename("spoken.wav");
    }
    void TearDown() override
    {
        model.reset();
        muse::modularity::removeIoC(context);
        auto ioc = muse::modularity::globalIoc();
        ioc->unregister<au::appshell::IAppShellConfiguration>("recipe-tests");
        ioc->unregister<muse::io::IFileSystem>("recipe-tests");
        ioc->unregister<IExportRecipeStore>("recipe-tests");
        ioc->unregister<IExportConfiguration>("recipe-tests");
    }
    ExportRecipe storedRecipe()
    {
        ExportRecipe r;
        r.id = "12345678-1234-4567-8123-123456789abc";
        r.name = "Spoken 日本語";
        r.format = "WAV";
        r.process = ExportProcessType::SELECTED_AUDIO;
        r.channels = 3;
        r.channelType = ExportChannelsPref::ExportChannels::CUSTOM;
        r.channelMapping = { { true, false, true }, { false, true, false } };
        r.sampleRate = 48000;
        r.trimBlankSpace = true;
        r.parameters = parameters;
        return r;
    }
};

TEST_F(ExportModelRecipes, AppliedRecipeExportsOnceWithExactImmutableSettings)
{
    const auto recipe = storedRecipe();
    ASSERT_TRUE(store->save(recipe).ok());
    EXPECT_CALL(*exporter, exportData(_, _, _, _)).Times(0);
    ASSERT_TRUE(model->applyRecipe(recipe.id));
    EXPECT_EQ(configuration->processType(), recipe.process);
    EXPECT_TRUE(configuration->trimBlankSpace());
    EXPECT_EQ(configuration->exportChannels(), 3);
    EXPECT_EQ(configuration->exportSampleRate(), 48000);
    EXPECT_EQ(utils::valToMatrix(configuration->exportCustomChannelMapping()), recipe.channelMapping);
    Mock::VerifyAndClearExpectations(exporter.get());
    int completed = 0;
    QObject::connect(model.get(), &ExportPreferencesModel::exportCompleted, [&] { ++completed; });
    EXPECT_CALL(*exporter, exportData(_, _, _, _))
        .Times(1)
        .WillOnce([&](const muse::io::path_t& path, const IExporter::Options& options, muse::ProgressPtr,
                      au::project::IAudacityProjectPtr) {
            EXPECT_EQ(path.toQString(), directory.filePath("spoken.wav"));
            EXPECT_EQ(options.size(), 8u) << "Every recipe setting, including trim, belongs to the immutable export request";
            EXPECT_TRUE(options.at(IExporter::OptionKey::TrimBlankSpace).toBool());
            configuration->setTrimBlankSpace(false);
            EXPECT_FALSE(configuration->trimBlankSpace());
            EXPECT_TRUE(utils::resolveTrimBlankSpace(options, configuration->trimBlankSpace()));
            EXPECT_EQ(options.at(IExporter::OptionKey::Format).toString(), recipe.format);
            EXPECT_EQ(options.at(IExporter::OptionKey::ProcessType).toInt(), int(recipe.process));
            EXPECT_EQ(options.at(IExporter::OptionKey::ExportChannelsType).toInt(), int(recipe.channelType));
            EXPECT_EQ(options.at(IExporter::OptionKey::ExportChannels).toInt(), 3);
            EXPECT_EQ(options.at(IExporter::OptionKey::ExportSampleRate).toInt(), 48000);
            EXPECT_EQ(utils::valToMatrix(options.at(IExporter::OptionKey::ExportCustomChannelMapping)), recipe.channelMapping);
            auto entries = options.at(IExporter::OptionKey::Parameters).toList();
            EXPECT_EQ(entries.size(), 4u);
            if (entries.size() != 4u)
                return muse::Ret(false);
            EXPECT_EQ(entries[0].toMap().at("value").type(), muse::Val::Type::Bool);
            EXPECT_TRUE(entries[0].toMap().at("value").toBool());
            EXPECT_EQ(entries[1].toMap().at("value").type(), muse::Val::Type::Int);
            EXPECT_EQ(entries[1].toMap().at("value").toInt(), 24);
            EXPECT_EQ(entries[2].toMap().at("value").type(), muse::Val::Type::Double);
            EXPECT_DOUBLE_EQ(entries[2].toMap().at("value").toDouble(), 0.75);
            EXPECT_EQ(entries[3].toMap().at("value").type(), muse::Val::Type::String);
            EXPECT_EQ(entries[3].toMap().at("value").toString(), "pcm");
            for (size_t i = 0; i < entries.size(); ++i)
                EXPECT_EQ(entries[i].toMap().at("id").toInt(), int(i + 1));
            return muse::Ret(true);
        });
    model->exportData();
    EXPECT_EQ(completed, 1);
}

TEST_F(ExportModelRecipes, CustomMappingForDifferentProjectInputsIsRejectedBeforeMutation)
{
    const auto recipe = storedRecipe();
    ASSERT_TRUE(store->save(recipe).ok());
    au::trackedit::Track mono;
    mono.type = au::trackedit::TrackType::Mono;
    trackList.push_back(mono);
    const auto before = model->capture();
    EXPECT_CALL(*exporter, setValue(_, _)).Times(0);
    EXPECT_CALL(*exporter, exportData(_, _, _, _)).Times(0);
    EXPECT_FALSE(model->applyRecipe(recipe.id));
    EXPECT_EQ(model->capture(), before);
    EXPECT_FALSE(model->recipeError().isEmpty());
}

TEST_F(ExportModelRecipes, OverwriteConfirmationKeepsTheOriginalExportSnapshot)
{
    const auto recipe = storedRecipe();
    ASSERT_TRUE(store->save(recipe).ok());
    ASSERT_TRUE(model->applyRecipe(recipe.id));
    ON_CALL(*fs, exists(_)).WillByDefault(Return(muse::Ret(true)));
    EXPECT_CALL(*interactive, questionSync(_, _, _, _, _, _)).WillOnce([&](auto&&...) {
        configuration->setCurrentFormat("FLAC");
        configuration->setProcessType(ExportProcessType::FULL_PROJECT_AUDIO);
        configuration->setExportSampleRate(44100);
        configuration->setTrimBlankSpace(false);
        configuration->setDirectoryPath(directory.filePath("changed"));
        model->setFilename("different.flac");
        parameters[2] = 16;
        return muse::IInteractive::Result(int(muse::IInteractive::Button::CustomButton) + 1);
    });
    EXPECT_CALL(*exporter, exportData(_, _, _, _))
        .Times(1)
        .WillOnce([&](const auto& path, const IExporter::Options& options, auto, auto) {
            EXPECT_EQ(path.toQString(), directory.filePath("spoken.wav"));
            EXPECT_EQ(options.at(IExporter::OptionKey::Format).toString(), "WAV");
            EXPECT_EQ(options.at(IExporter::OptionKey::ProcessType).toInt(), int(recipe.process));
            EXPECT_EQ(options.at(IExporter::OptionKey::ExportSampleRate).toInt(), 48000);
            EXPECT_EQ(options.at(IExporter::OptionKey::Parameters).toList().at(1).toMap().at("value").toInt(), 24);
            EXPECT_TRUE(options.at(IExporter::OptionKey::TrimBlankSpace).toBool());
            EXPECT_TRUE(utils::resolveTrimBlankSpace(options, configuration->trimBlankSpace()));
            return muse::Ret(true);
        });
    model->exportData();
}

TEST_F(ExportModelRecipes, CancelingOverwriteDoesNotExportOrComplete)
{
    const auto recipe = storedRecipe();
    ASSERT_TRUE(store->save(recipe).ok());
    ASSERT_TRUE(model->applyRecipe(recipe.id));
    ON_CALL(*fs, exists(_)).WillByDefault(Return(muse::Ret(true)));
    EXPECT_CALL(*interactive, questionSync(_, _, _, _, _, _))
        .WillOnce(Return(muse::IInteractive::Result(int(muse::IInteractive::Button::Cancel))));
    EXPECT_CALL(*exporter, exportData(_, _, _, _)).Times(0);
    int completed = 0;
    QObject::connect(model.get(), &ExportPreferencesModel::exportCompleted, [&] { ++completed; });
    model->exportData();
    EXPECT_EQ(completed, 0);
}

TEST_F(ExportModelRecipes, ExplicitFalseTrimOverridesLaterTrueConfiguration)
{
    auto recipe = storedRecipe();
    recipe.trimBlankSpace = false;
    ASSERT_TRUE(store->save(recipe).ok());
    ASSERT_TRUE(model->applyRecipe(recipe.id));
    EXPECT_CALL(*exporter, exportData(_, _, _, _))
        .Times(1)
        .WillOnce([&](const auto&, const IExporter::Options& options, auto, auto) {
            configuration->setTrimBlankSpace(true);
            EXPECT_TRUE(configuration->trimBlankSpace());
            EXPECT_FALSE(options.at(IExporter::OptionKey::TrimBlankSpace).toBool());
            EXPECT_FALSE(utils::resolveTrimBlankSpace(options, configuration->trimBlankSpace()));
            return muse::Ret(true);
        });
    model->exportData();
}

TEST_F(ExportModelRecipes, FailedExportWithoutTextDoesNotSignalCompletion)
{
    EXPECT_CALL(*exporter, exportData(_, _, _, _)).Times(1).WillOnce(Return(muse::Ret(false)));
    int completed = 0;
    QObject::connect(model.get(), &ExportPreferencesModel::exportCompleted, [&] { ++completed; });
    model->exportData();
    EXPECT_EQ(completed, 0);
}

TEST_F(ExportModelRecipes, UnavailableEncoderLeavesActualSettingsAndParametersUnchanged)
{
    const auto recipe = storedRecipe();
    ASSERT_TRUE(store->save(recipe).ok());
    const auto before = model->capture();
    EXPECT_CALL(*exporter, recipeFormat(_, _)).WillOnce(Return(std::nullopt));
    EXPECT_CALL(*exporter, setValue(_, _)).Times(0);
    EXPECT_CALL(*exporter, exportData(_, _, _, _)).Times(0);
    EXPECT_FALSE(model->applyRecipe(recipe.id));
    EXPECT_EQ(model->capture(), before);
    EXPECT_FALSE(model->recipeError().isEmpty());
}

TEST(ExportOptions, MissingTrimOptionPreservesLegacyConfiguration)
{
    EXPECT_TRUE(utils::resolveTrimBlankSpace({ }, true));
    EXPECT_FALSE(utils::resolveTrimBlankSpace({ }, false));
}

TEST(ExportOptions, ChannelMappingRetainsTheActualExportedRowsInOrder)
{
    const std::vector<std::vector<bool>> matrix = { { true, false, false }, { false, true, false }, { false, false, true } };
    const auto filtered = utils::exportChannelMapping(matrix, { false, true, true }, 3);
    ASSERT_TRUE(filtered);
    EXPECT_EQ(*filtered, (std::vector<std::vector<bool>> { { false, true, false }, { false, false, true } }));
    EXPECT_EQ(utils::exportChannelMapping(matrix, { true, false, true }, 3).value(),
        (std::vector<std::vector<bool>> { { true, false, false }, { false, false, true } }));
}

TEST(ExportOptions, ChannelMappingRejectsChangedInputsAndMalformedWidths)
{
    EXPECT_FALSE(utils::exportChannelMapping({ { true, false } }, { true, true }, 2));
    EXPECT_FALSE(utils::exportChannelMapping({ { true, false }, { false, true } }, { true }, 2));
    EXPECT_FALSE(utils::exportChannelMapping({ { true }, { false, true } }, { true, true }, 2));
    EXPECT_FALSE(utils::exportChannelMapping({ { } }, { true }, 0));
}

TEST_F(ExportModelRecipes, LabelTracksDoNotChangeMappingInputs)
{
    const auto recipe = storedRecipe();
    ASSERT_TRUE(store->save(recipe).ok());
    au::trackedit::Track label;
    label.type = au::trackedit::TrackType::Label;
    trackList.push_back(label);
    ASSERT_TRUE(model->applyRecipe(recipe.id));
    EXPECT_EQ(model->capture().channelMapping, recipe.channelMapping);
}
}

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    QTemporaryDir settingsDirectory;
    QCoreApplication::setOrganizationName("WaveQuayModelTests");
    QCoreApplication::setApplicationName(QUuid::createUuid().toString(QUuid::WithoutBraces));
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, settingsDirectory.path());
    InitGoogleMock(&argc, argv);
    return RUN_ALL_TESTS();
}
