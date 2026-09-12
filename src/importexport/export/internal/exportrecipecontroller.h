/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveWeft export recipes.
 */
#pragma once
#include "../iexportrecipestore.h"
namespace au::importexport {
// The live export model implements this boundary. No destination or export
// operation is exposed to recipe selection.
class IRecipeExportState {
public:
    virtual ~IRecipeExportState() = default;
    virtual ExportRecipe capture() const = 0;
    virtual RecipeResult<ExportRecipeFormat> describe(const ExportRecipe&) const = 0;
    virtual void applyValidated(const ExportRecipe&) = 0;
};
class ExportRecipeController {
public:
    ExportRecipeController(IExportRecipeStore& store, IRecipeExportState& state)
        : m_store(store)
        , m_state(state)
    {
    }
    RecipeResult<QString> saveCurrent(const QString& name, const QString& replaceId = { }, bool allowDuplicateName = false);
    RecipeStatus apply(const QString& id);

private:
    IExportRecipeStore& m_store;
    IRecipeExportState& m_state;
};
}
