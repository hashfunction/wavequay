/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Trieflow. Test-only empty effects host. */
#pragma once
#include "effects/effects_base/irealtimeeffectservice.h"
namespace au::effects
{
class EmptyRealtimeEffects : public IRealtimeEffectService
{
public:
    RealtimeEffectStatePtr addRealtimeEffect(TrackId trackId, const EffectId& effectId) override { return { }; }
    void removeRealtimeEffect(TrackId trackId, const RealtimeEffectStatePtr& state) override { }
    RealtimeEffectStatePtr replaceRealtimeEffect(TrackId trackId, int effectListIndex, const EffectId& newEffectId) override
    {
        return { };
    }
    RealtimeEffectStatePtr replaceRealtimeEffect(
        TrackId trackId, const RealtimeEffectStatePtr& state, const EffectId& newEffectId) override
    {
        return { };
    }
    void moveRealtimeEffect(const RealtimeEffectStatePtr& state, int newIndex) override { }
    muse::async::Channel<TrackId, RealtimeEffectStatePtr> realtimeEffectAdded() const override { return { }; }
    muse::async::Channel<TrackId, RealtimeEffectStatePtr> realtimeEffectRemoved() const override { return { }; }
    muse::async::Channel<TrackId, EffectChainLinkIndex, RealtimeEffectStatePtr> realtimeEffectReplaced() const override
    {
        return { };
    }
    muse::async::Channel<TrackId, EffectChainLinkIndex, EffectChainLinkIndex> realtimeEffectMoved() const override { return { }; }
    muse::async::Channel<TrackId> realtimeEffectStackChanged() const override { return { }; }
    muse::async::Notification effectSettingsChanged() const override { return { }; }
    std::optional<TrackId> trackId(const RealtimeEffectStatePtr& state) const override { return { }; }
    std::optional<std::string> effectName(const RealtimeEffectStatePtr& state) const override { return { }; }
    std::optional<std::string> effectTrackName(const RealtimeEffectStatePtr& state) const override { return { }; }
    std::optional<std::vector<RealtimeEffectStatePtr>> effectStack(TrackId trackId) const override { return { }; }
    bool isAvailable(const RealtimeEffectStatePtr& state) const override { return { }; }
    bool isActive(const RealtimeEffectStatePtr& state) const override { return { }; }
    void setIsActive(const RealtimeEffectStatePtr& state, bool) override { }
    muse::async::Channel<RealtimeEffectStatePtr> isActiveChanged() const override { return { }; }
    bool trackEffectsActive(TrackId trackId) const override { return { }; }
    void setTrackEffectsActive(TrackId trackId, bool active) override { }
};
}
