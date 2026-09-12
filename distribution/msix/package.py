# SPDX-License-Identifier: MIT
# Copyright 2026 Trieflow LLC.
# File, PNG and MSIX checks derived from Scriblark's reviewed qualification
# implementation (474e93cec63af125eab0458ef97c889a79ec7be7).
# Retained upstream terms: PIPELINE-MIT.txt and RETICLEQUAY-MIT.txt.
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import unicodedata
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zipfile
from files import (file_record, inventory_tree, assert_unsigned_payload, resize_png,
                   _digest, _regular_stream, _register_path, _checked_path, _write_new, _reject_link)

ROOT = Path(__file__).resolve().parents[2]
ARTWORK = ROOT / 'distribution/branding/waveweft.png'
APPX_NS = 'http://schemas.microsoft.com/appx/manifest/foundation/windows10'
UAP_NS = 'http://schemas.microsoft.com/appx/manifest/uap/windows10'
RESCAP_NS = 'http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities'
ET.register_namespace('', APPX_NS)
ET.register_namespace('uap', UAP_NS)
ET.register_namespace('rescap', RESCAP_NS)
QUALIFICATION_IDENTITY = {
    'packageName': 'Trieflow.WaveQuay.Qualification',
    'publisher': 'CN=WaveQuay-CI-Qualification',
    'version': '1.0.1.0', 'architecture': 'x64', 'applicationId': 'WaveQuay',
    'executable': 'bin/WaveWeft.exe', 'deviceFamily': 'Windows.Desktop',
    'minVersion': '10.0.19041.0', 'maxVersionTested': '10.0.26100.0', 'capability': 'runFullTrust',
}
STORE_IDENTITY = {**QUALIFICATION_IDENTITY,
    'packageName': '1659hashfunction.WaveQuay',
    'publisher': 'CN=B6A2631A-FD32-45CC-AE12-82466975F528',
    'familyName': '1659hashfunction.WaveQuay_r3hxytd7jt6c4'}
PACKAGE_METADATA = {'[Content_Types].xml', 'AppxBlockMap.xml', 'AppxMetadata/CodeIntegrity.cat'}


def identity_for_mode(mode="qualification"):
    if mode not in ("qualification", "store"):
        raise ValueError("Only fixed qualification/store identities are supported")
    return dict(STORE_IDENTITY if mode == "store" else QUALIFICATION_IDENTITY)


def generated_files(mode='qualification', source_files=None):
    artwork = ARTWORK.read_bytes()
    result = {
        'AppxManifest.xml': create_manifest(mode),
        'Assets/StoreLogo.png': resize_png(artwork, 50),
        'Assets/Square44x44Logo.png': resize_png(artwork, 44),
        'Assets/Square150x150Logo.png': resize_png(artwork, 150),
    }
    if source_files is not None:
        for name, data in source_files.items():
            _checked_path(name)
            if not isinstance(data, bytes) or not (name in ('SOURCE-INFO.json', 'SOURCE-README.txt') or name.startswith('Notices/')):
                raise ValueError('Invalid generated source/notice package member')
            if name in result:
                raise ValueError('Duplicate generated package member')
            result[name] = data
    return result


def expected_payload(release, mode='qualification', source_files=None):
    """Regenerate from current stage and source-owned artwork, never a receipt."""
    files = inventory_tree(release)
    assert_unsigned_payload(files)
    if not files.get('bin/WaveWeft.exe', {}).get('bytes'):
        raise ValueError('Missing WaveWeft executable')
    generated = generated_files(mode, source_files)
    for name, data in generated.items():
        if name in files or any(n.casefold() == name.casefold() for n in files):
            raise ValueError('Stage contains generated package input: ' + name)
        files[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    seen = {}
    for name in files:
        _register_path(name, seen)
        if name in PACKAGE_METADATA:
            raise ValueError('Stage contains container metadata: ' + name)
    assert_unsigned_payload(files)
    return files


def stage_payload(release, destination, mode='qualification', source_files=None):
    expected = expected_payload(release, mode, source_files)
    destination = Path(destination)
    for ancestor in destination.absolute().parents:
        _reject_link(ancestor)
    destination.mkdir()  # exclusive: preserve any earlier stage or package
    for name in inventory_tree(release):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with _regular_stream(Path(release) / name) as source, target.open('xb') as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
    for name, data in generated_files(mode, source_files).items():
        _write_new(destination / name, data)
    if inventory_tree(destination) != expected:
        raise ValueError('Package payload changed while copying')
    validate_manifest((destination / 'AppxManifest.xml').read_bytes(), mode)
    return expected


def package_name(mode="qualification"):
    identity_for_mode(mode)
    return (
        "WaveWeft" if mode == "store" else "WaveWeft.Qualification"
    ) + "_1.0.1.0_x64.msix"


def create_manifest(mode="qualification"):
    identity = identity_for_mode(mode)
    package = ET.Element(f"{{{APPX_NS}}}Package", {"IgnorableNamespaces": "uap rescap"})
    ET.SubElement(
        package,
        f"{{{APPX_NS}}}Identity",
        {
            "Name": identity["packageName"],
            "Publisher": identity["publisher"],
            "Version": identity["version"],
            "ProcessorArchitecture": identity["architecture"],
        },
    )
    properties = ET.SubElement(package, f"{{{APPX_NS}}}Properties")
    for name, value in (
        ("DisplayName", "WaveWeft"),
        ("PublisherDisplayName", "hashfunction" if mode == "store" else "Trieflow LLC"),
        (
            "Description",
            "WaveWeft" if mode == "store" else "WaveWeft qualification package",
        ),
        ("Logo", r"Assets\StoreLogo.png"),
    ):
        ET.SubElement(properties, f"{{{APPX_NS}}}{name}").text = value
    resources = ET.SubElement(package, f"{{{APPX_NS}}}Resources")
    ET.SubElement(resources, f"{{{APPX_NS}}}Resource", {"Language": "en-US"})
    dependencies = ET.SubElement(package, f"{{{APPX_NS}}}Dependencies")
    ET.SubElement(
        dependencies,
        f"{{{APPX_NS}}}TargetDeviceFamily",
        {
            "Name": identity["deviceFamily"],
            "MinVersion": identity["minVersion"],
            "MaxVersionTested": identity["maxVersionTested"],
        },
    )
    applications = ET.SubElement(package, f"{{{APPX_NS}}}Applications")
    application = ET.SubElement(
        applications,
        f"{{{APPX_NS}}}Application",
        {
            "Id": identity["applicationId"],
            "Executable": identity["executable"],
            "EntryPoint": "Windows.FullTrustApplication",
        },
    )
    ET.SubElement(
        application,
        f"{{{UAP_NS}}}VisualElements",
        {
            "DisplayName": "WaveWeft",
            "Description": (
                "WaveWeft" if mode == "store" else "WaveWeft qualification package"
            ),
            "BackgroundColor": "#142e38",
            "Square150x150Logo": r"Assets\Square150x150Logo.png",
            "Square44x44Logo": r"Assets\Square44x44Logo.png",
        },
    )
    capabilities = ET.SubElement(package, f"{{{APPX_NS}}}Capabilities")
    ET.SubElement(
        capabilities, f"{{{RESCAP_NS}}}Capability", {"Name": identity["capability"]}
    )
    ET.indent(package, space="  ")
    return ET.tostring(package, encoding="utf-8", xml_declaration=True)


def _one(parent, tag, label):
    items = parent.findall(tag)
    if len(items) != 1:
        raise ValueError(f"Manifest requires exactly one {label}")
    return items[0]


def validate_manifest(data, mode="qualification"):
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"Invalid manifest XML: {error}") from error
    if root.tag != f"{{{APPX_NS}}}Package" or root.attrib != {
        "IgnorableNamespaces": "uap rescap"
    }:
        raise ValueError("Invalid manifest package root")
    expected_children = [
        f"{{{APPX_NS}}}Identity",
        f"{{{APPX_NS}}}Properties",
        f"{{{APPX_NS}}}Resources",
        f"{{{APPX_NS}}}Dependencies",
        f"{{{APPX_NS}}}Applications",
        f"{{{APPX_NS}}}Capabilities",
    ]
    if [child.tag for child in root] != expected_children:
        raise ValueError("Unexpected manifest sections or extensions")
    identity_node = _one(root, f"{{{APPX_NS}}}Identity", "identity")
    identity = identity_for_mode(mode)
    if identity_node.attrib != {
        "Name": identity["packageName"],
        "Publisher": identity["publisher"],
        "Version": identity["version"],
        "ProcessorArchitecture": identity["architecture"],
    }:
        raise ValueError("Unexpected qualification identity")
    properties = _one(root, f"{{{APPX_NS}}}Properties", "properties")
    expected_properties = {
        "DisplayName": "WaveWeft",
        "PublisherDisplayName": "hashfunction" if mode == "store" else "Trieflow LLC",
        "Description": (
            "WaveWeft" if mode == "store" else "WaveWeft qualification package"
        ),
        "Logo": r"Assets\StoreLogo.png",
    }
    if (
        len(properties) != len(expected_properties)
        or {child.tag.rsplit("}", 1)[-1]: child.text for child in properties}
        != expected_properties
        or any(child.attrib or len(child) for child in properties)
    ):
        raise ValueError("Unexpected manifest properties")
    resources = _one(root, f"{{{APPX_NS}}}Resources", "resources")
    resource = _one(resources, f"{{{APPX_NS}}}Resource", "resource")
    if len(resources) != 1 or resource.attrib != {"Language": "en-US"} or len(resource):
        raise ValueError("Unexpected manifest resources")
    dependencies = _one(root, f"{{{APPX_NS}}}Dependencies", "dependencies")
    family = _one(
        dependencies, f"{{{APPX_NS}}}TargetDeviceFamily", "target device family"
    )
    if (
        len(dependencies) != 1
        or family.attrib
        != {
            "Name": identity["deviceFamily"],
            "MinVersion": identity["minVersion"],
            "MaxVersionTested": identity["maxVersionTested"],
        }
        or len(family)
    ):
        raise ValueError("Unexpected target device family")
    applications = _one(root, f"{{{APPX_NS}}}Applications", "applications")
    application = _one(applications, f"{{{APPX_NS}}}Application", "application")
    if len(applications) != 1 or application.attrib != {
        "Id": identity["applicationId"],
        "Executable": identity["executable"],
        "EntryPoint": "Windows.FullTrustApplication",
    }:
        raise ValueError("Unexpected manifest executable/application")
    visual = _one(application, f"{{{UAP_NS}}}VisualElements", "visual elements")
    if (
        len(application) != 1
        or visual.attrib
        != {
            "DisplayName": "WaveWeft",
            "Description": (
                "WaveWeft" if mode == "store" else "WaveWeft qualification package"
            ),
            "BackgroundColor": "#142e38",
            "Square150x150Logo": r"Assets\Square150x150Logo.png",
            "Square44x44Logo": r"Assets\Square44x44Logo.png",
        }
        or len(visual)
    ):
        raise ValueError("Unexpected manifest visual elements")
    capabilities = _one(root, f"{{{APPX_NS}}}Capabilities", "capabilities")
    capability = _one(capabilities, f"{{{RESCAP_NS}}}Capability", "capability")
    if (
        len(capabilities) != 1
        or capability.attrib != {"Name": identity["capability"]}
        or len(capability)
    ):
        raise ValueError("Unexpected manifest capabilities")
    return dict(identity)


def _decode_opc_path(value):
    # MakeAppx stores OPC URI names in the ZIP, e.g. libc++.dll becomes
    # libc%2B%2B.dll. Decode once before payload/hash and alias comparison.
    # Escaped separators cannot change the archive's directory hierarchy.
    if re.search(r"%(?![0-9A-Fa-f]{2})|%(?:2f|5c)", value, re.I):
        raise ValueError(f"Malformed or hierarchy-changing OPC path: {value!r}")
    return _checked_path(unquote(value, encoding="utf-8", errors="strict"))


def verify_msix(path, expected, mode="qualification"):
    assert_unsigned_payload(expected)
    if not isinstance(expected, dict) or "AppxManifest.xml" not in expected:
        raise ValueError("Invalid expected package payload")
    allowed_directories = {
        str(parent)
        for name in set(expected) | PACKAGE_METADATA
        for parent in PurePosixPath(name).parents
        if str(parent) != "."
    }
    seen = {}
    actual = {}
    metadata = set()
    directories = set()
    manifest_data = None
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = _decode_opc_path(
                info.filename.rstrip("/") if info.is_dir() else info.filename
            )
            file_mode = info.external_attr >> 16
            if info.flag_bits & 1:
                raise ValueError(f"Encrypted package entry: {info.filename}")
            if info.is_dir():
                key = unicodedata.normalize("NFC", name).casefold()
                if (
                    stat.S_IFMT(file_mode) not in (0, stat.S_IFDIR)
                    or name not in allowed_directories
                    or key in directories
                ):
                    raise ValueError(
                        f"Unexpected/special package directory: {info.filename}"
                    )
                directories.add(key)
                continue
            _register_path(name, seen)
            if stat.S_IFMT(file_mode) not in (0, stat.S_IFREG):
                raise ValueError(f"Special package entry: {name}")
            if name in PACKAGE_METADATA:
                if info.file_size > 32 * 1024 * 1024:
                    raise ValueError(f"Oversized package metadata: {name}")
                metadata.add(name)
                continue
            record = expected.get(name)
            if not record or info.file_size != record["bytes"]:
                raise ValueError(f"Unexpected package entry or size: {name}")
            with archive.open(info) as stream:
                measured = _digest(stream)
            if measured != record:
                raise ValueError(f"Package hash mismatch: {name}")
            actual[name] = measured
            if name == "AppxManifest.xml":
                manifest_data = archive.read(info)
    if set(actual) != set(expected):
        raise ValueError("Package payload is missing expected files")
    if not {"[Content_Types].xml", "AppxBlockMap.xml"}.issubset(metadata):
        raise ValueError("Package metadata is incomplete")
    validate_manifest(manifest_data, mode)
    with _regular_stream(path) as stream:
        package = _digest(stream)
    return {
        "verifiedPayloadFiles": len(actual),
        "metadata": sorted(metadata),
        "package": package,
    }


def verify_unpacked(root, expected, mode="qualification"):
    actual = inventory_tree(root)
    for metadata in PACKAGE_METADATA:
        actual.pop(metadata, None)
    if actual != expected:
        raise ValueError("SDK-unpacked payload differs from staged payload")
    validate_manifest((Path(root) / "AppxManifest.xml").read_bytes(), mode)
    return {"verifiedPayloadFiles": len(actual)}


def verify_installed(root, expected, mode="qualification"):
    actual = inventory_tree(root)
    for metadata in PACKAGE_METADATA | {"AppxSignature.p7x"}:
        actual.pop(metadata, None)
    if actual != expected:
        raise ValueError(
            "Installed package has missing, altered or extra payload files"
        )
    validate_manifest((Path(root) / "AppxManifest.xml").read_bytes(), mode)
    return {"verifiedPayloadFiles": len(actual)}
