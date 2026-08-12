#!/usr/bin/env python
"""Fail when the repository contains common credentials or private machine traces."""

from __future__ import annotations

import base64
import gzip
import io
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
    "co-author trailer": re.compile(r"Co-Authored-By\s*:", re.I),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    "GitHub access token": re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "API secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "disallowed legacy agent name": re.compile("".join(map(chr, [99, 108, 97, 117, 100, 101])), re.I),
    "disallowed legacy provider name": re.compile(
        "".join(map(chr, [97, 110, 116, 104, 114, 111, 112, 105, 99])), re.I
    ),
}


def run(*args: str) -> bytes:
    return subprocess.check_output(args, cwd=ROOT, stderr=subprocess.DEVNULL)


def scan(label: str, data: bytes) -> list[str]:
    text = data.decode("utf-8", "replace")
    return [f"{label}: {name}" for name, pattern in FORBIDDEN.items() if pattern.search(text)]


def historical_blobs() -> list[tuple[str, str, bytes]]:
    """Return reachable Git blobs with one batched Git process per phase."""

    object_paths: dict[str, str] = {}
    for entry in run("git", "rev-list", "--objects", "--all").decode("utf-8", "replace").splitlines():
        object_id, _, path = entry.partition(" ")
        if path and path != SELF:
            object_paths.setdefault(object_id, path)

    request = ("\n".join(object_paths) + "\n").encode()
    checked = subprocess.check_output(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        cwd=ROOT,
        input=request,
    ).decode("ascii", "replace")
    blob_ids = [line.split()[0] for line in checked.splitlines() if " blob " in line]
    if not blob_ids:
        return []

    payload = subprocess.check_output(
        ["git", "cat-file", "--batch"],
        cwd=ROOT,
        input=("\n".join(blob_ids) + "\n").encode(),
    )
    stream = io.BytesIO(payload)
    blobs: list[tuple[str, str, bytes]] = []
    for expected_id in blob_ids:
        header = stream.readline().decode("ascii", "replace").strip().split()
        if len(header) != 3 or header[1] != "blob":
            raise RuntimeError(f"unexpected git cat-file response for {expected_id}")
        size = int(header[2])
        data = stream.read(size)
        stream.read(1)  # trailing newline inserted by git cat-file --batch
        blobs.append((expected_id, object_paths[expected_id], data))
    return blobs


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

    # A clean working tree is not sufficient for a public repository: secrets
    # removed in a later commit remain downloadable from earlier Git blobs.
    # Scan every unique historical blob, including decompressed rich-text
    # templates, while excluding this scanner because it contains the patterns
    # by definition.
    for object_id, path, data in historical_blobs():
        label = f"git history {path}@{object_id[:12]}"
        findings.extend(scan(label, data))
        if path.endswith(".cfhtml.gz.b64"):
            try:
                findings.extend(scan(label + " (decompressed)", gzip.decompress(base64.b64decode(data))))
            except Exception as exc:
                findings.append(f"{label}: template decode failed ({exc})")

    if findings:
        print("Repository safety audit: FAIL")
        for item in sorted(set(findings)):
            print("-", item)
        return 1
    print("Repository safety audit: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
