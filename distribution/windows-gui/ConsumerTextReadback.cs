// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
// Read-only convergence after queued SendInput. This policy has no input API.
using System;

namespace WaveQuayQualification
{
    public sealed class ConsumerTextRequest
    {
        public readonly long Window;
        public readonly uint Message=0x000D, Capacity=4096, Flags=0x0023, TimeoutMs;
        public ConsumerTextRequest(long window,uint timeout) { Window=window;TimeoutMs=timeout; }
    }
    public sealed class ConsumerTextResult
    {
        public bool Completed;
        public string Text;
        public ulong Copied;
        public int Error;
    }
    public sealed class ConsumerTextConfirmation
    { public int Attempts; public long ElapsedMs; }
    public static class ConsumerTextReadback
    {
        private static void Require(bool value,string message)
        { if(!value)throw new InvalidOperationException(message); }
        private static ConsumerTextConfirmation Converge(string expected,Func<uint,ConsumerTextResult> read,
            Action guard,Func<long> clock,Action<int> wait,Action<ConsumerTextResult> observe)
        {
            Require(expected!=null && expected.Length>0 && expected.Length<4095 && expected.IndexOf('\0')<0,"Expected control text exceeds the bounded buffer");
            long start=clock();
            for(int attempt=1;attempt<=101;attempt++)
            {
                long remaining=5000-(clock()-start);
                if(remaining<=0)throw new TimeoutException("Queued control text did not converge within five seconds");
                guard();ConsumerTextResult result;
                remaining=5000-(clock()-start);
                if(remaining<=0)throw new TimeoutException("Ownership observation exhausted the control text deadline before querying");
                try { result=read((uint)Math.Min(500,remaining)); }
                finally { guard(); }
                Require(result!=null,"Control text query returned no result");
                observe(result);
                Require(result.Completed,"Bounded control text query failed/timed out; error="+result.Error);
                Require(result.Text!=null && result.Copied<4095 && result.Copied==(ulong)result.Text.Length,"Control text was truncated or its copied count differs");
                long elapsed=clock()-start;
                if(elapsed<0 || elapsed>5000)throw new TimeoutException("Control text query exceeded its convergence deadline");
                if(result.Text==expected)return new ConsumerTextConfirmation{Attempts=attempt,ElapsedMs=elapsed};
                if(elapsed==5000)throw new TimeoutException("Queued control text did not converge within five seconds");
                wait((int)Math.Min(50,5000-elapsed));
            }
            throw new TimeoutException("Read-only control text convergence exceeded 101 observations");
        }
        public static ConsumerTextConfirmation Confirm(long window,string expected,Func<ConsumerTextRequest,ConsumerTextResult> query,
            Action guard,Func<long> clock,Action<int> wait,Action<ConsumerTextResult> observe)
        {
            Require(window!=0 && window!=65535,"No exact native control HWND; broadcast queries are forbidden");
            return Converge(expected,timeout=>query(new ConsumerTextRequest(window,timeout)),guard,clock,wait,observe);
        }
        public static ConsumerTextConfirmation ConfirmValue(string expected,Func<string> read,Action guard,Func<long> clock,
            Action<int> wait,Action<ConsumerTextResult> observe)
        {
            return Converge(expected,timeout=>{string value=read();return new ConsumerTextResult{Completed=true,Text=value,Copied=value==null?0:(ulong)value.Length};},
                guard,clock,wait,observe);
        }
    }
}
