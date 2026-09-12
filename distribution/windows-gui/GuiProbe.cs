// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
// Runs only on a disposable Windows CI desktop. No WaveWeft/Qt code is loaded
// into this .NET Framework UI Automation observer.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Automation;
using System.Windows.Forms;

namespace WaveQuayQualification
{
    public sealed class OwnedJob : IDisposable
    {
        private IntPtr handle;
        [StructLayout(LayoutKind.Sequential)] private struct BasicLimits
        {
            public long PerProcess, PerJob;
            public uint Flags;
            public UIntPtr MinWorking, MaxWorking;
            public uint ActiveProcesses;
            public UIntPtr Affinity;
            public uint Priority, Scheduling;
        }
        [StructLayout(LayoutKind.Sequential)] private struct IoCounters
        {
            public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes;
        }
        [StructLayout(LayoutKind.Sequential)] private struct Limits
        {
            public BasicLimits Basic;
            public IoCounters Io;
            public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
        }
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateJobObject(IntPtr attributes, string name);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref Limits info, uint size);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        public OwnedJob()
        {
            handle = CreateJobObject(IntPtr.Zero, null);
            if (handle == IntPtr.Zero) throw new Win32Exception();
            var limits = new Limits();
            limits.Basic.Flags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if (!SetInformationJobObject(handle, 9, ref limits, (uint)Marshal.SizeOf(limits)))
            {
                int error = Marshal.GetLastWin32Error();
                Dispose();
                throw new Win32Exception(error);
            }
        }
        public void Assign(Process process)
        {
            if (!AssignProcessToJobObject(handle, process.Handle)) throw new Win32Exception();
        }
        public void Dispose()
        {
            if (handle != IntPtr.Zero)
            {
                if (!CloseHandle(handle)) throw new Win32Exception();
                handle = IntPtr.Zero;
            }
        }
    }

    public static class GuiProbe
    {
        private static readonly string[] Pages = { "Select a theme", "Clip visualization", "What UI layout (workspace) do you want?" };
        private static readonly string[] Buttons = { "Next", "Next", "Accept & continue" };
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 16000000 };
        [StructLayout(LayoutKind.Sequential)] private struct Rect { public int Left, Top, Right, Bottom; }
        [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
        [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr window, int command);
        [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
        [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr window, out Rect rect);
        [DllImport("user32.dll")] private static extern bool SetProcessDPIAware();

        [StructLayout(LayoutKind.Sequential)] private struct NativePoint { public int X, Y; }
        [StructLayout(LayoutKind.Sequential)] private struct MouseInput
        {
            public int X, Y;
            public uint Data, Flags, Time;
            public UIntPtr ExtraInfo;
        }
        [StructLayout(LayoutKind.Explicit)] private struct InputUnion
        {
            [FieldOffset(0)] public MouseInput Mouse;
        }
        [StructLayout(LayoutKind.Sequential)] private struct Input
        {
            public uint Type;
            public InputUnion Value;
        }
        [DllImport("user32.dll")] private static extern IntPtr WindowFromPoint(NativePoint point);
        [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr window, uint flags);
        [DllImport("user32.dll", SetLastError = true)] private static extern bool SetCursorPos(int x, int y);
        [DllImport("user32.dll", SetLastError = true)] private static extern bool GetCursorPos(out NativePoint point);
        [DllImport("user32.dll", SetLastError = true)] private static extern uint SendInput(uint count, Input[] inputs, int size);

        private static Dictionary<string, object> D(params object[] pairs)
        {
            var d = new Dictionary<string, object>();
            for (int i = 0; i < pairs.Length; i += 2) d.Add((string)pairs[i], pairs[i + 1]);
            return d;
        }
        private static void Save(string path, object value)
        {
            File.WriteAllText(path, Json.Serialize(value), new UTF8Encoding(false));
        }
        private static string Hash(string path)
        {
            using (var input = File.OpenRead(path))
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
        }
        private static void Alive(Process process)
        {
            if (process.HasExited) throw new InvalidOperationException("WaveWeft exited early with code " + process.ExitCode);
        }
        private static void NoReparsePath(string path)
        {
            for (var info = new DirectoryInfo(path); info != null; info = info.Parent)
                if ((info.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("Reparse-point path: " + info.FullName);
        }
        private static List<AutomationElement> Windows(int processId, ref int transientAutomationElements)
        {
            var result = new List<AutomationElement>();
            var handles = new HashSet<int>();
            var roots = AutomationElement.RootElement.FindAll(TreeScope.Children,
                new PropertyCondition(AutomationElement.ProcessIdProperty, processId));
            // An owned QQuickView can be a descendant of the main UIA window,
            // rather than a direct desktop child. Search only these PID roots.
            foreach (AutomationElement root in roots)
            {
                try
                {
                    var windows = root.FindAll(TreeScope.Element | TreeScope.Descendants,
                        new AndCondition(new PropertyCondition(AutomationElement.ProcessIdProperty, processId),
                            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Window)));
                    if (windows.Count > 3000) throw new InvalidOperationException("Owned UIA window collection exceeded bound");
                    foreach (AutomationElement window in windows)
                    {
                        try
                        {
                            var current = window.Current;
                            uint nativePid;
                            if (current.ProcessId != processId || current.NativeWindowHandle == 0
                                || GetWindowThreadProcessId(new IntPtr(current.NativeWindowHandle), out nativePid) == 0
                                || nativePid != (uint)processId)
                                throw new InvalidOperationException("UIA/native window ownership differs from the retained process");
                            if (handles.Add(current.NativeWindowHandle)) result.Add(window);
                        }
                        catch (ElementNotAvailableException) { transientAutomationElements++; }
                    }
                }
                catch (ElementNotAvailableException) { transientAutomationElements++; }
            }
            return result;
        }
        private static bool TryWindow<T>(AutomationElement window, Func<AutomationElement, T> operation, out T value)
        {
            try
            {
                value = operation(window);
                return true;
            }
            catch (ElementNotAvailableException)
            {
                // Top-level UIA elements are snapshots of native windows. A
                // splash/onboarding transition may destroy one after FindAll
                // and before its properties or descendants are read. Only
                // this documented stale-element condition is retryable.
                value = default(T);
                return false;
            }
        }
        private static void Visit(AutomationElement node, int depth, List<Dictionary<string, object>> tree)
        {
            if (depth > 40 || tree.Count >= 3000) throw new InvalidOperationException("UI Automation tree exceeded bounded capture");
            var current = node.Current;
            object pattern;
            bool invoke = node.TryGetCurrentPattern(InvokePattern.Pattern, out pattern);
            tree.Add(D("name", current.Name, "automationId", current.AutomationId, "controlType", current.ControlType.ProgrammaticName.Replace("ControlType.", ""),
                "className", current.ClassName, "processId", current.ProcessId, "enabled", current.IsEnabled,
                "nativeWindowHandle", current.NativeWindowHandle,
                "offscreen", current.IsOffscreen, "invoke", invoke,
                "bounds", new double[] { current.BoundingRectangle.X, current.BoundingRectangle.Y, current.BoundingRectangle.Width, current.BoundingRectangle.Height }));
            var walker = TreeWalker.RawViewWalker;
            for (var child = walker.GetFirstChild(node); child != null; child = walker.GetNextSibling(child)) Visit(child, depth + 1, tree);
        }
        private static List<Dictionary<string, object>> Tree(AutomationElement window)
        {
            var tree = new List<Dictionary<string, object>>();
            Visit(window, 0, tree);
            return tree;
        }
        private static bool Has(List<Dictionary<string, object>> tree, string name, int pid, bool button)
        {
            return tree.Exists(n => (string)n["name"] == name && (int)n["processId"] == pid && (bool)n["enabled"]
                && !(bool)n["offscreen"] && (!button || (string)n["controlType"] == "Button"));
        }
        private static void RejectDialogs(List<AutomationElement> windows, bool onboardingAllowed, ref int transientAutomationElements)
        {
            foreach (var window in windows)
            {
                string problem;
                if (!TryWindow(window, candidate =>
                {
                    var c = candidate.Current;
                    if (onboardingAllowed && c.Name == "Getting started") return null;
                    object p;
                    bool modal = candidate.TryGetCurrentPattern(WindowPattern.Pattern, out p) && ((WindowPattern)p).Current.IsModal;
                    if (!c.IsOffscreen && (modal || c.ClassName == "#32770"
                        || Regex.IsMatch(c.Name, @"\b(error|fatal|exception|warning)\b", RegexOptions.IgnoreCase)))
                        return "Unexpected native/modal dialog: " + c.Name;
                    return null;
                }, out problem))
                {
                    transientAutomationElements++;
                    continue;
                }
                if (problem != null) throw new InvalidOperationException(problem);
            }
        }
        private static Dictionary<string, object> Screenshot(AutomationElement window, string directory, string filename, int pid)
        {
            var handle = new IntPtr(window.Current.NativeWindowHandle);
            if (handle == IntPtr.Zero) throw new InvalidOperationException("No native window for screenshot");
            ShowWindow(handle, 9); // SW_RESTORE, only the owned window
            SetForegroundWindow(handle);
            Thread.Sleep(250);
            uint foregroundPid;
            GetWindowThreadProcessId(GetForegroundWindow(), out foregroundPid);
            if (foregroundPid != pid) throw new InvalidOperationException("Owned window is not foreground; screenshot would be misleading");
            Rect rect;
            if (!GetWindowRect(handle, out rect)) throw new Win32Exception();
            Rectangle bounds = Rectangle.FromLTRB(rect.Left, rect.Top, rect.Right, rect.Bottom);
            Rectangle desktop = SystemInformation.VirtualScreen;
            if (bounds.Width < 400 || bounds.Height < 300 || !desktop.Contains(bounds))
                throw new InvalidOperationException("Window is too small or outside the visible desktop");
            string path = Path.Combine(directory, filename);
            using (var bitmap = new Bitmap(bounds.Width, bounds.Height))
            {
                using (var graphics = Graphics.FromImage(bitmap))
                    graphics.CopyFromScreen(bounds.Location, Point.Empty, bounds.Size, CopyPixelOperation.SourceCopy);
                var colors = new HashSet<int>();
                for (int y = 0; y < bitmap.Height; y += 5)
                    for (int x = 0; x < bitmap.Width; x += 5) colors.Add(bitmap.GetPixel(x, y).ToArgb());
                bitmap.Save(path, ImageFormat.Png);
                return D("path", filename, "sha256", Hash(path), "width", bounds.Width, "height", bounds.Height, "sampledColors", colors.Count);
            }
        }
        private static AutomationElement NextButton(AutomationElement window, string button, int pid)
        {
            var found = window.FindAll(TreeScope.Descendants, new AndCondition(
                new PropertyCondition(AutomationElement.NameProperty, button),
                new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button),
                new PropertyCondition(AutomationElement.ProcessIdProperty, pid),
                new PropertyCondition(AutomationElement.IsEnabledProperty, true),
                new PropertyCondition(AutomationElement.IsOffscreenProperty, false)));
            if (found.Count != 1) throw new InvalidOperationException("Expected exactly one enabled visible onboarding button");
            return found[0];
        }
        private static ButtonInputSnapshot InputSnapshot(Process process, AutomationElement window, string button)
        {
            process.Refresh();
            Alive(process);
            var target = NextButton(window, button, process.Id).Current;
            var dialog = window.Current;
            var handle = new IntPtr(dialog.NativeWindowHandle);
            Rect rectangle;
            if (handle == IntPtr.Zero || !GetWindowRect(handle, out rectangle)) throw new Win32Exception();
            var bounds = target.BoundingRectangle;
            var point = new NativePoint { X = (int)Math.Floor(bounds.X + bounds.Width / 2), Y = (int)Math.Floor(bounds.Y + bounds.Height / 2) };
            var foreground = GetForegroundWindow();
            var hit = WindowFromPoint(point);
            uint nativePid, foregroundPid, hitPid;
            GetWindowThreadProcessId(handle, out nativePid);
            GetWindowThreadProcessId(foreground, out foregroundPid);
            GetWindowThreadProcessId(hit, out hitPid);
            var desktop = SystemInformation.VirtualScreen;
            return new ButtonInputSnapshot {
                name = target.Name, controlType = target.ControlType.ProgrammaticName.Replace("ControlType.", ""),
                enabled = target.IsEnabled, offscreen = target.IsOffscreen, processId = target.ProcessId, matchingButtons = 1,
                windowTitle = dialog.Name, windowHandle = handle.ToInt64(), nativeWindowProcessId = checked((int)nativePid),
                foregroundHandle = foreground.ToInt64(), foregroundProcessId = checked((int)foregroundPid),
                hitRootHandle = GetAncestor(hit, 2).ToInt64(), hitProcessId = checked((int)hitPid),
                buttonBounds = new double[] { bounds.X, bounds.Y, bounds.Width, bounds.Height },
                windowBounds = new double[] { rectangle.Left, rectangle.Top, rectangle.Right - rectangle.Left, rectangle.Bottom - rectangle.Top },
                desktopBounds = new double[] { desktop.X, desktop.Y, desktop.Width, desktop.Height },
                point = new int[] { point.X, point.Y }
            };
        }
        private static void Advance(Process process, AutomationElement window, Dictionary<string, object> observation, string button)
        {
            // The real Next button is visible in the provider, but Muse does not
            // expose InvokePattern for it. Do not infer its action from the name
            // of Page.qml's separately focused screen-reader surrogate.
            var handle = new IntPtr(window.Current.NativeWindowHandle);
            var before = InputSnapshot(process, window, button);
            observation["inputBefore"] = before;
            OnboardingInput.Validate(before, button, process.Id, handle.ToInt64());
            object pattern;
            var candidate = NextButton(window, button, process.Id);
            if (candidate.TryGetCurrentPattern(InvokePattern.Pattern, out pattern))
            {
                var finalInvoke = InputSnapshot(process, window, button);
                OnboardingInput.RequireStable(before, finalInvoke, button, process.Id, handle.ToInt64());
                ((InvokePattern)pattern).Invoke();
                observation["interaction"] = "uia-invoke";
                return;
            }
            if (!SetCursorPos(before.point[0], before.point[1])) throw new Win32Exception();
            var final = InputSnapshot(process, window, button);
            observation["inputFinal"] = final;
            OnboardingInput.RequireStable(before, final, button, process.Id, handle.ToInt64());
            NativePoint cursor;
            if (!GetCursorPos(out cursor) || cursor.X != final.point[0] || cursor.Y != final.point[1])
                throw new InvalidOperationException("Cursor moved away from the observed owned button before input");
            observation["cursorPosition"] = new int[] { cursor.X, cursor.Y };
            // Mouse down/up use one native call, after final ownership and hit
            // checks. No coordinates are guessed or retained across page changes.
            var inputs = new[] {
                new Input { Type = 0, Value = new InputUnion { Mouse = new MouseInput { Flags = 0x0002 } } },
                new Input { Type = 0, Value = new InputUnion { Mouse = new MouseInput { Flags = 0x0004 } } }
            };
            uint sent = SendInput(2, inputs, Marshal.SizeOf(typeof(Input)));
            observation["sentInputs"] = sent;
            if (sent != 2)
            {
                int error = Marshal.GetLastWin32Error();
                // A partially inserted pair must never count as advancement.
                // Release a possibly pressed button only while the same owned
                // target and cursor are still proved; otherwise retain the error.
                if (sent == 1)
                {
                    try
                    {
                        var release = InputSnapshot(process, window, button);
                        OnboardingInput.RequireStable(final, release, button, process.Id, handle.ToInt64());
                        if (!GetCursorPos(out cursor) || cursor.X != release.point[0] || cursor.Y != release.point[1])
                            throw new InvalidOperationException("Cannot release partial mouse input after cursor movement");
                        observation["partialInputReleaseSent"] = SendInput(1, new[] { inputs[1] }, Marshal.SizeOf(typeof(Input)));
                    }
                    catch (Exception releaseError) { observation["partialInputReleaseError"] = releaseError.Message; }
                }
                throw new Win32Exception(error, "Native onboarding click was incomplete");
            }
            observation["interaction"] = "owned-native-button-click";
        }
        private static List<Dictionary<string, object>> Modules(Process process)
        {
            process.Refresh();
            var result = new List<Dictionary<string, object>>();
            foreach (ProcessModule module in process.Modules)
            {
                NoReparsePath(Path.GetDirectoryName(module.FileName));
                if ((File.GetAttributes(module.FileName) & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("Redirected runtime module: " + module.FileName);
                result.Add(D("path", Path.GetFullPath(module.FileName), "sha256", Hash(module.FileName), "version", module.FileVersionInfo.FileVersion));
            }
            return result;
        }
        private static List<Dictionary<string, object>> FreshState()
        {
            // Qt QStandardPaths uses Windows known folders; APPDATA redirection
            // alone is not profile isolation. Never erase or inject preferences.
            var roots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var folder in new[] { Environment.SpecialFolder.LocalApplicationData, Environment.SpecialFolder.ApplicationData })
                foreach (var app in new[] { "Audacity4Development", "Audacity4", "WaveQuay", "WaveQuay4", "WaveQuay 4", "WaveWeft", "WaveWeft1", "WaveWeft 1" })
                {
                    // main.cpp currently uses Trieflow / Audacity4Development.
                    // QSettings' non-portable INI is beside, not inside, the app directory.
                    roots.Add(Path.Combine(Environment.GetFolderPath(folder), "Trieflow", app));
                    roots.Add(Path.Combine(Environment.GetFolderPath(folder), "Trieflow", app + ".ini"));
                    roots.Add(Path.Combine(Environment.GetFolderPath(folder), "Trieflow LLC", app));
                    roots.Add(Path.Combine(Environment.GetFolderPath(folder), "Trieflow LLC", app + ".ini"));
                    roots.Add(Path.Combine(Environment.GetFolderPath(folder), app));
                    roots.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), app));
                }
            var state = new List<Dictionary<string, object>>();
            foreach (string path in roots) state.Add(D("path", path, "exists", Directory.Exists(path) || File.Exists(path)));
            return state;
        }
        public static int Run(string stage, string directory, string sourceCommit, string expectedMainWindowTitle)
        {
            SetProcessDPIAware();
            stage = Path.GetFullPath(stage).TrimEnd(Path.DirectorySeparatorChar);
            directory = Path.GetFullPath(directory);
            Directory.CreateDirectory(directory);
            string system = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            string executable = Path.Combine(stage, "bin", "WaveWeft.exe");
            string reportPath = Path.Combine(directory, "gui-observations.json");
            var events = new List<Dictionary<string, object>>();
            var errors = new List<string>();
            var report = D("schemaVersion", 1, "sourceCommit", sourceCommit, "stageRoot", stage, "systemRoot", system,
                "executable", executable, "expectedMainWindowTitle", expectedMainWindowTitle, "arguments", new string[0], "events", events, "errors", errors, "survivedUntilCleanup", false,
                "transientAutomationElements", 0, "cleanup", D("ownedJobClosed", false, "processExited", false));
            Process process = null;
            OwnedJob job = null;
            StreamWriter stdout = null, stderr = null;
            var clock = Stopwatch.StartNew();
            int transientAutomationElements = 0;
            try
            {
                if (String.IsNullOrWhiteSpace(expectedMainWindowTitle) || expectedMainWindowTitle.IndexOfAny(new[] { '\r', '\n' }) >= 0)
                    throw new ArgumentException("Expected a single exact configured main-window title");
                NoReparsePath(stage);
                if (!File.Exists(executable) || (File.GetAttributes(executable) & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("Missing or redirected staged WaveWeft executable");
                NoReparsePath(Path.GetDirectoryName(executable));
                var state = FreshState();
                report["userStateBefore"] = state;
                Save(reportPath, report);
                if (state.Exists(entry => (bool)entry["exists"])) throw new IOException("WaveWeft profile state already exists; need a fresh disposable runner");
                string privateRoot = Path.Combine(directory, "private-environment");
                if (Directory.Exists(privateRoot)) throw new IOException("GUI probe environment already exists; use a new evidence directory");
                var start = new ProcessStartInfo(executable) { UseShellExecute = false, WorkingDirectory = Path.Combine(stage, "bin"), RedirectStandardOutput = true, RedirectStandardError = true };
                start.EnvironmentVariables.Clear();
                var env = new Dictionary<string, string> {
                    { "PATH", Path.Combine(stage, "bin") + ";" + Path.Combine(system, "System32") + ";" + system },
                    { "SystemRoot", system }, { "WINDIR", system }, { "SystemDrive", Path.GetPathRoot(system).TrimEnd('\\') },
                    { "COMSPEC", Path.Combine(system, "System32", "cmd.exe") },
                    { "USERPROFILE", privateRoot }, { "APPDATA", Path.Combine(privateRoot, "Roaming") },
                    { "LOCALAPPDATA", Path.Combine(privateRoot, "Local") }, { "TEMP", Path.Combine(privateRoot, "Temp") }, { "TMP", Path.Combine(privateRoot, "Temp") },
                    { "CI", "true" }, { "WAVEQUAY_STARTUP_DIAGNOSTICS", "1" },
                    { "LANG", "en_US.UTF-8" }, { "QT_FORCE_STDERR_LOGGING", "1" }, { "QT_DEBUG_PLUGINS", "1" }
                };
                foreach (var variable in env) start.EnvironmentVariables.Add(variable.Key, variable.Value);
                foreach (string key in new[] { "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP" }) Directory.CreateDirectory(env[key]);
                report["environment"] = env;
                report["executableSha256"] = Hash(executable);
                stdout = new StreamWriter(Path.Combine(directory, "stdout.log"), false, new UTF8Encoding(false)) { AutoFlush = true };
                stderr = new StreamWriter(Path.Combine(directory, "stderr.log"), false, new UTF8Encoding(false)) { AutoFlush = true };
                process = new Process { StartInfo = start };
                process.OutputDataReceived += (sender, e) => { if (e.Data != null) stdout.WriteLine(e.Data); };
                process.ErrorDataReceived += (sender, e) => { if (e.Data != null) stderr.WriteLine(e.Data); };
                job = new OwnedJob();
                if (!process.Start()) throw new IOException("Process.Start failed");
                report["processId"] = process.Id;
                // Assign before any UI work. If assignment fails, finally kills this
                // exact Process handle; no process-name based cleanup is used.
                job.Assign(process);
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                report["startedUtc"] = process.StartTime.ToUniversalTime().ToString("o");
                Save(reportPath, report);
                int page = 0;
                long firstMain = -1;
                while (clock.ElapsedMilliseconds < 90000)
                {
                    Alive(process);
                    var windows = Windows(process.Id, ref transientAutomationElements);
                    var diagnostics = new List<object>();
                    foreach (var window in windows)
                    {
                        Dictionary<string, object> diagnostic;
                        if (TryWindow(window, candidate => D("title", candidate.Current.Name, "tree", Tree(candidate)), out diagnostic))
                            diagnostics.Add(diagnostic);
                        else transientAutomationElements++;
                    }
                    Save(Path.Combine(directory, "latest-ui-tree.json"), diagnostics);
                    RejectDialogs(windows, page < 3, ref transientAutomationElements);
                    if (page < 3)
                    {
                        foreach (var window in windows)
                        {
                            try
                            {
                                if (window.Current.Name != "Getting started" || window.Current.IsOffscreen) continue;
                                var tree = Tree(window);
                                if (!Has(tree, Pages[page], process.Id, false) && !Has(tree, Pages[page] + ". " + Buttons[page], process.Id, true)) continue;
                                // Allow the source's one-second page accessibility timer to settle.
                                Thread.Sleep(1200);
                                tree = Tree(window);
                                var observation = D("kind", "onboarding", "title", window.Current.Name, "page", Pages[page], "button", Buttons[page],
                                    "processId", process.Id, "elapsedMs", clock.ElapsedMilliseconds, "tree", tree,
                                    "screenshot", Screenshot(window, directory, "onboarding-" + (page + 1) + ".png", process.Id));
                                events.Add(observation);
                                Save(reportPath, report);
                                Advance(process, window, observation, Buttons[page]);
                                Save(reportPath, report);
                                page++;
                                break;
                            }
                            catch (ElementNotAvailableException) { transientAutomationElements++; }
                        }
                    }
                    else
                    {
                        foreach (var window in windows)
                        {
                            try
                            {
                                if (window.Current.Name != expectedMainWindowTitle || window.Current.IsOffscreen) continue;
                                var tree = Tree(window);
                                // Muse prefixes the focused control with its current panel name.
                                // Both exact forms still require an owned, enabled, visible Button.
                                if (!Has(tree, "Playback toolbar", process.Id, false) || !(Has(tree, "Add track", process.Id, true) || Has(tree, "Add track panel, Add track", process.Id, true))) continue;
                                if (firstMain >= 0 && clock.ElapsedMilliseconds - firstMain < 3000) continue;
                                var observation = D("kind", "main-window", "title", window.Current.Name, "processId", process.Id,
                                    "elapsedMs", clock.ElapsedMilliseconds, "tree", tree,
                                    "screenshot", Screenshot(window, directory, firstMain < 0 ? "main-window-initial.png" : "main-window-stable.png", process.Id));
                                events.Add(observation);
                                report["modules"] = Modules(process);
                                Save(reportPath, report);
                                if (firstMain >= 0)
                                {
                                    Alive(process);
                                    report["survivedUntilCleanup"] = true;
                                    return 0;
                                }
                                firstMain = clock.ElapsedMilliseconds;
                                break;
                            }
                            catch (ElementNotAvailableException) { transientAutomationElements++; }
                        }
                    }
                    Thread.Sleep(300);
                }
                throw new TimeoutException("Genuine three-page onboarding and stable editor not observed within 90 seconds");
            }
            catch (Exception error)
            {
                errors.Add(error.ToString());
                if (process != null)
                {
                    try
                    {
                        if (!process.HasExited)
                        {
                            report["modules"] = Modules(process);
                            foreach (var window in Windows(process.Id, ref transientAutomationElements))
                            {
                                try
                                {
                                    if (!window.Current.IsOffscreen)
                                    {
                                        report["failureScreenshot"] = Screenshot(window, directory, "failure-window.png", process.Id);
                                        break;
                                    }
                                }
                                catch (ElementNotAvailableException) { transientAutomationElements++; }
                                catch (InvalidOperationException diagnosticError) { errors.Add("Diagnostics: " + diagnosticError); }
                            }
                        }
                        else report["earlyExitCode"] = process.ExitCode;
                    }
                    catch (Exception diagnosticError) { errors.Add("Diagnostics: " + diagnosticError); }
                }
                return 1;
            }
            finally
            {
                bool closed = false, exited = false;
                try
                {
                    if (process != null && (bool)report["survivedUntilCleanup"] && process.HasExited)
                    {
                        report["survivedUntilCleanup"] = false;
                        errors.Add("Process exited before owned cleanup: " + process.ExitCode);
                    }
                    if (job != null) { job.Dispose(); closed = true; }
                    if (process != null)
                    {
                        try
                        {
                            if (!process.HasExited && !process.WaitForExit(5000)) process.Kill();
                            exited = process.WaitForExit(5000);
                            if (exited) process.WaitForExit(); // drain asynchronous stdout/stderr callbacks
                        }
                        catch (Exception error) { errors.Add("Owned process cleanup: " + error); }
                    }
                }
                catch (Exception error) { errors.Add("Owned job cleanup: " + error); }
                report["cleanup"] = D("ownedJobClosed", closed, "processExited", exited);
                report["transientAutomationElements"] = transientAutomationElements;
                report["finishedUtc"] = DateTime.UtcNow.ToString("o");
                Save(reportPath, report);
                if (exited)
                {
                    if (stdout != null) stdout.Dispose();
                    if (stderr != null) stderr.Dispose();
                    if (process != null) process.Dispose();
                }
            }
        }

        public static string SelfTest()
        {
            if (IntPtr.Size != 8 || Marshal.SizeOf(typeof(Input)) != 40 || Marshal.OffsetOf(typeof(Input), "Value").ToInt32() != 8
                || Marshal.SizeOf(typeof(MouseInput)) != 32 || Marshal.SizeOf(typeof(NativePoint)) != 8)
                throw new InvalidOperationException("Native x64 mouse input structure layout differs");
            string ignored;
            bool staleIgnored = !TryWindow<string>(AutomationElement.RootElement,
                element => { throw new ElementNotAvailableException("Destroyed native-window fixture"); }, out ignored);
            bool otherErrorPropagated = false;
            try
            {
                TryWindow<string>(AutomationElement.RootElement,
                    element => { throw new InvalidOperationException("Non-stale fixture"); }, out ignored);
            }
            catch (InvalidOperationException) { otherErrorPropagated = true; }
            if (!staleIgnored || !otherErrorPropagated)
                throw new InvalidOperationException("Transient UIA exception boundary self-test failed");
            // Real Windows interop fixture, not product GUI qualification.
            var start = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),
                "WindowsPowerShell", "v1.0", "powershell.exe"), "-NoProfile -NonInteractive -Command Start-Sleep -Seconds 60")
                { UseShellExecute = false, CreateNoWindow = true };
            using (var child = Process.Start(start))
            {
                try
                {
                    using (var job = new OwnedJob())
                    {
                        job.Assign(child);
                        Thread.Sleep(100);
                        if (child.HasExited) throw new InvalidOperationException("Cleanup fixture exited before job closure");
                    }
                    if (!child.WaitForExit(5000)) throw new InvalidOperationException("Owned job failed to stop its real child");
                }
                finally { if (!child.HasExited) child.Kill(); }
            }
            return Json.Serialize(D("nativeMouseInputAbiVerified", true, "ownedJobCleanup", true, "staleAutomationElementIgnored", staleIgnored,
                "nonStaleAutomationErrorPropagated", otherErrorPropagated, "desktopUiaName", AutomationElement.RootElement.Current.Name,
                "uiaAssembly", typeof(AutomationElement).Assembly.Location, "framework", Environment.Version.ToString(),
                "windows", Environment.OSVersion.ToString()));
        }
    }
}
