// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
using System;
using System.Collections.Generic;
namespace WaveQuayQualification
{
    public sealed class ConsumerTreeRoot
    {
        public int pid,nativePid;
        public long window;
        public bool owned,enabled,offscreen;
        public string name,role,className,identity;
    }
    public static class ConsumerTreeRead
    {
        public static void RootStable(ConsumerTreeRoot retained,ConsumerTreeRoot current)
        {
            if(retained==null || current==null || retained.pid<=0 || retained.nativePid!=retained.pid || retained.window==0
                || !retained.owned || retained.role!="ControlType.Window" || String.IsNullOrEmpty(retained.identity)
                || String.IsNullOrEmpty(retained.name) || String.IsNullOrEmpty(retained.className)
                || current.pid!=retained.pid || current.nativePid!=retained.nativePid || current.window!=retained.window || !current.owned
                || current.role!=retained.role || current.name!=retained.name || current.className!=retained.className
                || current.identity!=retained.identity || current.enabled!=retained.enabled || current.offscreen!=retained.offscreen)
                throw new InvalidOperationException("Retained consumer observation root identity/properties changed");
        }
        // This boundary contains read-only observation delegates. Input methods
        // never enter it. A failed traversal has no returned partial list.
        public static T Poll<T>(Func<List<T>> read,Action check,Func<long> elapsed,
            Action pause,Func<Exception,bool> unavailable,Action<Exception> failed,string label)
        {
            Exception first=null;
            while(elapsed()<10000)
            {
                check();List<T> complete=null;
                try{complete=read();}
                catch(Exception error)
                {
                    if(!unavailable(error))throw;
                    if(first==null)first=error;
                    failed(error);
                }
                if(complete!=null)
                {
                    if(complete.Count>1)throw new InvalidOperationException("Ambiguous consumer control: "+label);
                    if(complete.Count==1 && elapsed()<10000)return complete[0];
                }
                if(elapsed()<10000)pause();
            }
            throw new TimeoutException("Exact consumer control absent or incomplete within original 10 second budget: "+label,first);
        }
    }
}
