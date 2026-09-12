// SPDX-License-Identifier: GPL-3.0-only
using System;
using System.IO;
namespace WaveQuayQualification {
    public static class AccessibilityGraphCapture {
        public static string Prepare(bool enabled, string privateRoot, string token, string identityMode) {
            if (!enabled) return null;
            if (identityMode != null) throw new InvalidOperationException("Graph diagnostics are staged-only and cannot qualify an installed package");
            Guid parsed;
            if (String.IsNullOrEmpty(privateRoot) || !Path.IsPathRooted(privateRoot) ||
                Path.GetFullPath(privateRoot) != privateRoot ||
                Path.GetFileName(privateRoot) != "private-environment" || !Guid.TryParse(token, out parsed) || parsed.ToString() != token)
                throw new IOException("Invalid graph diagnostic private root");
            for (var directory = new DirectoryInfo(privateRoot); directory != null; directory = directory.Parent)
                if (!directory.Exists || (directory.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("Graph diagnostic directory is missing or redirected");
            string marker = Path.Combine(privateRoot, ".waveweft-consumer-owner");
            if (!File.Exists(marker) || (File.GetAttributes(marker) & FileAttributes.ReparsePoint) != 0 ||
                new FileInfo(marker).Length != 36 || File.ReadAllText(marker) != token)
                throw new IOException("Graph diagnostic ownership changed");
            string temp = Path.Combine(privateRoot, "Temp");
            if (!Directory.Exists(temp) || (File.GetAttributes(temp) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Graph diagnostic temporary directory is missing or redirected");
            string path = Path.Combine(temp, "accessibility-graph.jsonl");
            if (File.Exists(path) || Directory.Exists(path)) throw new IOException("Graph output already exists; preserving it");
            return path;
        }
    }
}
