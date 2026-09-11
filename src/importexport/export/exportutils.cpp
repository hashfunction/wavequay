/*
 * Audacity: A Digital Audio Editor
 */

#include "exportutils.h"

bool au::importexport::utils::resolveTrimBlankSpace(const IExporter::Options& options, bool defaultValue)
{
    const auto it = options.find(IExporter::OptionKey::TrimBlankSpace);
    return it == options.end() ? defaultValue : it->second.toBool();
}

std::optional<std::vector<std::vector<bool> > > au::importexport::utils::exportChannelMapping(
    const std::vector<std::vector<bool> >& matrix, const std::vector<bool>& exportedInputs, int outputChannels)
{
    if (matrix.size() != exportedInputs.size() || outputChannels < 1)
        return std::nullopt;
    std::vector<std::vector<bool> > result;
    for (size_t input = 0; input < matrix.size(); ++input) {
        if (matrix[input].size() != size_t(outputChannels))
            return std::nullopt;
        if (exportedInputs[input])
            result.push_back(matrix[input]);
    }
    return result;
}

muse::Val au::importexport::utils::matrixToVal(const std::vector<std::vector<bool> >& matrix)
{
    muse::ValList rows;
    rows.reserve(matrix.size());

    for (const auto& row : matrix) {
        muse::ValList cols;
        cols.reserve(row.size());
        for (bool val : row) {
            cols.emplace_back(muse::Val(val));
        }
        rows.emplace_back(muse::Val(cols));
    }

    return muse::Val(rows);
}

std::vector<std::vector<bool> > au::importexport::utils::valToMatrix(const muse::Val& val)
{
    std::vector<std::vector<bool> > matrix;

    if (val.type() != muse::Val::Type::List) {
        return matrix;
    }

    const muse::ValList rows = val.toList();
    matrix.resize(rows.size());

    for (size_t rIdx = 0; rIdx < rows.size(); ++rIdx) {
        if (rows[rIdx].type() != muse::Val::Type::List) {
            continue;
        }

        const muse::ValList cols = rows[rIdx].toList();
        matrix[rIdx].resize(cols.size());

        for (size_t cIdx = 0; cIdx < cols.size(); ++cIdx) {
            matrix[rIdx][cIdx] = cols[cIdx].toBool();
        }
    }

    return matrix;
}
