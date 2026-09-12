// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
using System;
using System.IO;

namespace WaveQuayQualification
{
    public static class PrivateEnvironment
    {
        // The Win32 picker resolves Desktop under the redirected USERPROFILE.
        // Call only after ClaimConsumerProfile has marked the new private root.
        public static string PrepareDesktop(string root, string token)
        {
            Guid owner;
            if (String.IsNullOrEmpty(root) || !Path.IsPathRooted(root) ||
                !Guid.TryParse(token, out owner) || owner.ToString() != token)
                throw new IOException("Invalid claimed private environment");
            string marker = Path.Combine(root, ".waveweft-consumer-owner");
            if (!Directory.Exists(root) || (File.GetAttributes(root) & FileAttributes.ReparsePoint) != 0 ||
                !File.Exists(marker) || (File.GetAttributes(marker) & FileAttributes.ReparsePoint) != 0 ||
                new FileInfo(marker).Length != 36 || File.ReadAllText(marker) != token)
                throw new IOException("Private environment owner is missing or changed");
            string desktop = Path.Combine(root, "Desktop");
            if (Directory.Exists(desktop) || File.Exists(desktop))
                throw new IOException("Private Desktop already exists; preserving it");
            Directory.CreateDirectory(desktop);
            if ((File.GetAttributes(desktop) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Private Desktop is redirected");
            return desktop;
        }
    }
}
