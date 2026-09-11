/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveQuay export recipes.
 */
#pragma once
#include "framework/global/modularity/imoduleinterface.h"
#include "types/exportrecipe.h"
namespace au::importexport {
class IExportRecipeStore : MODULE_GLOBAL_INTERFACE {
    INTERFACE_ID(IExportRecipeStore)
public:
    virtual ~IExportRecipeStore() = default;
    virtual RecipeResult<std::vector<ExportRecipe>> recipes() = 0;
    virtual RecipeResult<ExportRecipe> recipe(const QString& id) = 0;
    virtual RecipeStatus save(const ExportRecipe&, const std::function<bool()>& cancelled = { }) = 0;
    virtual RecipeStatus remove(const QString& id) = 0;
};
}
