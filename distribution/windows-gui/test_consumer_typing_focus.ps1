# SPDX-License-Identifier: GPL-3.0-only
# Execute production Type/TypingFocus with real input guards; native leaves only
# are replayed. Private namespaces keep the preloaded Windows UIA host intact.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$driver=Get-Content (Join-Path $PSScriptRoot 'ConsumerDriver.cs') -Raw
function Method([string]$Name,[switch]$Optional){
    $m=[regex]::Match($driver,'private (?:void|string) '+$Name+'\([^\n]+\)\s*\{')
    if(-not $m.Success){if($Optional){return ''};throw "Production method missing: $Name"}
    $end=$m.Index+$m.Length;$depth=1
    while($depth -gt 0 -and $end -lt $driver.Length){if($driver[$end] -eq '{'){$depth++};if($driver[$end] -eq '}'){$depth--};$end++}
    if($depth -ne 0){throw 'Unbalanced producer method'}
    $driver.Substring($m.Index,$end-$m.Index)
}
$original=Get-Content (Join-Path $PSScriptRoot 'fixtures/filename-focus-34727941322.json') -Raw | ConvertFrom-Json
if($original.last_keys.before.pid -ne 2800 -or $original.last_keys.before.main -ne 262212 -or $original.last_keys.before.window -ne 655770 -or
   $original.last_keys.before.identity -cne '42,655770,4,-2147482860' -or $original.failure_focus.uia.identity -cne '42,655770,4,-2147482864' -or
   $original.failure_focus.uia.name -cne 'Format: WAV (Microsoft)'){throw 'Production replay no longer matches retained original focus identities'}
$policy=(Get-Content (Join-Path $PSScriptRoot 'ConsumerInput.cs') -Raw).Replace('namespace WaveQuayQualification','namespace WaveTypingPolicy')
$methods=(Method Type)+(Method TypingFocus -Optional)
Add-Type -TypeDefinition ($policy + @'
namespace WaveTypingReplay {
 using System;using System.Collections.Generic;using System.Runtime.InteropServices;using WaveTypingPolicy;
 enum ControlType {Edit,ComboBox}
 sealed class State {public int ProcessId=2800,NativeWindowHandle;public string ClassName="muse::accessibility::AccessibleObject",Name="File name: Dawn-thread";public ControlType ControlType=ControlType.Edit;public bool IsEnabled=true,IsOffscreen=false;}
 sealed class AutomationElement {public State Current=new State();public string Id="42,655770,4,-2147482860";}
 sealed class Process {public int Id=2800;}
 sealed class Stopwatch {public static long Now;private long start=Now;public static Stopwatch StartNew(){return new Stopwatch();}public long ElapsedMilliseconds{get{return Now-start;}}}
 static class Thread {public static bool Frozen;public static void Sleep(int ms){if(!Frozen)Stopwatch.Now+=ms;}}
 [StructLayout(LayoutKind.Sequential)]struct ConsumerKey {public ushort Key,Scan;public uint Flags,Time;public UIntPtr Extra;}
 [StructLayout(LayoutKind.Explicit,Size=32)]struct ConsumerUnion {[FieldOffset(0)]public ConsumerKey Key;}
 [StructLayout(LayoutKind.Sequential)]struct ConsumerNativeInput {public uint Type;public ConsumerUnion Value;}
 public sealed class Replay {
  readonly Process process=new Process();readonly IntPtr main=new IntPtr(262212);string action="configure-wav-recipe";
  readonly Dictionary<string,object> report=new Dictionary<string,object>();readonly List<Dictionary<string,object>> inputs=new List<Dictionary<string,object>>();
  readonly List<Dictionary<string,object>> typingFocusWaits=new List<Dictionary<string,object>>();
  ConsumerKeyboardSnapshot lastKeyboard;AutomationElement target,root;string fault;long ready;public string Sent="";public int SelectAll,FocusReads,Sends;
  static Dictionary<string,object> D(params object[] args){var d=new Dictionary<string,object>();for(int i=0;i<args.Length;i+=2)d[(string)args[i]]=args[i+1];return d;}
  static void Require(bool pass,string error){if(!pass)throw new InvalidOperationException(error);}
  void Check(){Require(Stopwatch.Now<420000,"original workflow deadline");}void Write(){}
  string Identity(AutomationElement e){return e.Id;}
  string Focus(AutomationElement r,AutomationElement e){
   Check();FocusReads++;bool pending=Sent.Length>0 && (fault=="never" || Stopwatch.Now<ready);
   lastKeyboard=new ConsumerKeyboardSnapshot{pid=2800,foregroundPid=2800,nativeFocusPid=2800,uiaFocusPid=2800,main=main.ToInt64(),window=655770,foreground=655770,active=655770,nativeFocus=655770,nativeFocusRoot=655770,owned=true,enabled=true,expectedTargetContainsFocus=!pending,identity=pending?"42,655770,4,-2147482864":target.Id,title="Export audio",windowBounds=new double[]{646,177,652,747},desktopBounds=new double[]{0,0,1920,1080}};
   if(Sent.Length>0 && fault=="foreign")lastKeyboard.foregroundPid=99;
   if(Sent.Length>0 && fault=="native")lastKeyboard.nativeFocus=999;
   if(Sent.Length>0 && fault=="identity" && !pending)lastKeyboard.identity="unobserved-descendant";
   if(Sent.Length>0 && fault=="late" && !pending)Stopwatch.Now+=1001;
   ConsumerInput.Keyboard(lastKeyboard,2800,main.ToInt64(),655770);
   return lastKeyboard.identity+"|"+lastKeyboard.nativeFocus+"|Export audio";
  }
  void Keys(AutomationElement r,AutomationElement e,params ushort[] keys){Require(keys.Length==2&&keys[0]==17&&keys[1]==65,"Unexpected chord");Focus(r,e);SelectAll++;}
  uint ConsumerSendInput(uint count,ConsumerNativeInput[] values,int size){
   Require(count==2&&values.Length==2&&values[0].Value.Key.Scan==values[1].Value.Key.Scan&&values[0].Value.Key.Flags==4&&values[1].Value.Key.Flags==6,"Unexpected or replayed native packet");
   Sends++;Sent+=(char)values[0].Value.Key.Scan;
   if(fault!="stable")ready=Stopwatch.Now+80;
   if(fault=="target")target.Id="changed-runtime-id";
   if(fault=="class")target.Current.ClassName="foreign edit provider";
   if(fault=="workflow")Stopwatch.Now=420000;
   return 2;
  }
  public void Run(string text,string failure,bool native=false){fault=failure;Stopwatch.Now=0;Thread.Frozen=fault=="frozen";root=new AutomationElement{Current=new State{NativeWindowHandle=655770,Name="Export audio"}};target=new AutomationElement();if(native){target.Current.ClassName="Edit";target.Current.NativeWindowHandle=123;}Type(root,target,text);}
  public int WaitCount{get{return typingFocusWaits.Count;}}
'@ + $methods + @'
 }
 public static class Tests {
  static void Require(bool pass,string error){if(!pass)throw new Exception(error);}
  public static string Run(){
   foreach(string text in new[]{"reversed","reopened","Dawn thread stereo"}){
    var r=new Replay();r.Run(text,"revoice");
    Require(r.Sent==text&&r.Sends==text.Length&&r.SelectAll==1&&r.WaitCount==text.Length-1,"Production typing replayed input or skipped restored focus");
   }
   var stable=new Replay();stable.Run("native path","stable",true);Require(stable.Sent=="native path"&&stable.WaitCount==0,"Native picker typing behavior changed");
   foreach(string fault in new[]{"never","foreign","native","target","class","identity","late","workflow","frozen"}){
    var r=new Replay();bool failed=false;try{r.Run("reversed",fault);}catch(InvalidOperationException){failed=true;}catch(TimeoutException){failed=true;}
    Require(failed&&r.Sent=="r"&&r.Sends==1&&r.SelectAll==1,"Unrestored/foreign/stale/late focus accepted or input replayed: "+fault);
    Require(r.FocusReads<48,"Focus polling exceeded independent read bound");
   }
   var nativeLost=new Replay();bool refused=false;try{nativeLost.Run("native path","revoice",true);}catch(InvalidOperationException){refused=true;}
   Require(refused&&nativeLost.Sent=="n"&&nativeLost.WaitCount==0,"Muse-only convergence leaked into native picker");
   return "PASS actual Type/TypingFocus: filename/reentry/recipe revoicing, one-shot input, stable native path and ten focus/deadline refusals.";
  }
 }
}
'@)
[WaveTypingReplay.Tests]::Run()
