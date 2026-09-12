// SPDX-License-Identifier: GPL-3.0-only
// Managed fixtures for the actual read-only query policy, never product evidence.
using System;
using System.Collections.Generic;
using WaveQuayQualification;

namespace WaveQuayQualificationTests
{
    public static class ConsumerTextReadbackTests
    {
        private static void Require(bool value,string message) { if(!value)throw new Exception(message); }
        private static ConsumerTextResult Value(string text) { return new ConsumerTextResult{Completed=true,Text=text,Copied=(ulong)text.Length}; }
        private static void Reject(Action action,string name)
        { bool rejected=false;try{action();}catch(InvalidOperationException){rejected=true;}catch(TimeoutException){rejected=true;}Require(rejected,"Accepted unsafe readback: "+name); }
        public static string Run()
        {
            const string expected=@"C:\fixture\résumé,原稿.wav";
            int queries=0,guards=0,waits=0;long time=0;var order=new List<string>();
            var result=ConsumerTextReadback.Confirm(123,expected,r=>{
                Require(r.Window==123 && r.Message==13 && r.Capacity==4096 && r.Flags==0x23 && r.TimeoutMs==500,"Incorrect WM_GETTEXT native packet");
                queries++;order.Add("query");return Value(queries==1?"":queries==2?@"C:\fixture\résumé,原":expected);
            },()=>{guards++;order.Add("guard");},()=>time,ms=>{waits++;time+=ms;order.Add("wait");},r=>order.Add("observed"));
            Require(result.Attempts==3 && result.ElapsedMs==100 && queries==3 && guards==6 && waits==2,"Queued input did not converge by read-only polling");
            Require(String.Join(",",order)=="guard,query,guard,observed,wait,guard,query,guard,observed,wait,guard,query,guard,observed","Query/ownership order differs");

            queries=guards=waits=0;time=0;
            Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>{queries++;return new ConsumerTextResult{Completed=false,Error=1460,Text="",Copied=0};},
                ()=>guards++,()=>time,ms=>waits++,r=>{}),"native timeout");
            Require(queries==1 && guards==2 && waits==0,"Timed-out native query was retried or lost post-ownership guard");

            foreach(var invalid in new[]{new ConsumerTextResult{Completed=true,Text=new string('x',4095),Copied=4095},
                new ConsumerTextResult{Completed=true,Text=expected,Copied=(ulong)expected.Length+1},
                new ConsumerTextResult{Completed=true,Text=null,Copied=0}})
                Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>invalid,()=>{},()=>0,ms=>{},r=>{}),"truncated/inconsistent/null native result");

            foreach(long window in new long[]{0,65535})
                Reject(()=>ConsumerTextReadback.Confirm(window,expected,r=>{throw new Exception("Unowned query sent");},()=>{},()=>0,ms=>{},r=>{}),"invalid/broadcast HWND");
            Reject(()=>ConsumerTextReadback.Confirm(123,new string('x',4095),r=>Value(""),()=>{},()=>0,ms=>{},r=>{}),"overlong expected filename");

            queries=guards=0;
            Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>{queries++;return Value(expected);},()=>{guards++;throw new InvalidOperationException("owner changed");},
                ()=>0,ms=>{},r=>{}),"ownership before query");
            Require(queries==0 && guards==1,"Query happened after rejected ownership");
            queries=guards=0;
            Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>{queries++;return Value(expected);},()=>{if(++guards==2)throw new InvalidOperationException("focus changed");},
                ()=>0,ms=>{},r=>{}),"ownership after query");
            Require(queries==1 && guards==2,"Changed post-query owner was accepted");

            queries=0;time=0;
            Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>{queries++;time+=r.TimeoutMs;return Value("old name");},()=>{},()=>time,ms=>time+=ms,r=>{}),"convergence deadline");
            Require(time<=5000 && queries<=10,"Native/read-only convergence exceeded its total deadline");
            queries=0;
            Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>{queries++;return Value("old name");},()=>{},()=>0,ms=>{},r=>{}),"nonadvancing clock");
            Require(queries==101,"Readback polling is not independently bounded");
            time=0;
            Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>{time=5001;return Value(expected);},()=>{},()=>time,ms=>{},r=>{}),"late success");
            queries=guards=0;time=0;
            result=ConsumerTextReadback.ConfirmValue(expected,()=>{queries++;return queries==1?"":expected;},()=>guards++,()=>time,ms=>time+=ms,r=>{});
            Require(result.Attempts==2 && queries==2 && guards==4,"UIA value did not use guarded read-only convergence");
            guards=0;
            Reject(()=>ConsumerTextReadback.ConfirmValue(expected,()=>{throw new InvalidOperationException("UIA provider failed");},()=>guards++,()=>0,ms=>{},r=>{}),"UIA provider failure");
            Require(guards==2,"Post-read owner check omitted on UIA getter exception");
            queries=0;time=0;
            Reject(()=>ConsumerTextReadback.Confirm(123,expected,r=>{queries++;return Value(expected);},()=>time=5000,()=>time,ms=>{},r=>{}),"ownership consumed deadline");
            Require(queries==0,"Query started after the deadline expired in its ownership check");
            return "PASS: WM_GETTEXT packet, native/UIA queued-input convergence and timeout/ownership/result/deadline cases; no input replay API.";
        }
    }
}
