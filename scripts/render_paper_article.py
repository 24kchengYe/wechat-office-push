#!/usr/bin/env python
"""Render verified paper metadata into account-specific WeChat artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def author_display(source: dict) -> tuple[str, list[str]]:
    corresponding = {item["name"] for item in source.get("corresponding_authors", [])}
    plain = [item["name"] if isinstance(item, dict) else str(item) for item in source["authors"]]
    marked = [f"{name}*" if name in corresponding else name for name in plain]
    return ", ".join(marked), plain


def render(source: dict, profile: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    title_cn = source["title_cn"]
    title_en = source["title_en"]
    journal = source.get("journal", "Transactions in Urban Data, Science, and Technology")
    doi = source["doi"].removeprefix("https://doi.org/")
    doi_url = f"https://doi.org/{doi}"
    display_authors, plain_authors = author_display(source)
    image_files = source["image_files"]
    date = source["date"]
    time = source["time"]
    guide_paragraph = source["guide_cn"].strip()
    if source.get("opening_cn"):
        opening = source["opening_cn"].strip()
    elif source.get("source_language") == "zh":
        opening = (
            f"本期为大家推荐的内容为论文《{title_cn}》（{title_en}），"
            f"发表在 {journal} 期刊，欢迎大家学习与交流。"
        )
    else:
        opening = (
            f"本期为大家推荐的内容为论文《{title_en}》（{title_cn}），"
            f"发表在 {journal} 期刊，欢迎大家学习与交流。"
        )
    guide = opening + guide_paragraph
    abstract_display = source.get("abstract_display")
    if not abstract_display:
        abstract_display = (
            source.get("abstract_cn")
            if source.get("source_language") == "zh"
            else source.get("abstract_en")
        )
    if not abstract_display:
        abstract_display = source.get("abstract_en", "")
    image_md = "\n\n".join(
        f"![论文第{int(name[5:8])}页]({name})" for name in image_files
    )
    image_txt = "\n\n".join(f"【配图：{name}】" for name in image_files)
    footer = "\n\n".join(profile.get("footer_text", []))
    footer_md = footer
    qrcode_filename = profile.get("qrcode_filename", "")
    if qrcode_filename:
        footer_md = footer_md.replace(
            f"【配图：{qrcode_filename}】",
            f"![{profile.get('account_short', profile['account_name'])}二维码]({qrcode_filename})",
        )
    headline_prefix = profile.get("headline_prefix", "论文推荐")
    editor_line = ""
    if profile.get("show_editor", bool(profile.get("default_editor"))):
        editor_line = f"\n\n责任编辑：{profile['default_editor']}"

    md = f"""# {headline_prefix} | {title_cn}

{profile["account_name"]} {date} {time}

---

**导读**{guide}

---

## 论文相关

**题 目 ：** {title_en}

（{title_cn}）

**作者：** {display_authors}

**发表刊物：** {journal}

**DOI：**

{doi_url}

---

## 摘 要 ABSTRACT

{abstract_display}

---

## 论文展示（部分）

{image_md}

---

{footer_md}{editor_line}

[阅读原文]({doi_url})
"""

    txt = f"""{headline_prefix} | {title_cn}

{profile["account_name"]} {date} {time}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【导读】

{opening}

{guide_paragraph}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【论文相关】

题 目 ：{title_en}

（{title_cn}）

作者：{display_authors}

发表刊物：{journal}

DOI：{doi_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【摘 要 ABSTRACT】

{abstract_display}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【论文展示（部分）】

{image_txt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{footer}{editor_line}

阅读原文：{doi_url}
"""

    corresponding = source.get("corresponding_authors", [])
    article = {
        "type": "论文推荐",
        "title_cn": title_cn,
        "title_en": title_en,
        "headline": f"{headline_prefix} | {title_cn}",
        "account": profile["account_name"],
        "profile_id": profile.get("profile_id", ""),
        "date": date,
        "time": time,
        "导读": guide,
        "论文相关": {
            "题目_en": title_en,
            "题目_cn": title_cn,
            "作者": display_authors,
            "作者列表": plain_authors,
            "通讯作者": "、".join(item["name"] for item in corresponding),
            "通讯作者邮箱": "；".join(item.get("email", "") for item in corresponding),
            "通讯作者单位": "；".join(item.get("affiliation", "") for item in corresponding),
            "发表刊物": journal,
            "DOI": doi,
            "DOI链接": doi_url,
            "发表年份": source.get("year", 0),
            "备注": source.get("note", ""),
        },
        "摘要": abstract_display,
        "推荐语": source.get("recommendation", opening),
        "论文展示": image_files,
        "footer": {
            "qrcode": qrcode_filename,
            "account_intro": profile.get("account_intro", ""),
            "contact": profile.get("contact", {}),
            "责任编辑": profile.get("default_editor", "") if profile.get("show_editor", True) else "",
            "阅读原文": doi_url,
        },
    }

    write_text(output_dir / "推文.md", md)
    write_text(output_dir / "推文.txt", txt)
    write_text(output_dir / "article.json", json.dumps(article, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--qrcode-source", type=Path)
    args = parser.parse_args()

    source = load_json(args.source)
    profile = load_json(args.profile)
    render(source, profile, args.output_dir)
    if args.qrcode_source and profile.get("qrcode_filename"):
        shutil.copy2(args.qrcode_source, args.output_dir / profile["qrcode_filename"])
    print(f"Rendered 推文.md, 推文.txt, article.json -> {args.output_dir}")


if __name__ == "__main__":
    main()
