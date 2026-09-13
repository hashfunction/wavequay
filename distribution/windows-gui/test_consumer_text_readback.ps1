# SPDX-License-Identifier: GPL-3.0-only
# Managed query/ownership seam fixtures, not Windows product UI evidence.
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
Add-Type -Path @((Join-Path $PSScriptRoot 'ConsumerTextReadback.cs'),(Join-Path $PSScriptRoot 'ConsumerTextReadbackTests.cs'))
[WaveQuayQualificationTests.ConsumerTextReadbackTests]::Run()

# Execute the production UIA pattern selector. Private types model the public
# UIA interfaces; they do not collide with the real preloaded Windows assemblies.
$driver=Get-Content (Join-Path $PSScriptRoot 'ConsumerDriver.cs') -Raw
$match=[regex]::Match($driver,'private string TextValue\(AutomationElement target\)\s*\{')
if(-not $match.Success){throw 'Production TextValue method absent'}
$end=$match.Index+$match.Length;$depth=1
while($depth -gt 0 -and $end -lt $driver.Length){if($driver[$end] -eq '{'){$depth++};if($driver[$end] -eq '}'){$depth--};$end++}
if($depth -ne 0){throw 'Unbalanced production TextValue'}
$method=$driver.Substring($match.Index,$end-$match.Index)
Add-Type -TypeDefinition (@'
using System;
namespace WaveTextPatternReplay {
 sealed class ValuePattern { public static readonly object Pattern=new object();public ValueState Current=new ValueState(); }
 sealed class ValueState { public string Value; }
 sealed class TextPattern { public static readonly object Pattern=new object();public TextRange DocumentRange=new TextRange(); }
 sealed class TextRange {
  public string Text;public bool Fail;public int Limit;
  public string GetText(int limit){Limit=limit;if(Fail)throw new InvalidOperationException("original text getter failure");return Text;}
 }
 sealed class AutomationElement {
  public ValuePattern Value;public TextPattern Text;public string Queries="";
  public bool TryGetCurrentPattern(object pattern,out object value){
   if(pattern==TextPattern.Pattern){Queries+="T";value=Text;}else if(pattern==ValuePattern.Pattern){Queries+="V";value=Value;}else throw new Exception("Unexpected pattern");
   return value!=null;
  }
 }
 public sealed class Replay {
  static void Require(bool value,string message){if(!value)throw new Exception(message);}
  static AutomationElement Both(string text,string value){return new AutomationElement{Text=new TextPattern{DocumentRange=new TextRange{Text=text}},Value=new ValuePattern{Current=new ValueState{Value=value}}};}
  public string Run(string folder,string originalValue){
   foreach(string expected in new[]{folder,"reversed","Dawn thread stereo"}){
    var target=Both(expected,originalValue);
    Require(TextValue(target)==expected,"Muse editable text was hidden by empty ValuePattern");
    Require(target.Queries=="T" && target.Text.DocumentRange.Limit==4096,"Text read was not bounded or empty ValuePattern was consulted");
   }
   foreach(string wrong in new[]{"","other path"}){
    var target=Both(wrong,"expected");
    Require(TextValue(target)==wrong && target.Queries=="T","Wrong text fell back to a convenient ValuePattern");
   }
   var broken=Both("expected","expected");broken.Text.DocumentRange.Fail=true;bool failed=false;
   try{TextValue(broken);}catch(InvalidOperationException error){Require(error.Message=="original text getter failure","Original getter failure lost");failed=true;}
   Require(failed && broken.Queries=="T","Text getter failure was swallowed or used Value fallback");
   var valueOnly=new AutomationElement{Value=new ValuePattern{Current=new ValueState{Value="value-only edit"}}};
   Require(TextValue(valueOnly)=="value-only edit" && valueOnly.Queries=="TV","Value-only public UIA control was not read");
   var neither=new AutomationElement();failed=false;
   try{TextValue(neither);}catch(InvalidOperationException error){Require(error.Message=="No independent UI text readback for target","Missing-pattern failure changed");failed=true;}
   Require(failed && neither.Queries=="TV","Missing public readback was accepted");
   var lines=Both("exact\r\n","");Require(TextValue(lines)=="exact","Existing terminal CR/LF handling changed");
   return "PASS: actual TextValue selector, three Muse field values, wrong/empty/throwing Text refusal to fallback, Value-only/missing patterns and bounded terminal handling.";
  }
'@ + $method + '}}')
$original=Get-Content (Join-Path $PSScriptRoot 'fixtures/folder-readback-34725528186.json') -Raw | ConvertFrom-Json
if($original.readback.confirmed -ne $false -or $original.read_count -ne 77 -or $original.first_read.value -cne '' -or $original.last_read.value -cne ''){throw 'Retained original empty readback sample differs'}
[WaveTextPatternReplay.Replay]::new().Run($original.readback.expected,$original.first_read.value)
