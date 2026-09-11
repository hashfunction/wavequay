// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
// Portable replay of the actual observer discovery method. The UIA/Win32
// adapters model the retained root/owned-popup shape; this is not native UIA.
using System;
using System.Collections.Generic;
using System.Reflection;

[Flags] enum TreeScope { Element = 1, Children = 2, Descendants = 4 }
static class ControlType { public static readonly object Window = new object(); }
abstract class Condition { public abstract bool Matches(AutomationElement element); }
sealed class PropertyCondition : Condition
{
    object property, value;
    public PropertyCondition(object property, object value) { this.property = property; this.value = value; }
    public override bool Matches(AutomationElement element)
    {
        return Object.Equals(property == AutomationElement.ProcessIdProperty ? (object)element.State.ProcessId : element.State.ControlType, value);
    }
}
sealed class AndCondition : Condition
{
    Condition[] conditions;
    public AndCondition(params Condition[] conditions) { this.conditions = conditions; }
    public override bool Matches(AutomationElement element)
    {
        foreach (var condition in conditions) if (!condition.Matches(element)) return false;
        return true;
    }
}
sealed class ElementNotAvailableException : Exception { }
sealed class AutomationElement
{
    public sealed class Information
    {
        public string Name;
        public int ProcessId, NativeWindowHandle;
        public object ControlType = ControlTypeWindow;
    }
    static readonly object ControlTypeWindow = ControlType.Window;
    public static readonly object ProcessIdProperty = new object(), ControlTypeProperty = new object();
    public static AutomationElement RootElement;
    public Information State = new Information();
    public Exception ReadFailure;
    public Information Current { get { if (ReadFailure != null) throw ReadFailure; return State; } }
    public List<AutomationElement> Children = new List<AutomationElement>();
    public List<AutomationElement> FindAll(TreeScope scope, Condition condition)
    {
        var result = new List<AutomationElement>();
        if ((scope & TreeScope.Element) != 0 && condition.Matches(this)) result.Add(this);
        foreach (var child in Children)
        {
            if ((scope & (TreeScope.Children | TreeScope.Descendants)) != 0 && condition.Matches(child)) result.Add(child);
            if ((scope & TreeScope.Descendants) != 0) result.AddRange(child.FindAll(TreeScope.Descendants, condition));
        }
        return result;
    }
}
static class GuiProbe
{
    static readonly Dictionary<int, uint> Owners = new Dictionary<int, uint>();
    static uint GetWindowThreadProcessId(IntPtr handle, out uint pid)
    {
        if (!Owners.TryGetValue(handle.ToInt32(), out pid)) return 0;
        return 1;
    }

    // ACTUAL_WINDOWS_METHOD

    static AutomationElement Make(string name, int handle, int pid)
    {
        Owners[handle] = (uint)pid;
        return new AutomationElement { State = new AutomationElement.Information { Name = name, NativeWindowHandle = handle, ProcessId = pid } };
    }
    static List<AutomationElement> Discover(out int discarded)
    {
        var method = typeof(GuiProbe).GetMethod("Windows", BindingFlags.NonPublic | BindingFlags.Static);
        object[] arguments = method.GetParameters().Length == 1 ? new object[] { 1532 } : new object[] { 1532, 0 };
        try
        {
            var result = (List<AutomationElement>)method.Invoke(null, arguments);
            discarded = arguments.Length == 1 ? 0 : (int)arguments[1];
            return result;
        }
        catch (TargetInvocationException error) { throw error.InnerException; }
    }
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static void Reject(string scenario)
    {
        int count;
        try { Discover(out count); }
        catch (InvalidOperationException) { return; }
        throw new Exception("Accepted " + scenario);
    }
    public static int Main()
    {
        try
        {
            var desktop = Make("Desktop", 1, 1);
            var main = Make("WaveQuay 4.0", 101, 1532);
            var popup = Make("Getting started", 202, 1532);
            // The real run's desktop-child list contained only main; its tree
            // contained the owned Getting started Window as a descendant.
            desktop.Children.Add(main); main.Children.Add(popup);
            AutomationElement.RootElement = desktop;
            int discarded;
            var result = Discover(out discarded);
            Check(result.Count == 2 && result.Contains(popup), "Owned descendant Getting started was omitted");

            main.Children.Add(Make("Getting started", 303, 999));
            Check(Discover(out discarded).Count == 2, "Foreign UIA PID was included");
            main.Children.Add(popup);
            Check(Discover(out discarded).Count == 2, "Native window handle was duplicated");
            main.Children.RemoveAt(main.Children.Count - 1);
            Owners[202] = 999; Reject("native HWND owned by another process"); Owners[202] = 1532;
            popup.State.NativeWindowHandle = 0; Reject("zero native HWND"); popup.State.NativeWindowHandle = 202;
            popup.ReadFailure = new ElementNotAvailableException();
            Check(Discover(out discarded).Count == 1 && discarded == 1, "Stale element was not separately counted");
            popup.ReadFailure = new InvalidOperationException("Real provider failure"); Reject("non-stale provider failure");
            popup.ReadFailure = null;
            Check(Discover(out discarded).Count == 2, "Discovery did not recover after a transient element");
            Console.WriteLine("PASS: actual discovery method; owned descendant, foreign PID/HWND, zero handle, duplicate, stale and provider-error boundaries");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
