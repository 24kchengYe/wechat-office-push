#!/usr/bin/env python
"""Maintain a DOI-keyed journal-to-WeChat publication ledger."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


GLOBAL_ALLOWED = {
    "journal_status": {"current_issue", "online_first", "archived"},
    "local_status": {"not_started", "generated", "verified"},
}

ACCOUNT_ALLOWED = {
    "draft_status": {"none", "saved", "needs_review"},
    "wechat_status": {"unknown", "not_found", "published"},
}

ALLOWED = {**GLOBAL_ALLOWED, **ACCOUNT_ALLOWED}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_doi(value: str) -> str:
    value = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value.strip()


def read_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def new_ledger(journal: str, catalog_url: str) -> dict:
    return {
        "schema_version": 2,
        "journal": journal,
        "catalog_url": catalog_url,
        "last_checked": now_iso(),
        "items": [],
    }


def empty_account_status() -> dict:
    return {
        "draft_status": "none",
        "draft_title": "",
        "wechat_status": "unknown",
        "publish_date": "",
        "article_url": "",
        "last_checked": "",
        "evidence": [],
    }


def migrate_ledger(ledger: dict) -> dict:
    """Upgrade schema-v1 single-account state to schema-v2 BCL state."""
    if int(ledger.get("schema_version", 1)) >= 2:
        return ledger
    account_fields = {
        "draft_status",
        "draft_title",
        "wechat_status",
        "publish_date",
        "article_url",
        "last_checked",
        "evidence",
    }
    for item in ledger.get("items", []):
        status = empty_account_status()
        for field in account_fields:
            if field in item:
                status[field] = item[field]
        item["accounts"] = {"bcl": status}
        for field in account_fields - {"last_checked"}:
            item.pop(field, None)
    ledger["schema_version"] = 2
    return ledger


def normalize_catalog(data) -> list[dict]:
    items = data.get("items", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("catalog must be a JSON list or an object with an items list")
    result = []
    for raw in items:
        doi = normalize_doi(str(raw.get("doi", "")))
        if not doi:
            raise ValueError("every catalog item must contain a DOI")
        result.append(
            {
                "doi": doi,
                "title_en": str(raw.get("title_en") or raw.get("title") or "").strip(),
                "issue_bucket": str(raw.get("issue_bucket", "")).strip(),
                "journal_status": str(raw.get("journal_status", "current_issue")).strip(),
            }
        )
    return result


def merge_catalog(ledger: dict, catalog_items: list[dict]) -> dict:
    indexed = {normalize_doi(item["doi"]): item for item in ledger.get("items", [])}
    stamp = now_iso()
    for source in catalog_items:
        doi = source["doi"]
        target = indexed.get(doi)
        if target is None:
            target = {
                "doi": doi,
                "title_en": "",
                "issue_bucket": "",
                "journal_status": "current_issue",
                "local_status": "not_started",
                "local_path": "",
                "accounts": {},
                "last_checked": stamp,
            }
            ledger.setdefault("items", []).append(target)
            indexed[doi] = target
        target.update(source)
        target["last_checked"] = stamp
    ledger["last_checked"] = stamp
    ledger["items"] = sorted(ledger["items"], key=lambda item: item["doi"])
    return ledger


def update_item(ledger: dict, args) -> dict:
    ledger = migrate_ledger(ledger)
    doi = normalize_doi(args.doi)
    item = next((x for x in ledger.get("items", []) if normalize_doi(x["doi"]) == doi), None)
    if item is None:
        raise ValueError(f"DOI not found in ledger: {doi}")
    for field in GLOBAL_ALLOWED:
        value = getattr(args, field)
        if value is not None:
            if value not in GLOBAL_ALLOWED[field]:
                raise ValueError(f"invalid {field}: {value}")
            item[field] = value
    if args.local_path is not None:
        item["local_path"] = args.local_path

    account = item.setdefault("accounts", {}).setdefault(args.account, empty_account_status())
    for field in ACCOUNT_ALLOWED:
        value = getattr(args, field)
        if value is not None:
            if value not in ACCOUNT_ALLOWED[field]:
                raise ValueError(f"invalid {field}: {value}")
            account[field] = value
    for field in ("draft_title", "publish_date", "article_url"):
        value = getattr(args, field)
        if value is not None:
            account[field] = value
    if args.evidence:
        account.setdefault("evidence", []).extend(args.evidence)
        account["evidence"] = list(dict.fromkeys(account["evidence"]))
    stamp = now_iso()
    account["last_checked"] = stamp
    item["last_checked"] = stamp
    ledger["last_checked"] = stamp
    return ledger


def cmd_sync(args) -> None:
    ledger_path = Path(args.ledger)
    if ledger_path.exists():
        ledger = migrate_ledger(read_json(ledger_path))
    else:
        ledger = new_ledger(args.journal, args.catalog_url)
    ledger = merge_catalog(ledger, normalize_catalog(read_json(Path(args.catalog))))
    write_json(ledger_path, ledger)
    print(f"Synced {len(ledger['items'])} items -> {ledger_path}")


def cmd_set(args) -> None:
    path = Path(args.ledger)
    ledger = update_item(read_json(path), args)
    write_json(path, ledger)
    print(f"Updated {normalize_doi(args.doi)} -> {path}")


def cmd_report(args) -> None:
    ledger = migrate_ledger(read_json(Path(args.ledger)))
    groups = {"published": [], "draft": [], "missing": [], "unknown": []}
    for item in ledger.get("items", []):
        status = item.get("accounts", {}).get(args.account, empty_account_status())
        if status.get("wechat_status") == "published":
            groups["published"].append(item)
        elif status.get("draft_status") in {"saved", "needs_review"}:
            groups["draft"].append(item)
        elif status.get("wechat_status") == "not_found":
            groups["missing"].append(item)
        else:
            groups["unknown"].append(item)
    output = {key: [{"doi": x["doi"], "title_en": x.get("title_en", "")} for x in value]
              for key, value in groups.items()}
    print(json.dumps(output, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="create/update a ledger from a catalog JSON file")
    sync.add_argument("--catalog", required=True)
    sync.add_argument("--ledger", required=True)
    sync.add_argument("--journal", default="Transactions in Urban Data, Science, and Technology")
    sync.add_argument("--catalog-url", default="https://sage.cnpereading.com/toc/tusa")
    sync.set_defaults(func=cmd_sync)

    setter = sub.add_parser("set", help="update status for one DOI")
    setter.add_argument("--ledger", required=True)
    setter.add_argument("--doi", required=True)
    setter.add_argument("--account", default="bcl", help="account profile id, e.g. bcl or tus")
    for field, choices in ALLOWED.items():
        setter.add_argument(f"--{field.replace('_', '-')}", dest=field, choices=sorted(choices))
    for field in ("local_path", "draft_title", "publish_date", "article_url"):
        setter.add_argument(f"--{field.replace('_', '-')}", dest=field)
    setter.add_argument("--evidence", action="append")
    setter.set_defaults(func=cmd_set)

    report = sub.add_parser("report", help="print a grouped publication-status report")
    report.add_argument("--ledger", required=True)
    report.add_argument("--account", default="bcl", help="account profile id")
    report.set_defaults(func=cmd_report)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
