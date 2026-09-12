// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32;

namespace WaveQuayQualification
{
    public static partial class GuiProbe
    {
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] private static extern bool CreateDirectory(string path,IntPtr security);
        [DllImport("advapi32.dll",CharSet=CharSet.Unicode)] private static extern int RegCreateKeyEx(IntPtr hive,string key,int reserved,string keyClass,
            int options,int access,IntPtr security,out IntPtr handle,out int disposition);
        [DllImport("advapi32.dll")] private static extern int RegCloseKey(IntPtr handle);
        private static Dictionary<string,object> ClaimConsumerProfile(List<Dictionary<string,object>> state,string privateRoot)
        {
            string token=Guid.NewGuid().ToString();var paths=new List<string>();
            foreach(var item in state)
            {
                string path=(string)item["path"],name=Path.GetFileName(path),parent=Path.GetDirectoryName(path);
                if((name=="Audacity4" || name=="Audacity4Development") && (Path.GetFileName(parent)=="Trieflow"
                    || parent==Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)))
                { if((bool)item["exists"] || Directory.Exists(path) || File.Exists(path))throw new IOException("Existing profile is not owned: "+path);paths.Add(path); }
            }
            if(paths.Count!=6)throw new InvalidOperationException("Expected six exact source-defined fresh profile roots");
            string[] registry={@"Software\Trieflow\Audacity4",@"Software\Trieflow\Audacity4Development"};
            foreach(string key in registry)using(var existing=Registry.CurrentUser.OpenSubKey(key))
                if(existing!=null)throw new IOException("Existing HKCU product settings are not owned: "+key);
            foreach(string path in paths)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path));NoReparsePath(Path.GetDirectoryName(path));
                if(!CreateDirectory(path,IntPtr.Zero))throw new IOException("Profile leaf was not exclusively created: "+path);
            }
            paths.Add(privateRoot);
            foreach(string path in paths)
                using(var stream=new FileStream(Path.Combine(path,".waveweft-consumer-owner"),FileMode.CreateNew,FileAccess.Write,FileShare.None))
                { byte[] bytes=Encoding.UTF8.GetBytes(token);stream.Write(bytes,0,bytes.Length); }
            foreach(string key in registry)
            {
                IntPtr handle;int disposition;int result=RegCreateKeyEx(new IntPtr(unchecked((int)0x80000001u)),key,0,null,0,0x20006,IntPtr.Zero,out handle,out disposition);
                if(result!=0)throw new IOException("Cannot exclusively create owned HKCU profile: "+result);
                RegCloseKey(handle);
                if(disposition!=1)throw new IOException("HKCU profile appeared during exclusive claim; preserved");
                using(var owned=Registry.CurrentUser.OpenSubKey(key,true))owned.SetValue("__WaveWeftConsumerOwner",token,RegistryValueKind.String);
            }
            return D("token",token,"paths",paths,"registry",registry,"marker",".waveweft-consumer-owner");
        }
    }
}
