/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveWeft export recipes.
 */
#pragma once
#include "../iexportrecipestore.h"
namespace au::importexport {
class ExportRecipeStore final : public IExportRecipeStore {
public:
    explicit ExportRecipeStore(QString path)
        : m_path(std::move(path))
    {
    }
    RecipeResult<std::vector<ExportRecipe>> recipes() override;
    RecipeResult<ExportRecipe> recipe(const QString& id) override;
    RecipeStatus save(const ExportRecipe&, const std::function<bool()>& cancelled = { }) override;
    RecipeStatus remove(const QString& id) override;

private:
    RecipeResult<std::vector<ExportRecipe>> read();
    RecipeStatus write(const std::vector<ExportRecipe>&, const std::function<bool()>& cancelled);
    QString m_path;
};
}
