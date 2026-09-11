#!/usr/bin/env python3
"""Fail closed on known service endpoints in an unpacked staged application.

This is a supplement to compile-time exclusion and runtime network testing;
passing a string scan alone does not prove absence of network activity.
"""
import hashlib
import json
import pathlib
import sys

FORBIDDEN = (
    "api.audio.com", "audio.com/auth", "identity.audio.com", "sentry.io",
    "crashpad_handler", "updates.audacityteam.org", "api.audacityteam.org",
    "api.musescore.com", "musescore.com/oauth", "musehub.com",
)

def scan(root):
    files, findings = [], []
    if not root.is_dir():
        raise ValueError("Expected an unpacked application directory")
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            findings.append({"path": relative, "reason": "symbolic link"})
            continue
        if path.is_dir():
            continue
        digest = hashlib.sha256()
        matched = set()
        tail = b""
        with path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)
                window = (tail + chunk).lower()
                for marker in FORBIDDEN:
                    if any(marker.encode(encoding) in window for encoding in ("utf-8", "utf-16-le", "utf-16-be")):
                        matched.add(marker)
                tail = chunk[-256:]
        files.append({"path": relative, "size": path.stat().st_size, "sha256": digest.hexdigest()})
        findings.extend({"path": relative, "reason": marker} for marker in sorted(matched))
    if not files:
        raise ValueError("Application stage contains no regular files")
    return {"schema_version": 1, "files": files, "findings": findings, "passed": not findings}

if __name__ == "__main__":
    try:
        report = scan(pathlib.Path(sys.argv[1]).resolve(strict=True))
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["passed"] else 1)
    except (OSError, ValueError, IndexError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        raise SystemExit(1)
