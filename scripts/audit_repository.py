#!/usr/bin/env python
"""Fail when the repository contains common credentials or private machine traces."""

from __future__ import annotations

import base64
import gzip
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SELF = "scripts/audit_repository.py"
FORBIDDEN = {
    "WeChat/login token": re.compile(r"(?:^|[?&])token=\d+", re.I),
    "authorization header": re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.I),
    "cookie/session material": re.compile(r"(?:cookie|sessionid)\s*[:=]\s*\S+", re.I),
    "WeChat local account id": re.compile(r"wxid_[A-Za-z0-9_]+", re.I),
    "Windows user path": re.compile(r"C:" + r"\\Users\\" + r"[^\\\s]+", re.I),
    "private legacy work path": re.compile(r"D:" + r"[/\\]pythonPycharms[/\\]工具开发", re.I),
    "legacy-agent co-author trailer": re.compile(r"Co-Authored-By\s*:\s*legacy-agent", re.I),
    "legacy-provider co-author email": re.compile(r"noreply@legacy-provider\.com", re.I),
}


def run(*args: str) -> bytes:
    return subprocess.check_output(args, cwd=ROOT, stderr=subprocess.DEVNULL)


def scan(label: str, data: bytes) -> list[str]:
    text = data.decode("utf-8", "replace")
    return [f"{label}: {name}" for name, pattern in FORBIDDEN.items() if pattern.search(text)]


def main() -> int:
    findings: list[str] = []
    tracked = run("git", "ls-files", "-z").split(b"\0")
    for raw_path in tracked:
        if not raw_path:
            continue
        path = raw_path.decode("utf-8", "replace")
        if path == SELF:
            continue
        data = (ROOT / path).read_bytes()
        findings.extend(scan(path, data))
        if path.endswith(".cfhtml.gz.b64"):
            try:
                findings.extend(scan(path + " (decompressed)", gzip.decompress(base64.b64decode(data))))
            except Exception as exc:
                findings.append(f"{path}: template decode failed ({exc})")

    history = run("git", "log", "--all", "--format=%H%n%an <%ae>%n%B%x1e")
    findings.extend(scan("git history metadata", history))
    for line in history.decode("utf-8", "replace").splitlines():
        if "<" in line and ">" in line:
            email = line.rsplit("<", 1)[-1].split(">", 1)[0]
            if "@" in email and not email.endswith("users.noreply.github.com"):
                findings.append("git history metadata: author email is not a GitHub noreply address")
                break

    if findings:
        print("Repository safety audit: FAIL")
        for item in sorted(set(findings)):
            print("-", item)
        return 1
    print("Repository safety audit: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
