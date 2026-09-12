# SPDX-License-Identifier: GPL-3.0-only
# Replay the actual production settings/choice methods with native UI leaves
# doubled. The names are original Windows evidence; this is no native UI claim.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$driver=Get-Content (Join-Path $PSScriptRoot 'ConsumerDriver.cs') -Raw
function Method([string]$Name) {
    $match=[regex]::Match($driver,'private void '+$Name+'\([^\n]+\)\s*\{')
    if(-not $match.Success){throw "Production method absent: $Name"}
    $end=$match.Index+$match.Length;$depth=1
    while($depth -gt 0 -and $end -lt $driver.Length){if($driver[$end] -eq '{'){$depth++};if($driver[$end] -eq '}'){$depth--};$end++}
    if($depth -ne 0){throw 'Unbalanced production method'}
    $driver.Substring($match.Index,$end-$match.Index)
}
$methods=(Method 'Settings')+(Method 'Choose')+(Method 'FocusedChoice')
Add-Type -TypeDefinition (@'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
namespace WaveEncodingReplay {
 enum ControlType {ComboBox,ListItem,RadioButton}
 sealed class State {public int ProcessId=3104;public ControlType ControlType=ControlType.ListItem;public bool IsEnabled=true,IsOffscreen=false;public string Name;}
 sealed class AutomationElement {public State Current=new State();public static AutomationElement FocusedElement;}
 public sealed class Replay {
  private Process process=Process.GetCurrentProcess();private string fixture="owned-fixture";
  private string[] names;private int index;public int Accepted,Down;public string Selected;
  static void Require(bool pass,string error){if(!pass)throw new InvalidOperationException(error);}
  void Check(){} void Focus(AutomationElement root,AutomationElement target){}
  string Identity(AutomationElement e){return "item-"+index;}
  void SetFocus(){AutomationElement.FocusedElement=new AutomationElement();AutomationElement.FocusedElement.Current.ProcessId=process.Id;AutomationElement.FocusedElement.Current.Name=names[index];}
  void Keys(AutomationElement root,AutomationElement e,ushort key){if(key==0x0D){Accepted++;Selected=e.Current.Name;}else if(key==0x28){Down++;index=(index+1)%names.Length;SetFocus();}else throw new Exception("Unexpected key");}
  void Target(AutomationElement root,string name,ControlType role,bool prefix){}
  void Click(AutomationElement root,string name,ControlType role,bool prefix=false){}
  void Field(AutomationElement root,string name,string value){}
  public void Run(string[] options){names=options;SetFocus();Settings(new AutomationElement());}
'@ + $methods + '}}')
$observed=Get-Content (Join-Path $PSScriptRoot 'fixtures/encoding-options-34711728628.json') -Raw | ConvertFrom-Json
$r=[WaveEncodingReplay.Replay]::new();$r.Run([string[]]$observed.focus_names)
if($r.Accepted -ne 1 -or $r.Down -ne 0 -or $r.Selected -cne $observed.failure_focus.uia.name){throw 'Actual encoding was not accepted exactly once without navigation'}
foreach($wrong in @('Signed 16 bit PCM','Signed 16–bit PCM','signed 16-bit PCM')){
    $r=[WaveEncodingReplay.Replay]::new();$failed=$false
    try{$r.Run(@($wrong,'Signed 24-bit PCM'))}catch{if($_.Exception.ToString() -notlike '*Choice navigation wrapped*'){throw};$failed=$true}
    if(-not $failed -or $r.Accepted -ne 0 -or $r.Down -ne 2){throw 'Nonexact encoding accepted or navigation replayed after wrap'}
}
'PASS actual Settings/Choose/FocusedChoice with retained encoding options, exact one Enter and three nonexact-label refusals.'
