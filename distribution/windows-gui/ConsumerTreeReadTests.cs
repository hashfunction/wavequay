// SPDX-License-Identifier: GPL-3.0-only
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using WaveQuayQualification;
namespace WaveQuayQualificationTests
{
    public static class ConsumerTreeReadTests
    {
        private static void Need(bool value,string message){if(!value)throw new Exception(message);}
        private static COMException Failure(){return new COMException("observed UIA GetFirstChild E_FAIL",unchecked((int)0x80004005));}
        private static bool Unavailable(Exception error){return error is COMException && ((COMException)error).ErrorCode==unchecked((int)0x80004005);}
        private static ConsumerTreeRoot Root(){return new ConsumerTreeRoot{pid=2784,nativePid=2784,window=655790,owned=true,
            name="Export audio",role="ControlType.Window",className="fixture-QML-class",identity="retained-runtime-id",enabled=true,offscreen=false};}
        public static void RunProviderClassifier(Func<Exception,bool> unavailable,Exception elementNotAvailable)
        {
            Need(elementNotAvailable.GetType().FullName=="System.Windows.Automation.ElementNotAvailableException","Real Windows UIA exception required");
            Need(unavailable(elementNotAvailable)&&unavailable(Failure()),"Actual unavailable provider errors not recognized");
            Need(!unavailable(new COMException("access denied",unchecked((int)0x80070005)))
                && !unavailable(new COMException("other",unchecked((int)0x80040200)))
                && !unavailable(new InvalidOperationException("foreign identity")),"Other failure incorrectly retried");
            Console.WriteLine("PASS: actual Windows UIA ElementNotAvailable and exact COM E_FAIL classifier; other COM/identity errors remain fatal.");
        }
        public static void Run()
        {
            ConsumerTreeRead.RootStable(Root(),Root());
            foreach(var mutate in new Action<ConsumerTreeRoot>[] {r=>r.pid=99,r=>r.nativePid=99,r=>r.window=1,r=>r.owned=false,
                r=>r.name="foreign",r=>r.role="ControlType.Pane",r=>r.className="replaced",r=>r.identity="new",r=>r.enabled=false,r=>r.offscreen=true})
            {
                var changed=Root();mutate(changed);bool rejected=false;
                try{ConsumerTreeRead.RootStable(Root(),changed);}catch(InvalidOperationException){rejected=true;}
                Need(rejected,"Retained root mutation accepted");
            }
            int reads=0,checks=0,failures=0;long now=0;
            var result=ConsumerTreeRead.Poll<string>(()=>{
                reads++;var partial=new List<string>{"matching node seen before failed child"};
                if(reads==1)throw Failure();return new List<string>{"complete unique target"};},
                ()=>checks++,()=>now,()=>now+=150,Unavailable,error=>failures++,"fixture target");
            Need(result=="complete unique target" && reads==2 && checks==2 && failures==1 && now==150,"Incomplete list accepted or no complete requery");
            reads=0;now=0;var original=Failure();Exception last=null;
            try{ConsumerTreeRead.Poll<string>(()=>{reads++;throw original;},()=>{},()=>now,()=>now+=150,Unavailable,error=>last=error,"persistent");throw new Exception("Persistent failure accepted");}
            catch(TimeoutException error){Need(Object.ReferenceEquals(error.InnerException,original)&&Object.ReferenceEquals(last,original)&&reads==67&&now==10050,"Original provider failure/budget lost");}
            reads=0;now=0;
            try{ConsumerTreeRead.Poll<string>(()=>{reads++;if(reads%2==1)throw Failure();return new List<string>();},()=>{},()=>now,()=>now+=150,Unavailable,error=>{},"alternating");throw new Exception("No match accepted");}
            catch(TimeoutException){Need(reads==67&&now==10050,"Read failure reset the one existing budget");}
            foreach(var error in new Exception[]{new COMException("access denied",unchecked((int)0x80070005)),new InvalidOperationException("foreign identity"),new Exception("unexpected")})
            {
                now=0;bool fatal=false;try{ConsumerTreeRead.Poll<string>(()=>{throw error;},()=>{},()=>now,()=>now+=150,Unavailable,e=>{},"unexpected");}catch(Exception actual){fatal=Object.ReferenceEquals(error,actual);}
                Need(fatal&&now==0,"Unexpected/ownership error retried");
            }
            now=0;reads=0;bool ownerFatal=false;
            try{ConsumerTreeRead.Poll<string>(()=>{reads++;return new List<string>{"foreign"};},()=>{throw new InvalidOperationException("retained root changed");},()=>now,()=>now+=150,Unavailable,e=>{},"owned");}
            catch(InvalidOperationException){ownerFatal=true;}Need(ownerFatal&&reads==0&&now==0,"Observation before retained-owner check");
            now=0;bool duplicateFatal=false;try{ConsumerTreeRead.Poll<string>(()=>new List<string>{"one","two"},()=>{},()=>now,()=>now+=150,Unavailable,e=>{},"duplicate");}
            catch(InvalidOperationException){duplicateFatal=true;}Need(duplicateFatal&&now==0,"Ambiguous exact match retried/accepted");
            now=0;bool expiredFatal=false;try{ConsumerTreeRead.Poll<string>(()=>{now=10000;return new List<string>{"too late"};},()=>{},()=>now,()=>now+=150,Unavailable,e=>{},"late");}
            catch(TimeoutException){expiredFatal=true;}Need(expiredFatal,"Read completed after original deadline was accepted");
            Console.WriteLine("PASS: production complete-tree polling boundary, discarded partial reads, exact single budget, original failure retention, 10 retained-root and 8 fatal/timeout mutations; Windows UIA remains pending.");
        }
    }
}
