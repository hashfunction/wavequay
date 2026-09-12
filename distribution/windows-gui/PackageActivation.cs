// SPDX-License-Identifier: GPL-3.0-only
// Copyright (C) 2026 Trieflow LLC
// Native activation declarations follow the reviewed Scriblark helper;
// its retained MIT notice is distribution/msix/PIPELINE-MIT.txt.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

namespace WaveQuayQualification
{
    [ComImport, Guid("45BA127D-10A8-46EA-8AB7-56EA9078943C")]
    internal class ApplicationActivationManagerClass { }
    [ComImport, Guid("2E941141-7F97-4756-BA1D-9DECDE894A3D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IApplicationActivationManager
    {
        [PreserveSig] int ActivateApplication([MarshalAs(UnmanagedType.LPWStr)] string appUserModelId,
            [MarshalAs(UnmanagedType.LPWStr)] string arguments, uint options, out uint processId);
        [PreserveSig] int ActivateForFile([MarshalAs(UnmanagedType.LPWStr)] string appUserModelId,
            IntPtr shellItemArray, [MarshalAs(UnmanagedType.LPWStr)] string verb, out uint processId);
        [PreserveSig] int ActivateForProtocol([MarshalAs(UnmanagedType.LPWStr)] string appUserModelId,
            IntPtr shellItemArray, out uint processId);
    }

    public static class PackageActivation
    {
        [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
        private struct PackageId
        {
            public uint Reserved, Architecture;
            public ulong Version;
            [MarshalAs(UnmanagedType.LPWStr)] public string Name, Publisher, ResourceId, PublisherId;
        }
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
        private static extern int PackageFamilyNameFromId(ref PackageId id, ref uint length, StringBuilder name);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
        private static extern int GetPackageFullName(IntPtr process, ref uint length, StringBuilder name);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
        private static extern int GetPackageFamilyName(IntPtr process, ref uint length, StringBuilder name);

        public static string FamilyForMode(string mode)
        {
            if(mode!="store" && mode!="qualification")throw new InvalidOperationException("Unexpected identity mode");
            var id=new PackageId { Architecture=9, Version=((ulong)1<<48)|((ulong)1<<16), ResourceId="",
                Name=mode=="store" ? "1659hashfunction.WaveQuay" : "Trieflow.WaveQuay.Qualification",
                Publisher=mode=="store" ? "CN=B6A2631A-FD32-45CC-AE12-82466975F528" : "CN=WaveQuay-CI-Qualification" };
            uint length=0;int result=PackageFamilyNameFromId(ref id,ref length,null);
            if(result!=122 || length<2 || length>1024)throw new InvalidOperationException("Cannot derive fixed package family: "+result);
            var value=new StringBuilder((int)length);
            result=PackageFamilyNameFromId(ref id,ref length,value);
            if(result!=0)throw new InvalidOperationException("Cannot derive fixed package family: "+result);
            string family=value.ToString();
            ValidateIdentity(mode,id.Name+"_1.0.1.0_x64__"+family.Substring(id.Name.Length+1),family);
            return family;
        }

        public static string ValidateIdentity(string mode, string fullName, string family)
        {
            string name;
            if(mode == "store")
            {
                name = "1659hashfunction.WaveQuay";
                if(family != "1659hashfunction.WaveQuay_r3hxytd7jt6c4")
                    throw new InvalidOperationException("Assigned Store package family differs");
            }
            else if(mode == "qualification") name = "Trieflow.WaveQuay.Qualification";
            else throw new InvalidOperationException("Only fixed qualification/store modes are supported");
            if(family == null || !Regex.IsMatch(family, "^"+Regex.Escape(name)+"_[0-9a-hjkmnp-tv-z]{13}$"))
                throw new InvalidOperationException("Unexpected package family");
            string publisherId = family.Substring(name.Length+1);
            if(fullName != name+"_1.0.1.0_x64__"+publisherId)
                throw new InvalidOperationException("Package full name/version/architecture/resource identity differs");
            return family+"!WaveQuay";
        }

        public static void ValidateLifetime(int pid, int[] preexisting, DateTime started, DateTime activation)
        {
            if(pid <= 0 || Array.IndexOf(preexisting, pid) >= 0 || started.Kind != DateTimeKind.Utc
                || activation.Kind != DateTimeKind.Utc || started < activation)
                throw new InvalidOperationException("Activation returned a pre-existing, stale or invalid process");
        }

        public static string FullName(Process process)
        {
            uint length=0; int result=GetPackageFullName(process.Handle,ref length,null);
            if(result!=122 || length<2 || length>1024)throw new InvalidOperationException("Owned process has no bounded package identity: "+result);
            var value=new StringBuilder((int)length);
            result=GetPackageFullName(process.Handle,ref length,value);
            if(result!=0)throw new InvalidOperationException("Cannot read owned process package identity: "+result);
            return value.ToString();
        }

        private static string FamilyName(Process process)
        {
            uint length=0;int result=GetPackageFamilyName(process.Handle,ref length,null);
            if(result!=122 || length<2 || length>1024)throw new InvalidOperationException("No bounded process package family: "+result);
            var value=new StringBuilder((int)length);
            result=GetPackageFamilyName(process.Handle,ref length,value);
            if(result!=0)throw new InvalidOperationException("Cannot read process package family: "+result);
            return value.ToString();
        }

        public static Process Start(string mode, string fullName, string family, string executable,
                                    out DateTime activation, out int[] before)
        {
            string aumid=ValidateIdentity(mode,fullName,family);
            if(family!=FamilyForMode(mode))throw new InvalidOperationException("Package family differs from the fixed publisher identity");
            var ids=new List<int>();
            foreach(var item in Process.GetProcesses()) {using(item)ids.Add(item.Id);}
            before=ids.ToArray();
            uint pid=0;object instance=new ApplicationActivationManagerClass();
            activation=DateTime.UtcNow;
            try {
                int result=((IApplicationActivationManager)instance).ActivateApplication(aumid,null,0,out pid);
                if(result<0)Marshal.ThrowExceptionForHR(result);
            } finally {Marshal.FinalReleaseComObject(instance);}
            if(pid==0 || pid>Int32.MaxValue)throw new InvalidOperationException("Activation broker returned invalid PID");
            var candidate=Process.GetProcessById((int)pid);
            try {
                // Open and retain the actual handle before any ownership decision.
                IntPtr handle=candidate.Handle;
                ValidateLifetime(candidate.Id,before,candidate.StartTime.ToUniversalTime(),activation);
                if(candidate.HasExited || FullName(candidate)!=fullName || FamilyName(candidate)!=family
                    || !String.Equals(Path.GetFullPath(candidate.MainModule.FileName),Path.GetFullPath(executable),StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Broker process differs from the exact installed package/executable");
                return candidate;
            } catch {candidate.Dispose();throw;} // no unowned process is stopped
        }
    }
}
