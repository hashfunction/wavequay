/*
 * SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow
 * WaveWeft export recipes.
 */
#include "exportrecipecontroller.h"
#include <QUuid>
using namespace au::importexport;
RecipeResult<QString> ExportRecipeController::saveCurrent(const QString& name, const QString& replaceId, bool allowDuplicateName)
{
    const auto existing = m_store.recipes();
    if (!existing.status.ok())
        return { existing.status, { } };
    if (!replaceId.isEmpty() && !m_store.recipe(replaceId).status.ok())
        return { { RecipeError::NotFound, "The recipe selected for replacement no longer exists.", { } }, { } };
    for (const auto& item : existing.value) {
        if (!allowDuplicateName && item.id != replaceId && item.name == name.trimmed())
            return { { RecipeError::Invalid, "A recipe has this name. Choose Update existing or Create another.", { } }, { } };
    }
    auto recipe = m_state.capture();
    recipe.name = name.trimmed();
    recipe.id = replaceId.isEmpty() ? QUuid::createUuid().toString(QUuid::WithoutBraces) : replaceId;
    const auto format = m_state.describe(recipe);
    if (!format.status.ok())
        return { format.status, { } };
    const auto validated = validateRecipeForFormat(recipe, format.value);
    if (!validated.ok())
        return { validated, { } };
    const auto status = m_store.save(recipe);
    return { status, status.ok() ? recipe.id : QString() };
}
RecipeStatus ExportRecipeController::apply(const QString& id)
{
    const auto recipe = m_store.recipe(id);
    if (!recipe.status.ok())
        return recipe.status;
    const auto format = m_state.describe(recipe.value);
    if (!format.status.ok())
        return format.status;
    const auto status = validateRecipeForFormat(recipe.value, format.value);
    if (!status.ok())
        return status;
    m_state.applyValidated(recipe.value);
    return { };
}
