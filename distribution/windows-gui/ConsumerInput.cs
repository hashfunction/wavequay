// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
using System;
using System.Collections.Generic;

namespace WaveQuayQualification
{
    public sealed class ConsumerFilenameNode
    { public long window,parent;public int pid,id;public string className; }
    public sealed class ConsumerKeyboardSnapshot
    {
        public int pid, foregroundPid, nativeFocusPid, uiaFocusPid;
        public long window, main, foreground, active, nativeFocus, nativeFocusRoot;
        public bool owned, enabled, offscreen, expectedTargetContainsFocus;
        public string identity, title;
        public double[] windowBounds, desktopBounds;
    }
    public sealed class ConsumerInputSnapshot
    {
        public string name, role, title, identity;
        public int pid, nativePid, foregroundPid, hitPid, matches;
        public long window, foreground, hitRoot, main;
        public bool owned, enabled, offscreen;
        public double[] targetBounds, windowBounds, desktopBounds;
        public int[] point;
    }
    public static class ConsumerInput
    {
        public static bool FilenameChain(ConsumerFilenameNode[] nodes,int pid,long dialog,long edit)
        {
            if(nodes==null || pid<=0 || dialog==0 || edit==0 || dialog==edit || (nodes.Length!=3 && nodes.Length!=5))return false;
            foreach(var node in nodes)if(node==null)return false;
            string[] classes=nodes.Length==3?new[]{"Edit","ComboBox","ComboBoxEx32"}:new[]{"Edit","ComboBox","FloatNotifySink","DirectUIHWND","DUIViewWndClassName"};
            var seen=new HashSet<long>();
            for(int i=0;i<nodes.Length;i++)
            {
                var n=nodes[i];int id=nodes.Length==3?1148:i==0?1001:0;
                if(n==null || n.pid!=pid || n.id!=id || n.className!=classes[i] || n.window==0 || n.window==dialog || !seen.Add(n.window)
                    || n.parent!=(i==nodes.Length-1?dialog:nodes[i+1].window) || (i==0 && n.window!=edit))return false;
            }
            return true;
        }
        private static void Require(bool value, string message)
        { if (!value) throw new InvalidOperationException(message); }
        private static bool Rect(double[] r)
        {
            if (r == null || r.Length != 4 || r[2] < 2 || r[3] < 2) return false;
            foreach (double v in r) if (Double.IsNaN(v) || Double.IsInfinity(v)) return false;
            return true;
        }
        private static bool Contains(double[] outer, double[] inner)
        { return inner[0] >= outer[0] && inner[1] >= outer[1] && inner[0]+inner[2] <= outer[0]+outer[2] && inner[1]+inner[3] <= outer[1]+outer[3]; }
        private static bool Same(double[] a, double[] b)
        { if (a.Length != b.Length) return false; for (int i=0;i<a.Length;i++) if(a[i]!=b[i])return false; return true; }
        public static void Validate(ConsumerInputSnapshot s, string name, string role, string title, int pid, long main, long window)
        {
            Require(s != null && pid > 0 && main != 0 && window != 0 && s.matches == 1 && s.name == name && s.role == role
                && s.title == title && s.enabled && !s.offscreen && !String.IsNullOrEmpty(s.identity), "Consumer target is not unique, visible and exact");
            Require(s.pid==pid && s.nativePid==pid && s.foregroundPid==pid && s.hitPid==pid && s.main==main && s.window==window
                && s.foreground==window && s.hitRoot==window && s.owned, "Consumer window/foreground/hit ownership differs");
            Require(Rect(s.targetBounds) && Rect(s.windowBounds) && Rect(s.desktopBounds)
                && Contains(s.windowBounds,s.targetBounds) && Contains(s.desktopBounds,s.windowBounds), "Consumer target/window clipped or invalid");
            Require(s.point != null && s.point.Length==2 && s.point[0]==(int)Math.Floor(s.targetBounds[0]+s.targetBounds[2]/2)
                && s.point[1]==(int)Math.Floor(s.targetBounds[1]+s.targetBounds[3]/2), "Consumer point differs from observed center");
        }
        public static void Stable(ConsumerInputSnapshot a, ConsumerInputSnapshot b, string name, string role, string title, int pid, long main, long window)
        {
            Validate(a,name,role,title,pid,main,window); Validate(b,name,role,title,pid,main,window);
            Require(a.identity==b.identity && Same(a.targetBounds,b.targetBounds) && Same(a.windowBounds,b.windowBounds)
                && Same(a.desktopBounds,b.desktopBounds), "Consumer target identity/geometry changed before input");
        }
        public static void Keyboard(ConsumerKeyboardSnapshot s,int pid,long main,long window)
        {
            Require(s!=null && pid>0 && main!=0 && window!=0 && s.pid==pid && s.foregroundPid==pid && s.nativeFocusPid==pid && s.uiaFocusPid==pid
                && s.main==main && s.window==window && s.foreground==window && s.active==window && s.nativeFocusRoot==window && s.nativeFocus!=0
                && s.owned && s.enabled && !s.offscreen && s.expectedTargetContainsFocus && !String.IsNullOrEmpty(s.identity) && !String.IsNullOrEmpty(s.title),
                "Consumer keyboard ownership/focus differs");
            Require(Rect(s.windowBounds) && Rect(s.desktopBounds) && Contains(s.desktopBounds,s.windowBounds), "Consumer keyboard window clipped/invalid");
        }
        public static void KeyboardStable(ConsumerKeyboardSnapshot a,ConsumerKeyboardSnapshot b,int pid,long main,long window)
        {
            Keyboard(a,pid,main,window);Keyboard(b,pid,main,window);
            Require(a.identity==b.identity && a.nativeFocus==b.nativeFocus && a.title==b.title
                && Same(a.windowBounds,b.windowBounds) && Same(a.desktopBounds,b.desktopBounds), "Consumer keyboard focus/geometry changed before input");
        }
    }
}
