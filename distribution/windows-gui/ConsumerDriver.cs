// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
// Ordinary UI only. Compiled into the .NET Framework observer, never the app.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Automation;
using System.Windows.Forms;

namespace WaveQuayQualification
{
    public static partial class GuiProbe
    {
        public static bool TreeReadUnavailable(Exception error)
        { return error is ElementNotAvailableException || (error is COMException && ((COMException)error).ErrorCode==unchecked((int)0x80004005)); }
        [StructLayout(LayoutKind.Sequential)] private struct ConsumerKey { public ushort Key, Scan; public uint Flags, Time; public UIntPtr Extra; }
        [StructLayout(LayoutKind.Explicit)] private struct ConsumerUnion
        { [FieldOffset(0)] public ConsumerKey Key; [FieldOffset(0)] public MouseInput Mouse; }
        [StructLayout(LayoutKind.Sequential)] private struct ConsumerNativeInput { public uint Type; public ConsumerUnion Value; }
        [StructLayout(LayoutKind.Sequential)] private struct ConsumerThreadInfo
        { public uint Size, Flags; public IntPtr Active, Focus, Capture, MenuOwner, MoveSize, Caret; public Rect CaretRect; }
        [DllImport("user32.dll", EntryPoint="SendInput", SetLastError=true)] private static extern uint ConsumerSendInput(uint count, ConsumerNativeInput[] inputs, int size);
        [DllImport("user32.dll")] private static extern bool GetGUIThreadInfo(uint thread, ref ConsumerThreadInfo info);
        [DllImport("user32.dll")] private static extern IntPtr GetWindow(IntPtr window, uint command);
        [DllImport("user32.dll")] private static extern IntPtr GetParent(IntPtr window);
        [DllImport("user32.dll")] private static extern int GetDlgCtrlID(IntPtr window);
        [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetClassName(IntPtr window, StringBuilder value, int size);
        [DllImport("user32.dll", EntryPoint="SendMessageTimeoutW", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern IntPtr ConsumerSendMessageTimeout(IntPtr window,uint message,UIntPtr capacity,[Out] StringBuilder value,uint flags,uint timeout,out UIntPtr copied);
        [DllImport("kernel32.dll",EntryPoint="SetLastError")] private static extern void ConsumerClearLastError(uint error);
        [DllImport("user32.dll", EntryPoint="GetWindowLongW")] private static extern int ConsumerWindowStyle(IntPtr window, int index);
        [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
        [DllImport("user32.dll")] private static extern bool IsWindowEnabled(IntPtr window);
        private delegate bool ConsumerEnumProc(IntPtr window, IntPtr data);
        [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr parent, ConsumerEnumProc callback, IntPtr data);

        private static string NativeClass(IntPtr window) { var b=new StringBuilder(256); GetClassName(window,b,b.Capacity); return b.ToString(); }
        private static int NativePid(IntPtr window) { uint pid; GetWindowThreadProcessId(window,out pid); return (int)pid; }
        private static string Identity(AutomationElement element) { return String.Join(",",element.GetRuntimeId()); }
        private static double[] Bounds(AutomationElement element)
        { var b=element.Current.BoundingRectangle; return new[]{b.X,b.Y,b.Width,b.Height}; }
        private static double[] NativeBounds(IntPtr window)
        { Rect b; if(!GetWindowRect(window,out b))throw new InvalidOperationException("Cannot read native bounds");return new double[]{b.Left,b.Top,b.Right-b.Left,b.Bottom-b.Top}; }

        private sealed class ConsumerSession
        {
            private readonly Process process;
            private readonly IntPtr main;
            private readonly string directory, fixture, appTitle;
            private readonly string fixtureMarkerHash;
            private readonly Action captureModules;
            private readonly Stopwatch clock=Stopwatch.StartNew();
            private readonly Dictionary<string,object> report;
            private readonly List<Dictionary<string,object>> observations=new List<Dictionary<string,object>>();
            private readonly List<Dictionary<string,object>> inputs=new List<Dictionary<string,object>>();
            private readonly List<Dictionary<string,object>> textReadbacks=new List<Dictionary<string,object>>();
            private int transient;
            private ConsumerKeyboardSnapshot lastKeyboard;
            private AutomationElement queryNode;
            private readonly List<AutomationElement> queryParents=new List<AutomationElement>();
            private string queryStep;
            private int queryDepth,queryCount,treeReadProviderFailures;
            private string action="begin";
            public ConsumerSession(Process process, AutomationElement mainWindow, string directory, string title, string source, Action captureModules)
            {
                this.process=process;main=new IntPtr(mainWindow.Current.NativeWindowHandle);this.directory=directory;
                fixture=Path.Combine(directory,"consumer-fixture");appTitle=title;
                NoReparsePath(fixture);fixtureMarkerHash=Hash(Path.Combine(fixture,".owner.json"));
                this.captureModules=captureModules;
                report=D("schemaVersion",1,"sourceCommit",source,"processId",process.Id,"mainWindowHandle",main.ToInt64(),
                    "fixture",fixture,"observations",observations,"inputs",inputs,"textReadbacks",textReadbacks,"errors",new List<string>(),"completed",false,
                    "normalCloseExitCode",null,"hardwareRecordingOrPlaybackTested",false);
            }
            private void Require(bool condition,string reason) { if(!condition)throw new InvalidOperationException(reason); }
            private void Check()
            { Alive(process);Require(clock.ElapsedMilliseconds<420000,"Consumer file workflow exceeded separate 420 second budget"); }
            private void Write() { report["currentAction"]=action;report["elapsedMs"]=clock.ElapsedMilliseconds;Save(Path.Combine(directory,"consumer-workflow.json"),report); }
            private bool Owned(IntPtr window)
            {
                for(int depth=0;window!=IntPtr.Zero && depth<12;depth++)
                { if(NativePid(window)!=process.Id)return false;if(window==main)return true;window=GetWindow(window,4); }
                return false;
            }
            private AutomationElement Main()
            {
                Check();var root=AutomationElement.FromHandle(main);var title=root.Current.Name;
                Require(root.Current.ProcessId==process.Id && NativePid(main)==process.Id &&
                    (title==appTitle || title=="Dawn-thread * - "+appTitle || title=="Dawn-thread  - "+appTitle
                    || title=="Untitled project * - "+appTitle || title=="Untitled project  - "+appTitle), "Retained editor title/PID differs from source-defined project titles");
                return root;
            }
            private List<AutomationElement> VisibleWindows()
            { Check();return Windows(process.Id,ref transient).FindAll(w=>!w.Current.IsOffscreen); }
            private AutomationElement Window(string title,bool native)
            {
                var wait=Stopwatch.StartNew();
                while(wait.ElapsedMilliseconds<15000)
                {
                    var found=VisibleWindows().FindAll(w=>w.Current.Name==title && Owned(new IntPtr(w.Current.NativeWindowHandle))
                        && (!native || w.Current.ClassName=="#32770"));
                    Require(found.Count<=1,"Duplicate exact owned dialog: "+title);
                    if(found.Count==1)return found[0];Thread.Sleep(150);
                }
                throw new TimeoutException("Exact owned dialog absent: "+title);
            }
            private void Enumerate(AutomationElement node,List<AutomationElement> nodes,int depth)
            {
                Require(depth<=40 && nodes.Count<3000,"Consumer UI tree exceeds bound");nodes.Add(node);queryParents.Add(node);
                var walker=TreeWalker.RawViewWalker;
                QueryStep(node,depth,nodes.Count,"GetFirstChild");var child=walker.GetFirstChild(node);
                while(child!=null)
                {
                    Enumerate(child,nodes,depth+1);
                    QueryStep(child,depth+1,nodes.Count,"GetNextSibling");child=walker.GetNextSibling(child);
                }
                queryParents.RemoveAt(queryParents.Count-1);
            }
            private void QueryStep(AutomationElement node,int depth,int count,string step)
            { queryNode=node;queryDepth=depth;queryCount=count;queryStep=step; }
            private List<AutomationElement> Match(AutomationElement root,string name,ControlType role,bool prefix)
            {
                queryParents.Clear();var nodes=new List<AutomationElement>();Enumerate(root,nodes,0);
                return nodes.FindAll(n=>{
                    QueryStep(n,0,nodes.Count,"ReadMatchProperties");
                    return n.Current.ProcessId==process.Id && n.Current.ControlType==role && n.Current.IsEnabled
                        && !n.Current.IsOffscreen && (prefix?n.Current.Name.StartsWith(name,StringComparison.Ordinal):n.Current.Name==name);
                });
            }
            private static string DiagnosticText(string value,int limit)
            { return value==null?null:(value.Length<=limit?value:value.Substring(0,limit)); }
            private Dictionary<string,object> QueryNodeFacts(AutomationElement node)
            {
                var facts=D();
                try
                {
                    var current=node.Current;
                    facts["pid"]=current.ProcessId;facts["name"]=DiagnosticText(current.Name,512);
                    facts["role"]=current.ControlType.ProgrammaticName;facts["className"]=DiagnosticText(current.ClassName,256);
                    facts["automationId"]=DiagnosticText(current.AutomationId,512);facts["identity"]=Identity(node);
                    facts["enabled"]=current.IsEnabled;facts["offscreen"]=current.IsOffscreen;facts["window"]=current.NativeWindowHandle;
                }
                catch(Exception error){facts["diagnosticError"]=DiagnosticText(error.ToString(),2000);}
                return facts;
            }
            private void RecordTreeReadFailure(Exception error,string name,string role,IntPtr window)
            {
                var parents=new List<object>();foreach(var node in queryParents)parents.Add(QueryNodeFacts(node));
                var failure=D("action",action,"targetName",name,"targetRole",role,"rootWindow",window.ToInt64(),
                    "elapsedMs",clock.ElapsedMilliseconds,"step",queryStep,"depth",queryDepth,"visitedNodes",queryCount,
                    "node",QueryNodeFacts(queryNode),"path",parents,"error",DiagnosticText(error.ToString(),4000));
                if(treeReadProviderFailures==0)report["firstTreeReadFailure"]=failure;
                report["lastTreeReadFailure"]=failure;report["treeReadProviderFailures"]=++treeReadProviderFailures;
            }
            private ConsumerTreeRoot TreeRoot(AutomationElement root)
            {
                var current=root.Current;var window=new IntPtr(current.NativeWindowHandle);
                return new ConsumerTreeRoot{pid=current.ProcessId,nativePid=NativePid(window),window=window.ToInt64(),owned=Owned(window),
                    role=current.ControlType.ProgrammaticName,name=current.Name,className=current.ClassName,identity=Identity(root),
                    enabled=current.IsEnabled,offscreen=current.IsOffscreen};
            }
            private AutomationElement Target(AutomationElement root,string name,ControlType role,bool prefix)
            {
                var wait=Stopwatch.StartNew();
                var retained=TreeRoot(root);var window=new IntPtr(retained.window);ConsumerTreeRead.RootStable(retained,retained);
                Func<AutomationElement> requery=()=>{
                    queryParents.Clear();QueryStep(root,0,0,"ReacquireRoot");
                    var fresh=AutomationElement.FromHandle(window);QueryStep(fresh,0,0,"ReadRootProperties");
                    ConsumerTreeRead.RootStable(retained,TreeRoot(fresh));
                    return fresh;
                };
                return ConsumerTreeRead.Poll<AutomationElement>(()=>{
                    var fresh=requery();var complete=Match(fresh,name,role,prefix);requery();return complete;
                },()=>{Check();Require(NativePid(window)==process.Id && Owned(window),"Retained consumer observation root is not owned");},
                ()=>wait.ElapsedMilliseconds,()=>Thread.Sleep(150),
                TreeReadUnavailable,
                error=>{
                    try{RecordTreeReadFailure(error,name,role.ProgrammaticName,window);}
                    catch(Exception diagnostic){report["treeReadDiagnosticError"]=DiagnosticText(diagnostic.ToString(),2000);}
                },name+" / "+role.ProgrammaticName);
            }
            private ConsumerInputSnapshot Snapshot(AutomationElement root,AutomationElement target,int matches)
            {
                var w=new IntPtr(root.Current.NativeWindowHandle);var b=Bounds(target);var point=new NativePoint{X=(int)Math.Floor(b[0]+b[2]/2),Y=(int)Math.Floor(b[1]+b[3]/2)};
                var hit=WindowFromPoint(point);var fg=GetForegroundWindow();var desktop=SystemInformation.VirtualScreen;
                return new ConsumerInputSnapshot{name=target.Current.Name,role=target.Current.ControlType.ProgrammaticName.Replace("ControlType.",""),
                    title=root.Current.Name,identity=Identity(target),pid=target.Current.ProcessId,nativePid=NativePid(w),foregroundPid=NativePid(fg),
                    hitPid=NativePid(hit),matches=matches,window=w.ToInt64(),foreground=fg.ToInt64(),hitRoot=GetAncestor(hit,2).ToInt64(),main=main.ToInt64(),
                    owned=Owned(w),enabled=target.Current.IsEnabled,offscreen=target.Current.IsOffscreen,targetBounds=b,windowBounds=NativeBounds(w),
                    desktopBounds=new double[]{desktop.X,desktop.Y,desktop.Width,desktop.Height},point=new[]{point.X,point.Y}};
            }
            private void ClickElement(AutomationElement root,AutomationElement target,Func<int> count)
            {
                Check();var w=new IntPtr(root.Current.NativeWindowHandle);
                Require(Owned(w),"Click root is not owned");SetForegroundWindow(w);
                var before=Snapshot(root,target,count());ConsumerInput.Validate(before,before.name,before.role,before.title,process.Id,main.ToInt64(),w.ToInt64());
                Require(SetCursorPos(before.point[0],before.point[1]),"Cannot position consumer pointer");
                var final=Snapshot(root,target,count());ConsumerInput.Stable(before,final,before.name,before.role,before.title,process.Id,main.ToInt64(),w.ToInt64());
                NativePoint cursor;Require(GetCursorPos(out cursor) && cursor.X==before.point[0] && cursor.Y==before.point[1],"Consumer pointer moved");
                var mouse=new[]{new Input{Type=0,Value=new InputUnion{Mouse=new MouseInput{Flags=2}}},new Input{Type=0,Value=new InputUnion{Mouse=new MouseInput{Flags=4}}}};
                uint sent=SendInput(2,mouse,Marshal.SizeOf(typeof(Input)));
                inputs.Add(D("action",action,"kind","click","before",before,"final",final,"sent",sent));Write();
                if(sent==1)
                {
                    try{var release=Snapshot(root,target,count());ConsumerInput.Stable(final,release,before.name,before.role,before.title,process.Id,main.ToInt64(),w.ToInt64());
                        report["partialMouseReleaseSent"]=SendInput(1,new[]{mouse[1]},Marshal.SizeOf(typeof(Input)));}
                    catch(Exception error){report["partialMouseReleaseRefused"]=error.Message;}
                }
                Require(sent==2,"Partial consumer mouse input");Thread.Sleep(180);
            }
            private AutomationElement Click(AutomationElement root,string name,ControlType role,bool prefix=false)
            { var target=Target(root,name,role,prefix);ClickElement(root,target,()=>Match(root,name,role,prefix).Count);return target; }
            private string Focus(AutomationElement root,AutomationElement expected)
            {
                Check();var w=new IntPtr(root.Current.NativeWindowHandle);uint nativePid;uint thread=GetWindowThreadProcessId(w,out nativePid);
                var info=new ConsumerThreadInfo{Size=(uint)Marshal.SizeOf(typeof(ConsumerThreadInfo))};
                Require(GetGUIThreadInfo(thread,ref info),"Cannot observe native keyboard focus");
                var focused=AutomationElement.FocusedElement;
                Require(focused!=null,"Consumer UIA focus missing");bool expectedFocus=expected==null;
                if(expected!=null)
                {
                    var cursor=focused;bool same=false;
                    for(int i=0;i<12 && cursor!=null;i++,cursor=TreeWalker.RawViewWalker.GetParent(cursor))
                    { if(Identity(cursor)==Identity(expected)){same=true;break;} }
                    expectedFocus=same;
                }
                var b=NativeBounds(w);var d=SystemInformation.VirtualScreen;
                var foreground=GetForegroundWindow();
                lastKeyboard=new ConsumerKeyboardSnapshot{pid=(int)nativePid,foregroundPid=NativePid(foreground),nativeFocusPid=NativePid(info.Focus),uiaFocusPid=focused.Current.ProcessId,
                    window=w.ToInt64(),main=main.ToInt64(),foreground=foreground.ToInt64(),active=info.Active.ToInt64(),nativeFocus=info.Focus.ToInt64(),nativeFocusRoot=GetAncestor(info.Focus,2).ToInt64(),
                    owned=Owned(w),enabled=focused.Current.IsEnabled,offscreen=focused.Current.IsOffscreen,expectedTargetContainsFocus=expectedFocus,identity=Identity(focused),title=root.Current.Name,
                    windowBounds=b,desktopBounds=new double[]{d.X,d.Y,d.Width,d.Height}};
                ConsumerInput.Keyboard(lastKeyboard,process.Id,main.ToInt64(),w.ToInt64());
                return Identity(focused)+"|"+info.Focus.ToInt64()+"|"+root.Current.Name;
            }
            private void Keys(AutomationElement root,AutomationElement expected,params ushort[] keys)
            {
                var before=Focus(root,expected);var beforeOwnership=lastKeyboard;var focused=AutomationElement.FocusedElement;
                string focusName=focused.Current.Name,focusRole=focused.Current.ControlType.ProgrammaticName;
                int window=root.Current.NativeWindowHandle;
                var sequence=new List<ConsumerNativeInput>();
                foreach(var key in keys)sequence.Add(new ConsumerNativeInput{Type=1,Value=new ConsumerUnion{Key=new ConsumerKey{Key=key}}});
                for(int i=keys.Length-1;i>=0;i--)sequence.Add(new ConsumerNativeInput{Type=1,Value=new ConsumerUnion{Key=new ConsumerKey{Key=keys[i],Flags=2}}});
                Require(Focus(root,expected)==before,"Consumer focus changed immediately before keys");
                ConsumerInput.KeyboardStable(beforeOwnership,lastKeyboard,process.Id,main.ToInt64(),window);
                uint sent=ConsumerSendInput((uint)sequence.Count,sequence.ToArray(),Marshal.SizeOf(typeof(ConsumerNativeInput)));
                inputs.Add(D("action",action,"kind","keys","keys",keys,"focusIdentity",before,"focusName",focusName,
                    "focusRole",focusRole,"window",window,"before",beforeOwnership,"final",lastKeyboard,"sent",sent,"expected",sequence.Count));Write();
                if(sent<sequence.Count)
                {
                    try{Require(Focus(root,expected)==before,"Partial key release lost original focus");var releases=new List<ConsumerNativeInput>();
                        for(int i=keys.Length-1;i>=0;i--)releases.Add(new ConsumerNativeInput{Type=1,Value=new ConsumerUnion{Key=new ConsumerKey{Key=keys[i],Flags=2}}});
                        report["partialKeyReleaseSent"]=ConsumerSendInput((uint)releases.Count,releases.ToArray(),Marshal.SizeOf(typeof(ConsumerNativeInput)));}
                    catch(Exception error){report["partialKeyReleaseRefused"]=error.Message;}
                }
                Require(sent==sequence.Count,"Partial consumer keyboard input");Thread.Sleep(150);
            }
            private readonly List<Dictionary<string,object>> typingFocusWaits=new List<Dictionary<string,object>>();
            private string TypingFocus(AutomationElement root,AutomationElement target,string targetIdentity,long nativeFocus,int characterIndex,bool museInput)
            {
                // Only the observed Muse edit provider has the source-defined 80ms
                // announcement focus. Native pickers keep their original immediate guard.
                if(!museInput)return Focus(root,target);
                var timer=Stopwatch.StartNew();Dictionary<string,object> record=null;
                var reads=new List<Dictionary<string,object>>();
                return ConsumerFocusConvergence.Read(()=>{
                    Check();Require(target.Current.ProcessId==process.Id && Identity(target)==targetIdentity
                        && target.Current.ClassName=="muse::accessibility::AccessibleObject" && target.Current.NativeWindowHandle==0
                        && target.Current.ControlType==ControlType.Edit && target.Current.IsEnabled && !target.Current.IsOffscreen,
                        "Retained Muse typing target changed");
                    string observed;
                    try { observed=Focus(root,target); }
                    catch(ConsumerTargetFocusPendingException)
                    {
                        Require(lastKeyboard.nativeFocus==nativeFocus,"Native typing focus changed during accessibility announcement");
                        throw;
                    }
                    Require(lastKeyboard.identity==targetIdentity && lastKeyboard.nativeFocus==nativeFocus,
                        "Restored typing focus differs from exact retained target");
                    return observed;
                },()=>timer.ElapsedMilliseconds,ms=>Thread.Sleep(ms),(attempt,elapsed,error)=>{
                    if(record==null && error==null)return;
                    if(record==null)
                    {
                        record=D("action",action,"targetIdentity",targetIdentity,"window",root.Current.NativeWindowHandle,
                            "nativeFocus",nativeFocus,"characterIndex",characterIndex,"firstError",error.ToString(),"reads",reads);
                        typingFocusWaits.Add(record);report["typingFocusWaits"]=typingFocusWaits;
                    }
                    reads.Add(D("attempt",attempt,"elapsedMs",elapsed,"exactTargetObserved",error==null,"withinDeadline",elapsed>=0 && elapsed<1000,"focus",lastKeyboard));
                });
            }
            private void Type(AutomationElement root,AutomationElement target,string text)
            {
                string targetIdentity=Identity(target);bool museInput=target.Current.ClassName=="muse::accessibility::AccessibleObject";
                Keys(root,target,0x11,0x41);
                long nativeFocus=lastKeyboard.nativeFocus;int characterIndex=0;
                foreach(char c in text)
                {
                    string before=TypingFocus(root,target,targetIdentity,nativeFocus,characterIndex,museInput);var beforeOwnership=lastKeyboard;var pair=new[]{new ConsumerNativeInput{Type=1,Value=new ConsumerUnion{Key=new ConsumerKey{Scan=c,Flags=4}}},
                        new ConsumerNativeInput{Type=1,Value=new ConsumerUnion{Key=new ConsumerKey{Scan=c,Flags=6}}}};
                    Require(TypingFocus(root,target,targetIdentity,nativeFocus,characterIndex,museInput)==before,"Consumer text target changed");
                    ConsumerInput.KeyboardStable(beforeOwnership,lastKeyboard,process.Id,main.ToInt64(),root.Current.NativeWindowHandle);
                    uint sent=ConsumerSendInput(2,pair,Marshal.SizeOf(typeof(ConsumerNativeInput)));
                    if(sent==1)
                    { try{Require(Focus(root,target)==before,"Partial Unicode release lost original focus");report["partialUnicodeReleaseSent"]=ConsumerSendInput(1,new[]{pair[1]},Marshal.SizeOf(typeof(ConsumerNativeInput)));}
                        catch(Exception error){report["partialUnicodeReleaseRefused"]=error.Message;} }
                    Require(sent==2,"Partial consumer Unicode input");characterIndex++;
                }
                // The next character normally waits out Muse's name-change
                // announcement. The final character has no next iteration, so
                // restore the same exact target before handing it to readback.
                TypingFocus(root,target,targetIdentity,nativeFocus,characterIndex,museInput);
                inputs.Add(D("action",action,"kind","unicode","characters",text.Length,"guardedCharacters",text.Length,"targetIdentity",Identity(target),"window",root.Current.NativeWindowHandle,"final",lastKeyboard));Write();
            }
            private string TextValue(AutomationElement target)
            {
                // Muse exposes actual editable content through TextInterface; Qt also
                // advertises ValuePattern, whose generic Value is empty for these edits.
                object value;if(target.TryGetCurrentPattern(TextPattern.Pattern,out value))return ((TextPattern)value).DocumentRange.GetText(4096).TrimEnd('\r','\n');
                if(target.TryGetCurrentPattern(ValuePattern.Pattern,out value))return ((ValuePattern)value).Current.Value;
                throw new InvalidOperationException("No independent UI text readback for target");
            }
            private void ConfirmText(AutomationElement root,AutomationElement target,string expected,IntPtr nativeEdit)
            {
                var window=new IntPtr(root.Current.NativeWindowHandle);string targetIdentity=Identity(target);
                ConsumerKeyboardSnapshot before=null;ConsumerTextRequest packet=null;var timer=Stopwatch.StartNew();
                var reads=new List<Dictionary<string,object>>();
                var receipt=D("action",action,"kind",nativeEdit==IntPtr.Zero?"uia-value-or-text":"owned-WM_GETTEXT","targetIdentity",targetIdentity,
                    "window",window.ToInt64(),"control",nativeEdit.ToInt64(),"expected",expected,"reads",reads,"confirmed",false);
                textReadbacks.Add(receipt);Write();
                Action guard=()=>{
                    Require(Owned(window) && root.Current.NativeWindowHandle==window.ToInt64() && target.Current.ProcessId==process.Id
                        && Identity(target)==targetIdentity && target.Current.ControlType==ControlType.Edit && target.Current.IsEnabled && !target.Current.IsOffscreen,
                        "Control text target identity/ownership changed");
                    if(nativeEdit!=IntPtr.Zero)Require(FileField(nativeEdit,window) && target.Current.NativeWindowHandle==nativeEdit.ToInt64(),"Native filename topology changed during readback");
                    Focus(root,target);
                    if(nativeEdit!=IntPtr.Zero)Require(lastKeyboard.nativeFocus==nativeEdit.ToInt64(),"Native filename edit no longer has exact keyboard focus");
                    if(before==null)before=lastKeyboard;
                    else ConsumerInput.KeyboardStable(before,lastKeyboard,process.Id,main.ToInt64(),window.ToInt64());
                };
                Action<ConsumerTextResult> observed=result=>{
                    reads.Add(D("packet",packet,"completed",result.Completed,"copied",result.Copied,"error",result.Error,"value",result.Text,
                        "matched",result.Text==expected,"before",before,"final",lastKeyboard,"elapsedMs",timer.ElapsedMilliseconds));
                    before=null;packet=null;Write();
                };
                ConsumerTextConfirmation confirmation;
                if(nativeEdit!=IntPtr.Zero)
                {
                    confirmation=ConsumerTextReadback.Confirm(nativeEdit.ToInt64(),expected,request=>{
                        packet=request;var buffer=new StringBuilder((int)request.Capacity);UIntPtr copied;
                        ConsumerClearLastError(0);
                        IntPtr status=ConsumerSendMessageTimeout(new IntPtr(request.Window),request.Message,new UIntPtr(request.Capacity),buffer,
                            request.Flags,request.TimeoutMs,out copied);
                        int error=status==IntPtr.Zero?Marshal.GetLastWin32Error():0;
                        return new ConsumerTextResult{Completed=status!=IntPtr.Zero,Copied=copied.ToUInt64(),Text=buffer.ToString(),Error=error};
                    },guard,()=>timer.ElapsedMilliseconds,ms=>Thread.Sleep(ms),observed);
                }
                else confirmation=ConsumerTextReadback.ConfirmValue(expected,()=>TextValue(target),guard,()=>timer.ElapsedMilliseconds,ms=>Thread.Sleep(ms),observed);
                receipt["confirmation"]=confirmation;receipt["confirmed"]=true;Write();
            }
            private void Field(AutomationElement root,string prefix,string text)
            {
                var field=Click(root,prefix,ControlType.Edit,true);Type(root,field,text);
                ConfirmText(root,field,text,IntPtr.Zero);Keys(root,field,0x09);
            }
            private bool FileField(IntPtr edit,IntPtr dialog)
            {
                if(NativePid(edit)!=process.Id || NativeClass(edit)!="Edit" || !IsWindowVisible(edit) || !IsWindowEnabled(edit)
                    || (ConsumerWindowStyle(edit,-16)&0x800)!=0)return false;
                return ConsumerInput.FilenameChain(FieldNodes(edit,dialog),process.Id,dialog.ToInt64(),edit.ToInt64());
            }
            private ConsumerFilenameNode[] FieldNodes(IntPtr edit,IntPtr dialog)
            {
                var nodes=new List<ConsumerFilenameNode>();var cursor=edit;
                for(int i=0;cursor!=IntPtr.Zero && cursor!=dialog && i<8;i++)
                {
                    var parent=GetParent(cursor);
                    nodes.Add(new ConsumerFilenameNode{window=cursor.ToInt64(),parent=parent.ToInt64(),pid=NativePid(cursor),id=GetDlgCtrlID(cursor),className=NativeClass(cursor)});
                    cursor=parent;
                }
                return nodes.ToArray();
            }
            private void Picker(string title,string path,bool save)
            {
                Require(Path.GetDirectoryName(Path.GetFullPath(path))==fixture && Hash(Path.Combine(fixture,".owner.json"))==fixtureMarkerHash,
                    "Native picker target escaped or lost its exclusive fixture owner");
                Require(save?!File.Exists(path):File.Exists(path),"Native picker input missing or save target already exists");
                var root=Window(title,true);var dialog=new IntPtr(root.Current.NativeWindowHandle);
                Require(NativeClass(dialog)=="#32770" && Owned(dialog),"Native picker ownership is unproved");
                var edits=new List<IntPtr>();var nativeEdits=new List<object>();bool truncated=false;
                EnumChildWindows(dialog,(child,data)=>{
                    if(NativeClass(child)=="Edit")
                    {
                        if(nativeEdits.Count>=64){truncated=true;return false;}
                        nativeEdits.Add(D("visible",IsWindowVisible(child),"enabled",IsWindowEnabled(child),"style",ConsumerWindowStyle(child,-16),"ancestry",FieldNodes(child,dialog)));
                    }
                    if(FileField(child,dialog))edits.Add(child);return true;
                },IntPtr.Zero);
                report["lastPicker"]=D("title",title,"handle",dialog.ToInt64(),"tree",Tree(root),"nativeEdits",nativeEdits,"truncated",truncated,"matchingFilenameFields",edits.Count);Write();
                Require(!truncated,"Native edit ancestry collection exceeded its bound");
                Require(edits.Count==1,"Exact native filename edit topology is unproved; inspect lastPicker");
                var edit=edits[0];var target=AutomationElement.FromHandle(edit);
                ClickElement(root,target,()=>FileField(edit,dialog)?1:0);
                Type(root,target,path);ConfirmText(root,target,path,edit);
                Keys(root,target,0x0D);
                var wait=Stopwatch.StartNew();while(wait.ElapsedMilliseconds<15000)
                {Check();if(!IsWindowVisible(dialog))return;Thread.Sleep(150);}
                throw new TimeoutException("Owned native picker did not close after exact filename confirmation: "+title);
            }
            private void Shortcut(params ushort[] keys)
            { var root=Main();SetForegroundWindow(main);Keys(root,null,keys); }
            private object MenuFocusFacts()
            {
                // Diagnostic observation only: a pointer action never asserts
                // that a non-activating popup owns keyboard/UIA focus.
                try {
                    uint pid;uint thread=GetWindowThreadProcessId(main,out pid);
                    var info=new ConsumerThreadInfo{Size=(uint)Marshal.SizeOf(typeof(ConsumerThreadInfo))};
                    bool available=GetGUIThreadInfo(thread,ref info);var focus=AutomationElement.FocusedElement;
                    return D("nativeAvailable",available,"foreground",GetForegroundWindow().ToInt64(),
                        "active",info.Active.ToInt64(),"nativeFocus",info.Focus.ToInt64(),
                        "uia",focus==null?null:D("pid",focus.Current.ProcessId,"name",focus.Current.Name,
                            "role",focus.Current.ControlType.ProgrammaticName,"identity",Identity(focus),
                            "enabled",focus.Current.IsEnabled,"offscreen",focus.Current.IsOffscreen));
                } catch(Exception error) { return D("diagnosticError",error.Message); }
            }
            private bool InNearestMenuWindow(AutomationElement root,AutomationElement target)
            {
                var cursor=target;
                for(int depth=0;cursor!=null && depth<12;depth++,cursor=TreeWalker.RawViewWalker.GetParent(cursor))
                {
                    // A submenu may also occur under its parent's raw tree.
                    // Bind the item only to its nearest native Window, never
                    // count it once for each ancestor popup.
                    if(cursor.Current.ControlType==ControlType.Window && cursor.Current.NativeWindowHandle!=0)
                        return Identity(cursor)==Identity(root);
                }
                return false;
            }
            private List<Tuple<AutomationElement,AutomationElement>> MenuMatches(string name)
            {
                var found=new List<Tuple<AutomationElement,AutomationElement>>();
                foreach(var window in VisibleWindows())
                {
                    var c=window.Current;
                    if(c.ControlType!=ControlType.Window || c.ClassName!="QQuickView"
                        || c.AutomationId!="muse::accessibility::AccessibleAppRootObject.MenuView_WindowView_QQuickView")continue;
                    foreach(var target in Match(window,name,ControlType.MenuItem,false))
                        if(InNearestMenuWindow(window,target))found.Add(Tuple.Create(window,target));
                }
                return found;
            }
            private ConsumerMenuSnapshot MenuSnapshot(AutomationElement root,AutomationElement target,string name)
            {
                var owners=new List<ConsumerMenuOwner>();var window=new IntPtr(root.Current.NativeWindowHandle);
                for(int depth=0;window!=IntPtr.Zero && depth<12;depth++)
                {
                    var owner=GetWindow(window,4);owners.Add(new ConsumerMenuOwner{window=window.ToInt64(),owner=owner.ToInt64(),pid=NativePid(window)});
                    if(window==main)break;window=owner;
                }
                bool contained=InNearestMenuWindow(root,target);
                return new ConsumerMenuSnapshot{target=Snapshot(root,target,MenuMatches(name).Count),mainPid=NativePid(main),
                    mainTitle=Main().Current.Name,mainBounds=NativeBounds(main),popupIdentity=Identity(root),
                    popupRole=root.Current.ControlType.ProgrammaticName.Replace("ControlType.",""),popupClass=root.Current.ClassName,
                    popupAutomationId=root.Current.AutomationId,popupEnabled=root.Current.IsEnabled && IsWindowEnabled(new IntPtr(root.Current.NativeWindowHandle)),
                    popupVisible=!root.Current.IsOffscreen && IsWindowVisible(new IntPtr(root.Current.NativeWindowHandle)),targetInPopup=contained,owners=owners.ToArray()};
            }
            private void PointAtMenu(string name,bool hover)
            {
                var wait=Stopwatch.StartNew();Tuple<AutomationElement,AutomationElement> choice=null;
                while(wait.ElapsedMilliseconds<10000)
                {
                    Check();var matches=MenuMatches(name);Require(matches.Count<=1,"Duplicate exact owned menu target: "+name);
                    if(matches.Count==1){choice=matches[0];break;}Thread.Sleep(150);
                }
                Require(choice!=null,"Exact visible effect menu target absent: "+name);
                var root=choice.Item1;var target=choice.Item2;var focusBefore=MenuFocusFacts();var before=MenuSnapshot(root,target,name);
                var attempt=D("name",name,"hoverOnly",hover,"before",before,"focusBefore",focusBefore);
                report["lastMenuPointerAttempt"]=attempt;
                ConsumerInput.Menu(before,name,process.Id,main.ToInt64());
                Require(SetCursorPos(before.target.point[0],before.target.point[1]),"Cannot position effect menu pointer");
                attempt["focusFinal"]=MenuFocusFacts();var final=MenuSnapshot(root,target,name);attempt["final"]=final;
                ConsumerInput.MenuStable(before,final,name,process.Id,main.ToInt64());
                NativePoint pointer;Require(GetCursorPos(out pointer) && pointer.X==before.target.point[0] && pointer.Y==before.target.point[1],"Effect menu pointer moved");
                if(hover)
                {
                    // StyledMenuItem.onHovered opens Special. Clicking after
                    // its hover has opened the submenu would toggle it closed.
                    inputs.Add(D("action",action,"kind","menu-hover","before",before,"final",final,"positioned",true));Write();return;
                }
                var mouse=new[]{new Input{Type=0,Value=new InputUnion{Mouse=new MouseInput{Flags=2}}},new Input{Type=0,Value=new InputUnion{Mouse=new MouseInput{Flags=4}}}};
                uint sent=SendInput(2,mouse,Marshal.SizeOf(typeof(Input)));
                inputs.Add(D("action",action,"kind","menu-click","before",before,"final",final,"sent",sent));Write();
                if(sent==1)
                {
                    try{ConsumerInput.MenuStable(final,MenuSnapshot(root,target,name),name,process.Id,main.ToInt64());
                        report["partialMenuMouseReleaseSent"]=SendInput(1,new[]{mouse[1]},Marshal.SizeOf(typeof(Input)));}
                    catch(Exception error){report["partialMenuMouseReleaseRefused"]=error.Message;}
                }
                Require(sent==2,"Partial effect menu click");Thread.Sleep(180);
            }
            private void FocusedChoice(AutomationElement root,string desired,ControlType role,ushort accept)
            {
                var ready=Stopwatch.StartNew();
                while(ready.ElapsedMilliseconds<10000)
                {
                    Focus(root,null);
                    if(AutomationElement.FocusedElement.Current.ControlType==role)break;
                    Thread.Sleep(150);
                }
                var seen=new HashSet<string>();
                for(int i=0;i<50;i++)
                {
                    Check();var focused=AutomationElement.FocusedElement;
                    Require(focused.Current.ProcessId==process.Id && focused.Current.ControlType==role && focused.Current.IsEnabled && !focused.Current.IsOffscreen,
                        "Choice focus does not have the exact source-defined role");
                    string name=focused.Current.Name;
                    if(name==desired){Keys(root,focused,accept);return;}
                    Require(seen.Add(Identity(focused)),"Choice navigation wrapped without exact expected item: "+desired);
                    Keys(root,focused,0x28);
                }
                throw new InvalidOperationException("Choice exceeded 50 observed items: "+desired);
            }
            private void Choose(AutomationElement root,string prefix,string value)
            { Click(root,prefix,ControlType.ComboBox,true);FocusedChoice(root,value,ControlType.ListItem,0x0D); }
            private void Observe(string stage,AutomationElement root)
            {
                action=stage;var w=new IntPtr(root.Current.NativeWindowHandle);Require(Owned(w),"Screenshot ownership differs");
                SetForegroundWindow(w);Require(GetForegroundWindow()==w,"Screenshot foreground differs");var before=NativeBounds(w);
                var screen=Screenshot(root,directory,"consumer-"+stage+".png",process.Id);
                Require(GetForegroundWindow()==w && String.Join(",",before)==String.Join(",",NativeBounds(w)),"Screenshot root/geometry changed");
                var tree=Tree(root);observations.Add(D("stage",stage,"elapsedMs",clock.ElapsedMilliseconds,"title",root.Current.Name,"window",w.ToInt64(),"tree",tree,"screenshot",screen));Write();
            }
            private void WaitFile(string name)
            {
                var wait=Stopwatch.StartNew();var path=Path.Combine(fixture,name);
                while(wait.ElapsedMilliseconds<30000){Check();if(File.Exists(path) && new FileInfo(path).Length>44)return;Thread.Sleep(150);}
                throw new TimeoutException("Real output absent: "+name);
            }
            private void ExportNew(AutomationElement root,string name)
            {
                NoReparsePath(fixture);
                Require(Hash(Path.Combine(fixture,".owner.json"))==fixtureMarkerHash && !File.Exists(Path.Combine(fixture,name)),
                    "Export target already exists or lost its fixture owner");
                Click(root,"Export",ControlType.Button);WaitFile(name);
            }
            private void WaitClosedProject()
            {
                var wait=Stopwatch.StartNew();
                while(wait.ElapsedMilliseconds<10000)
                { var root=Main();if(root.Current.Name==appTitle){Observe("project-closed",root);return;}Thread.Sleep(150); }
                throw new TimeoutException("Project did not close to the source-defined home-window title");
            }
            private AutomationElement ExportDialog()
            { Shortcut(0x11,0x10,0x45);return Window("Export audio",false); }
            private void Settings(AutomationElement root)
            {
                Target(root,"Format: WAV (Microsoft)",ControlType.ComboBox,false);
                Choose(root,"Encoding ","Signed 16-bit PCM");
                // ExportDialog.qml currently labels the sample-rate dropdown
                // with formatLabel.text; the model includes the Hz suffix.
                Target(root,"Format: 44100 Hz",ControlType.ComboBox,false);
                Click(root,"Stereo",ControlType.RadioButton);
                Field(root,"Folder: ",fixture);
            }
            public bool Run()
            {
                try
                {
                    Require(Marshal.SizeOf(typeof(ConsumerNativeInput))==40 && Marshal.OffsetOf(typeof(ConsumerNativeInput),"Value").ToInt32()==8,"Consumer x64 key ABI differs");
                    Require(File.Exists(Path.Combine(fixture,".owner.json")) && File.Exists(Path.Combine(fixture,"Dawn-thread.wav")),"Exclusive prepared audio fixture missing");NoReparsePath(fixture);
                    Write();action="import-local-wav";Shortcut(0x11,0x10,0x49);Picker("Open",Path.Combine(fixture,"Dawn-thread.wav"),false);
                    Click(Main(),"Clip: Dawn-thread",ControlType.Button);
                    Observe("imported",Main());
                    action="reverse-selected-audio";Shortcut(0x11,0x41);var root=Main();Click(root,"Effect",ControlType.Button);
                    PointAtMenu("Special Menu",true);PointAtMenu("Reverse",false);
                    Observe("reversed",Main());
                    action="save-local-project";Shortcut(0x11,0x53);root=Window("Save project",false);
                    if(root.Current.ClassName!="#32770")Click(root,"On your computer",ControlType.Button);
                    Picker("Save project",Path.Combine(fixture,"Dawn-thread.aup4"),true);WaitFile("Dawn-thread.aup4");Observe("project-saved",Main());
                    action="configure-wav-recipe";root=ExportDialog();Settings(root);Field(root,"File name: ","reversed");
                    Click(root,"Save recipe",ControlType.Button);var save=Window("Save export recipe",false);
                    var name=Click(save,"Recipe name",ControlType.Edit);Type(save,name,"Dawn thread stereo");ConfirmText(save,name,"Dawn thread stereo",IntPtr.Zero);
                    Click(save,"Save recipe",ControlType.Button);root=Window("Export audio",false);Observe("recipe-saved",root);
                    action="apply-saved-recipe";SelectRadio(root,"Mono");
                    report["recipeMonoBeforeApply"]=true;
                    Choose(root,"Spoken-audio export recipe","Dawn thread stereo");RequireSelected(Target(root,"Stereo",ControlType.RadioButton,false));report["recipeStereoAfterApply"]=true;Observe("recipe-applied",root);
                    action="export-reversed-wav";ExportNew(root,"reversed.wav");Observe("exported",Main());
                    action="close-project-and-reopen";Shortcut(0x11,0x57);WaitClosedProject();Shortcut(0x11,0x4F);Picker("Open",Path.Combine(fixture,"Dawn-thread.aup4"),false);
                    Target(Main(),"Clip: Dawn-thread",ControlType.Button,false);Observe("project-reopened",Main());
                    action="export-reopened-project";root=ExportDialog();Choose(root,"Spoken-audio export recipe","Dawn thread stereo");Field(root,"File name: ","reopened");Field(root,"Folder: ",fixture);
                    RequireSelected(Target(root,"Stereo",ControlType.RadioButton,false));ExportNew(root,"reopened.wav");Observe("reopened-exported",Main());
                    captureModules();action="normal-close";Shortcut(0x12,0x73);Require(process.WaitForExit(15000),"Normal UI close did not stop retained process");
                    report["normalCloseExitCode"]=process.ExitCode;Require(process.ExitCode==0,"Normal app close returned nonzero");report["completed"]=true;return true;
                }
                catch(Exception error)
                {
                    ((List<string>)report["errors"]).Add(error.ToString());
                    report["failureFocus"]=MenuFocusFacts();
                    if(!process.HasExited)
                    {
                        try
                        {
                            var trees=new List<object>();foreach(var window in VisibleWindows())trees.Add(D("title",window.Current.Name,"tree",Tree(window)));
                            report["lastObservation"]=trees;var fg=GetForegroundWindow();
                            if(Owned(fg))report["failureScreenshot"]=Screenshot(AutomationElement.FromHandle(fg),directory,"consumer-failure.png",process.Id);
                        }
                        catch(Exception diagnostic){report["diagnosticError"]=diagnostic.ToString();}
                    }
                    throw;
                }
                finally{Write();}
            }
            private void RequireSelected(AutomationElement radio)
            {
                object pattern;Require(radio.TryGetCurrentPattern(SelectionItemPattern.Pattern,out pattern)
                    && ((SelectionItemPattern)pattern).Current.IsSelected,"Actual radio selection state is not proved");
            }
            private void SelectRadio(AutomationElement root,string name)
            {
                // Retain the exact element whose click was guarded. Muse adds
                // section context to the focused provider's accessible name,
                // so re-querying its pre-focus name can no longer find it.
                var radio=Click(root,name,ControlType.RadioButton);var window=new IntPtr(root.Current.NativeWindowHandle);
                Require(Owned(window) && root.Current.ProcessId==process.Id && radio.Current.ProcessId==process.Id
                    && radio.Current.ClassName=="muse::accessibility::AccessibleObject" && radio.Current.NativeWindowHandle==0
                    && radio.Current.ControlType==ControlType.RadioButton && radio.Current.IsEnabled && !radio.Current.IsOffscreen,
                    "Selected radio provider identity/ownership changed");
                RequireSelected(radio);
            }
        }
        private static bool RunConsumer(Process process,AutomationElement main,string directory,string title,string source,Dictionary<string,object> startup)
        {
            startup["startupModules"]=startup["modules"];
            return new ConsumerSession(process,main,directory,title,source,()=>{
                var final=Modules(process);startup["consumerModules"]=final;
                var all=new List<Dictionary<string,object>>((List<Dictionary<string,object>>)startup["startupModules"]);
                all.AddRange(final);startup["modules"]=all; // existing strict verifier checks both observations
            }).Run();
        }
    }
}
