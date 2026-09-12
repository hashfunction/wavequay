// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
using System;

namespace WaveQuayQualification
{
    // Scalar observations shared by the native input boundary and its tests.
    public sealed class ButtonInputSnapshot
    {
        public string name, controlType, windowTitle;
        public bool enabled, offscreen;
        public int processId, matchingButtons, nativeWindowProcessId, foregroundProcessId, hitProcessId;
        public long windowHandle, foregroundHandle, hitRootHandle;
        public double[] buttonBounds, windowBounds, desktopBounds;
        public int[] point;
    }

    public static class OnboardingInput
    {
        private static void Require(bool valid, string message)
        {
            if (!valid) throw new InvalidOperationException(message);
        }
        private static bool Rectangle(double[] b)
        {
            if (b == null || b.Length != 4) return false;
            foreach (double v in b) if (Double.IsNaN(v) || Double.IsInfinity(v)) return false;
            return b[2] > 0 && b[3] > 0;
        }
        private static bool Contains(double[] outer, double[] inner)
        {
            return inner[0] >= outer[0] && inner[1] >= outer[1]
                && inner[0] + inner[2] <= outer[0] + outer[2] && inner[1] + inner[3] <= outer[1] + outer[3];
        }
        public static void Validate(ButtonInputSnapshot s, string button, int pid, long window)
        {
            Require(s != null && pid > 0 && window != 0 && s.matchingButtons == 1 && s.name == button
                && s.controlType == "Button" && s.enabled && !s.offscreen && s.windowTitle == "Getting started",
                "No unique enabled visible onboarding button");
            Require(s.processId == pid && s.nativeWindowProcessId == pid && s.foregroundProcessId == pid
                && s.hitProcessId == pid && s.windowHandle == window && s.foregroundHandle == window && s.hitRootHandle == window,
                "Onboarding input window/foreground/point ownership changed");
            Require(Rectangle(s.buttonBounds) && Rectangle(s.windowBounds) && Rectangle(s.desktopBounds)
                && s.buttonBounds[2] >= 4 && s.buttonBounds[3] >= 4
                && Contains(s.windowBounds, s.buttonBounds) && Contains(s.desktopBounds, s.windowBounds),
                "Onboarding button or window is outside the visible desktop");
            Require(s.point != null && s.point.Length == 2
                && s.point[0] == (int)Math.Floor(s.buttonBounds[0] + s.buttonBounds[2] / 2)
                && s.point[1] == (int)Math.Floor(s.buttonBounds[1] + s.buttonBounds[3] / 2),
                "Input point differs from the observed button center");
        }
        private static bool Same(double[] a, double[] b)
        {
            if (a == null || b == null || a.Length != b.Length) return false;
            for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
            return true;
        }
        public static void RequireStable(ButtonInputSnapshot before, ButtonInputSnapshot final, string button, int pid, long window)
        {
            Validate(before, button, pid, window);
            Validate(final, button, pid, window);
            Require(Same(before.buttonBounds, final.buttonBounds) && Same(before.windowBounds, final.windowBounds)
                && Same(before.desktopBounds, final.desktopBounds), "Onboarding geometry changed before mouse input");
        }
    }
}
