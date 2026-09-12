# SPDX-License-Identifier: GPL-3.0-only
# Replay the actual production settings/choice methods with native UI leaves
# doubled. The names are original Windows evidence; this is no native UI claim.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$driver=Get-Content (Join-Path $PSScriptRoot 'ConsumerDriver.cs') -Raw
function Method([string]$Name) {
    $match=[regex]::Match($driver,'private (?:void|List<AutomationElement>) '+$Name+'\([^\n]+\)\s*\{')
    if(-not $match.Success){throw "Production method absent: $Name"}
    $end=$match.Index+$match.Length;$depth=1
    while($depth -gt 0 -and $end -lt $driver.Length){if($driver[$end] -eq '{'){$depth++};if($driver[$end] -eq '}'){$depth--};$end++}
    if($depth -ne 0){throw 'Unbalanced production method'}
    $driver.Substring($match.Index,$end-$match.Index)
}
$methods=(Method 'Settings')+(Method 'Choose')+(Method 'FocusedChoice')+(Method 'Match')
Add-Type -TypeDefinition (@'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
namespace WaveEncodingReplay {
 enum ControlType {ComboBox,ListItem,RadioButton,Edit,Button}
 public sealed class ControlRow {public string Name,Role;public int Pid;public bool Enabled,Offscreen;}
 sealed class State {public int ProcessId=3104;public ControlType ControlType=ControlType.ListItem;public bool IsEnabled=true,IsOffscreen=false;public string Name;}
 sealed class AutomationElement {public State Current=new State();public static AutomationElement FocusedElement;}
 public sealed class Replay {
  private Process process=Process.GetCurrentProcess();private string fixture="owned-fixture";
  private string[] names;private int index;public int Accepted,Down,SettingsTailCalls;public string Selected;
  private List<AutomationElement> observed=new List<AutomationElement>(),queryParents=new List<AutomationElement>();
  void Enumerate(AutomationElement root,List<AutomationElement> nodes,int depth){nodes.AddRange(observed);}
  void QueryStep(AutomationElement node,int depth,int count,string step){}
  static void Require(bool pass,string error){if(!pass)throw new InvalidOperationException(error);}
  void Check(){} void Focus(AutomationElement root,AutomationElement target){}
  string Identity(AutomationElement e){return "item-"+index;}
  void SetFocus(){AutomationElement.FocusedElement=new AutomationElement();AutomationElement.FocusedElement.Current.ProcessId=process.Id;AutomationElement.FocusedElement.Current.Name=names[index];}
  void Keys(AutomationElement root,AutomationElement e,ushort key){if(key==0x0D){Accepted++;Selected=e.Current.Name;}else if(key==0x28){Down++;index=(index+1)%names.Length;SetFocus();}else throw new Exception("Unexpected key");}
  AutomationElement Target(AutomationElement root,string name,ControlType role,bool prefix){var matches=Match(root,name,role,prefix);Require(matches.Count==1,"Exact observed control absent or ambiguous: "+name);return matches[0];}
  void Click(AutomationElement root,string name,ControlType role,bool prefix=false){Target(root,name,role,prefix);if(role==ControlType.RadioButton)SettingsTailCalls++;}
  void Field(AutomationElement root,string name,string value){Target(root,name,ControlType.Edit,true);SettingsTailCalls++;}
  public void Run(string[] options,ControlRow[] rows,int originalPid){
   foreach(var row in rows)observed.Add(new AutomationElement{Current=new State{Name=row.Name,ControlType=(ControlType)Enum.Parse(typeof(ControlType),row.Role),ProcessId=row.Pid==originalPid?process.Id:row.Pid,IsEnabled=row.Enabled,IsOffscreen=row.Offscreen}});
   names=options;SetFocus();Settings(new AutomationElement());
  }
  public void AssertObserved(string name,string role,bool prefix){Target(new AutomationElement(),name,(ControlType)Enum.Parse(typeof(ControlType),role),prefix);}
'@ + $methods + '}}')
$observed=Get-Content (Join-Path $PSScriptRoot 'fixtures/encoding-options-34711728628.json') -Raw | ConvertFrom-Json
$settings=Get-Content (Join-Path $PSScriptRoot 'fixtures/export-settings-34723127574.json') -Raw | ConvertFrom-Json
function Controls {
    [WaveEncodingReplay.ControlRow[]]@($settings.controls | ForEach-Object {
        [WaveEncodingReplay.ControlRow]@{Name=$_.name;Role=$_.controlType;Pid=$_.processId;Enabled=$_.enabled;Offscreen=$_.offscreen}
    })
}
$r=[WaveEncodingReplay.Replay]::new();$r.Run([string[]]$observed.focus_names,(Controls),$settings.process_id)
if($r.Accepted -ne 1 -or $r.Down -ne 0 -or $r.Selected -cne $observed.failure_focus.uia.name -or $r.SettingsTailCalls -ne 2){throw 'Actual encoding was not accepted exactly once without navigation'}
foreach($wrong in @('Signed 16 bit PCM','Signed 16–bit PCM','signed 16-bit PCM')){
    $r=[WaveEncodingReplay.Replay]::new();$failed=$false
    try{$r.Run(@($wrong,'Signed 24-bit PCM'),(Controls),$settings.process_id)}catch{if($_.Exception.ToString() -notlike '*Choice navigation wrapped*'){throw};$failed=$true}
    if(-not $failed -or $r.Accepted -ne 0 -or $r.Down -ne 2){throw 'Nonexact encoding accepted or navigation replayed after wrap'}
}
# These existing controls are needed by the remaining consumer sequence. Replay
# actual Match against original rows; this does not simulate the later dialogs.
foreach($name in @('Mono','Stereo')){$r=[WaveEncodingReplay.Replay]::new();$r.Run([string[]]$observed.focus_names,(Controls),$settings.process_id);$r.AssertObserved($name,'RadioButton',$false)}
foreach($pair in @(@('File name: ','Edit'),@('Save recipe','Button'),@('Spoken-audio export recipe','ComboBox'),@('Export','Button'))){$r.AssertObserved($pair[0],$pair[1],$pair[0] -ceq 'File name: ')}
foreach($wrong in @('Format: 44100','Format: 48000 Hz','Format: 44100 kHz','Format: 44100 hz')) {
    $rows=Controls;($rows | Where-Object Name -CEQ 'Format: 44100 Hz').Name=$wrong
    $r=[WaveEncodingReplay.Replay]::new();$failed=$false
    try{$r.Run([string[]]$observed.focus_names,$rows,$settings.process_id)}catch{if($_.Exception.ToString() -notlike '*Exact observed control absent or ambiguous: Format: 44100 Hz*'){throw};$failed=$true}
    if(-not $failed -or $r.Accepted -ne 1 -or $r.SettingsTailCalls -ne 0){throw 'Nonexact rate accepted or later settings actions reached'}
}
$rows=Controls;$duplicate=$rows | Where-Object Name -CEQ 'Format: 44100 Hz'
$r=[WaveEncodingReplay.Replay]::new();$failed=$false
try{$r.Run([string[]]$observed.focus_names,($rows+@($duplicate)),$settings.process_id)}catch{if($_.Exception.ToString() -notlike '*Exact observed control absent or ambiguous: Format: 44100 Hz*'){throw};$failed=$true}
if(-not $failed -or $r.SettingsTailCalls -ne 0){throw 'Ambiguous rate accepted'}
'PASS actual Settings/Choose/FocusedChoice/Match with original controls, exact one Enter, three encoding and five rate refusals, remaining observed selectors.'
