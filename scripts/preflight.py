#!/usr/bin/env python
"""Validate a local installation without accessing or changing WeChat."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from pathlib import Path


BASE_MODULES = {
    "fitz": "PyMuPDF",
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "docx": "python-docx",
}
WINDOWS_MODULES = {"comtypes": "comtypes", "win32api": "pywin32"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--backend", action="store_true", help="also check Windows UI automation")
    parser.add_argument("--strict", action="store_true", help="treat local configuration warnings as errors")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []
    warnings: list[str] = []

    if sys.version_info < (3, 10):
        failures.append("Python 3.10 or newer is required")
    modules = dict(BASE_MODULES)
    if args.backend:
        if platform.system() != "Windows":
            failures.append("WeChat backend automation is Windows-only")
        modules.update(WINDOWS_MODULES)
    for module, package in modules.items():
        if importlib.util.find_spec(module) is None:
            failures.append(f"missing Python package: {package}")

    profile_path = args.profile.resolve()
    if not profile_path.is_file():
        failures.append(f"profile not found: {profile_path}")
        profile = {}
    else:
        profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    for field in ("profile_id", "account_name", "headline_prefix"):
        if not profile.get(field):
            failures.append(f"profile field is missing: {field}")
    if profile.get("show_editor") and not str(profile.get("default_editor", "")).strip():
        warnings.append("default_editor is empty; configure a profiles/local copy before rendering")
    if not str(profile.get("default_working_dir", "")).strip():
        warnings.append("default_working_dir is empty; user must supply an input/output path")

    template_config = profile.get("paper_template_config")
    if template_config and not (root / template_config).is_file():
        failures.append(f"paper template config not found: {template_config}")
    qrcode_source = profile.get("qrcode_source")
    if qrcode_source and not (root / qrcode_source).is_file():
        failures.append(f"QR-code asset not found: {qrcode_source}")

    status = "FAIL" if failures or (args.strict and warnings) else "OK"
    print(json.dumps({"status": status, "failures": failures, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
