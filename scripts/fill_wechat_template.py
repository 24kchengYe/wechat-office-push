#!/usr/bin/env python
"""Fill a profile-specific WeChat paper template and optionally save a draft.

The script never publishes. It uses a frozen account template so concurrent
Codex tasks cannot corrupt the rich-text copy through the shared clipboard.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import gzip
import html
import json
import math
import re
import time
from pathlib import Path

import comtypes.client
import win32api
import win32clipboard
import win32con
import win32gui


ctypes.windll.user32.SetProcessDPIAware()


UIA_CONTROL_TYPE = 30003
UIA_NAME = 30005
UIA_AUTOMATION_ID = 30011
UIA_CLASS_NAME = 30012
UIA_BUTTON = 50000
UIA_EDIT = 50004
UIA_IMAGE = 50006
UIA_LIST_ITEM = 50007
TREE_DESCENDANTS = 4
INVOKE_PATTERN = 10000
VALUE_PATTERN = 10002
TEXT_PATTERN = 10014
SCROLL_ITEM_PATTERN = 10017


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def uia_client(hwnd: int):
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen import UIAutomationClient as UIA  # noqa: PLC0415

    automation = comtypes.client.CreateObject(
        "{FF48DBA4-60EF-4201-AA87-54103EEF594E}", interface=UIA.IUIAutomation
    )
    return UIA, automation, automation.ElementFromHandle(hwnd)


def find_all(automation, root, property_id: int, value):
    return root.FindAll(
        TREE_DESCENDANTS, automation.CreatePropertyCondition(property_id, value)
    )


def find_first(automation, root, property_id: int, value):
    return root.FindFirst(
        TREE_DESCENDANTS, automation.CreatePropertyCondition(property_id, value)
    )


def invoke(UIA, element) -> None:
    element.GetCurrentPattern(INVOKE_PATTERN).QueryInterface(
        UIA.IUIAutomationInvokePattern
    ).Invoke()


def scroll_into_view(UIA, element) -> None:
    try:
        element.GetCurrentPattern(SCROLL_ITEM_PATTERN).QueryInterface(
            UIA.IUIAutomationScrollItemPattern
        ).ScrollIntoView()
    except Exception:
        pass


def text_of(UIA, element) -> str:
    return (
        element.GetCurrentPattern(TEXT_PATTERN)
        .QueryInterface(UIA.IUIAutomationTextPattern)
        .DocumentRange.GetText(-1)
    )


def click_element(element, hwnd: int) -> None:
    activate_window(hwnd)
    rect = element.CurrentBoundingRectangle
    try:
        point, clickable = element.GetClickablePoint()
    except Exception:
        clickable = False
    x = point.x if clickable else (rect.left + rect.right) // 2
    y = point.y if clickable else (rect.top + rect.bottom) // 2
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(0.35)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
    time.sleep(0.25)


def activate_window(hwnd: int) -> None:
    # Windows Terminal/remote-desktop helpers can leave the pointer clipped;
    # release that constraint before moving to an embedded-browser control.
    ctypes.windll.user32.ClipCursor(None)
    left, top, right, _ = win32gui.GetWindowRect(hwnd)
    ctypes.windll.user32.SetCursorPos((left + right) // 2, top + 20)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
    time.sleep(0.3)


def chord(letter: str) -> None:
    key = ord(letter.upper())
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(key, 0, 0, 0)
    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(
        win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0
    )
    time.sleep(0.15)


def set_unicode_clipboard(value: str) -> None:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, value)
    finally:
        win32clipboard.CloseClipboard()


def cf_html(fragment: str) -> bytes:
    prefix = "<html><body><!--StartFragment-->"
    suffix = "<!--EndFragment--></body></html>"
    body = prefix + fragment + suffix
    header_template = (
        "Version:1.0\r\n"
        "StartHTML:{start_html:010d}\r\n"
        "EndHTML:{end_html:010d}\r\n"
        "StartFragment:{start_fragment:010d}\r\n"
        "EndFragment:{end_fragment:010d}\r\n"
    )
    dummy = header_template.format(
        start_html=0, end_html=0, start_fragment=0, end_fragment=0
    )
    start_html = len(dummy.encode("utf-8"))
    start_fragment = start_html + len(prefix.encode("utf-8"))
    end_fragment = start_fragment + len(fragment.encode("utf-8"))
    end_html = start_html + len(body.encode("utf-8"))
    header = header_template.format(
        start_html=start_html,
        end_html=end_html,
        start_fragment=start_fragment,
        end_fragment=end_fragment,
    )
    return (header + body).encode("utf-8")


def set_rich_clipboard(fragment: str, plain: str) -> None:
    html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(html_format, cf_html(fragment))
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, plain)
    finally:
        win32clipboard.CloseClipboard()


def recommendation_count(value: str) -> int:
    ascii_count = sum(ord(char) <= 127 for char in value)
    return len(value) - ascii_count + math.ceil(ascii_count / 2)


def recommendation(article: dict) -> str:
    en = article["title_en"]
    cn = article["title_cn"]
    candidates = [
        f"本期为大家推荐的内容为论文《{en}》（{cn}），发表在 Transactions in Urban Data, Science, and Technology 期刊，欢迎大家学习与交流。",
        f"本期为大家推荐的内容为论文《{en}》（{cn}），发表于TUS，欢迎大家学习与交流。",
        f"本期推荐论文《{en}》（{cn}），发表于TUS，欢迎大家学习与交流。",
        f"本期推荐论文《{en}》（{cn}），发表于TUS，欢迎学习与交流。",
    ]
    for value in candidates:
        if recommendation_count(value) <= 120:
            return value
    raise ValueError("platform recommendation exceeds 120 weighted characters")


def build_fragment(article_dir: Path, config: dict) -> str:
    asset = Path(__file__).resolve().parent.parent / config["template_cfhtml_asset"]
    raw = gzip.decompress(base64.b64decode(asset.read_text(encoding="utf-8"))).decode(
        "utf-8-sig"
    )
    match = re.search(r"<!--StartFragment-->([\s\S]*?)<!--EndFragment-->", raw)
    if not match:
        raise ValueError("frozen template has no CF_HTML fragment")
    fragment = match.group(1)
    article = load_json(article_dir / "article_source.json")
    corresponding = {item["name"] for item in article.get("corresponding_authors", [])}
    authors = ", ".join(
        item["name"] + ("*" if item["name"] in corresponding else "")
        for item in article["authors"]
    )
    replacements = {
        config["old"]["title_en"]: article["title_en"],
        config["old"]["title_cn"]: article["title_cn"],
        config["old"]["authors"]: authors,
        config["old"]["doi_url"]: "https://doi.org/" + article["doi"],
        config["old"]["guide_cn"]: article["guide_cn"],
        config["old"]["abstract_en"]: article["abstract_en"],
    }
    for old, new in replacements.items():
        if old not in fragment:
            raise ValueError(f"template source text missing: {old[:50]}")
        fragment = fragment.replace(old, html.escape(new, quote=False))

    images = []
    for name in article["image_files"]:
        path = article_dir / name
        images.append("data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode())
    image_config = config["paper_images"]
    if len(images) != image_config["expected_output_count"]:
        raise ValueError("unexpected number of paper images")
    token = re.escape(image_config["class_token"])
    pattern = re.compile(rf'<img\b(?=[^>]*\bclass="[^"]*\b{token}\b[^"]*")[^>]*>')
    index = 0

    def replace_image(match):
        nonlocal index
        if index >= len(images):
            raise ValueError("template has too many paper image elements")
        value = match.group(0)
        value = re.sub(r'(\bsrc=")[^"]*(")', rf"\g<1>{images[index]}\g<2>", value, count=1)
        value = re.sub(
            r'(\bdata-src=")[^"]*(")', rf"\g<1>{images[index]}\g<2>", value, count=1
        )
        index += 1
        return value

    fragment = pattern.sub(replace_image, fragment)
    if index != image_config["expected_source_count"]:
        raise ValueError(f"expected {image_config['expected_source_count']} template paper images, got {index}")
    return fragment


def fill(args) -> dict:
    article_dir = args.article_dir.resolve()
    article = load_json(article_dir / "article_source.json")
    profile = load_json(args.profile.resolve())
    skill_root = Path(__file__).resolve().parent.parent
    config = load_json(skill_root / profile["paper_template_config"])
    fragment = build_fragment(article_dir, config)

    UIA, automation, root = uia_client(args.hwnd)
    editors = find_all(automation, root, UIA_CLASS_NAME, "ProseMirror")
    found = [editors.GetElement(i) for i in range(editors.Length)]
    if len(found) < 2:
        raise RuntimeError("WeChat title/body editors were not found")
    found.sort(
        key=lambda element: element.CurrentBoundingRectangle.bottom
        - element.CurrentBoundingRectangle.top,
        reverse=True,
    )
    body, title = found[0], found[1]

    activate_window(args.hwnd)
    headline = f"{profile.get('headline_prefix', '论文推荐')} | {article['title_cn']}"
    click_element(title, args.hwnd)
    set_unicode_clipboard(headline)
    chord("a"); chord("v")

    click_element(body, args.hwnd)
    set_rich_clipboard(fragment, article["guide_cn"])
    chord("a"); chord("v")
    time.sleep(12)

    title_text = text_of(UIA, title)
    body_text = text_of(UIA, body)
    image_elements = find_all(automation, body, UIA_CONTROL_TYPE, UIA_IMAGE)
    body_images = 0
    paper_images = 0
    for index in range(image_elements.Length):
        class_name = image_elements.GetElement(index).CurrentClassName
        if "wxw-img" in class_name:
            body_images += 1
        if config["paper_images"]["class_token"] in class_name:
            paper_images += 1
    corresponding = {item["name"] for item in article.get("corresponding_authors", [])}
    author_line = ", ".join(
        item["name"] + ("*" if item["name"] in corresponding else "")
        for item in article["authors"]
    )
    checks = {
        "headline": headline == title_text.strip(),
        "english_title": article["title_en"] in body_text,
        "chinese_title": article["title_cn"] in body_text,
        "doi": article["doi"] in body_text,
        "authors": author_line in body_text,
        "guide": article["guide_cn"][:30] in body_text,
        "abstract": article["abstract_en"][:50] in body_text,
        "old_title_removed": config["old"]["title_cn"] not in body_text,
        "images": body_images,
        "paper_images": paper_images,
    }
    expected_images = config["paper_images"]["expected_total_images"]
    expected_paper_images = config["paper_images"]["expected_output_count"]
    boolean_keys = [key for key in checks if key not in {"images", "paper_images"}]
    if (
        not all(checks[key] for key in boolean_keys)
        or body_images != expected_images
        or paper_images != expected_paper_images
    ):
        raise RuntimeError("pre-save validation failed: " + json.dumps(checks, ensure_ascii=False))

    rec = recommendation(article)
    description = find_first(automation, root, UIA_AUTOMATION_ID, "js_description")
    if not description:
        raise RuntimeError("platform recommendation field not found")
    scroll_into_view(UIA, description); click_element(description, args.hwnd)
    set_unicode_clipboard(rec); chord("a"); chord("v")

    doi_url = "https://doi.org/" + article["doi"]
    url_area = find_first(automation, root, UIA_AUTOMATION_ID, "js_article_url_area")
    if not url_area:
        raise RuntimeError("original-link setting not found")
    scroll_into_view(UIA, url_area)
    texts = find_all(automation, url_area, UIA_CONTROL_TYPE, 50020)
    current_url = None
    for index in range(texts.Length):
        candidate = texts.GetElement(index)
        if candidate.CurrentName.startswith(("https://", "http://")):
            current_url = candidate
            break
    if not current_url:
        raise RuntimeError("current original link not found")
    if current_url.CurrentName != doi_url:
        click_element(automation.RawViewWalker.GetParentElement(current_url), args.hwnd)
        url_input = find_first(automation, root, UIA_NAME, "输入或粘贴原文链接")
        if not url_input:
            raise RuntimeError("original-link input did not open")
        url_input.GetCurrentPattern(VALUE_PATTERN).QueryInterface(
            UIA.IUIAutomationValuePattern
        ).SetValue(doi_url)
        confirm = find_first(automation, root, UIA_NAME, "确定")
        if not confirm:
            raise RuntimeError("original-link confirmation missing")
        invoke(UIA, confirm); time.sleep(0.7)

    # Confirming the link re-renders the settings panel; reacquire the root so
    # subsequent collection/save lookups do not use a stale accessibility tree.
    root = automation.ElementFromHandle(args.hwnd)

    collection = config.get("collection_name", "论文推荐")
    collection_area = None
    if collection:
        collection_area = find_first(automation, root, UIA_AUTOMATION_ID, "js_article_tags_area")
    if collection and not collection_area:
        labels = find_all(automation, root, UIA_NAME, "合集")
        for index in range(labels.Length):
            candidate = labels.GetElement(index)
            for _ in range(6):
                if not candidate:
                    break
                if candidate.CurrentAutomationId == "js_article_tags_area":
                    collection_area = candidate
                    break
                candidate = automation.RawViewWalker.GetParentElement(candidate)
            if collection_area:
                break
    if collection and not collection_area:
        raise RuntimeError("collection setting not found")
    if collection_area:
        scroll_into_view(UIA, collection_area)
    selected = (
        find_first(automation, collection_area, UIA_NAME, collection)
        if collection_area and collection
        else None
    )
    if collection and not selected:
        unassigned = find_first(automation, collection_area, UIA_NAME, "未添加")
        if not unassigned:
            raise RuntimeError("current collection state could not be determined")
        trigger = automation.RawViewWalker.GetParentElement(unassigned)
        trigger.GetCurrentPattern(10018).QueryInterface(
            UIA.IUIAutomationLegacyIAccessiblePattern
        ).DoDefaultAction()
        time.sleep(0.7)
        root = automation.ElementFromHandle(args.hwnd)
        collection_input = find_first(automation, root, UIA_NAME, "请选择合集")
        if not collection_input:
            raise RuntimeError("collection dialog did not open")
        click_element(collection_input, args.hwnd)
        set_unicode_clipboard(collection)
        chord("a"); chord("v")
        time.sleep(0.7)
        matches = find_all(automation, root, UIA_NAME, collection)
        option = None
        for index in range(matches.Length):
            candidate = matches.GetElement(index)
            if candidate.CurrentControlType == UIA_LIST_ITEM:
                option = candidate
                break
        if not option:
            raise RuntimeError(f"collection option not found: {collection}")
        invoke(UIA, option)
        time.sleep(0.3)
        confirm_collection = find_first(automation, root, UIA_NAME, "确认")
        if not confirm_collection:
            raise RuntimeError("collection confirmation missing")
        invoke(UIA, confirm_collection)
        time.sleep(0.7)
        root = automation.ElementFromHandle(args.hwnd)
        collection_area = find_first(
            automation, root, UIA_AUTOMATION_ID, "js_article_tags_area"
        )
        selected = (
            find_first(automation, collection_area, UIA_NAME, collection)
            if collection_area
            else None
        )
        if not selected:
            raise RuntimeError(f"collection validation failed: {collection}")

    saved = False
    if args.save_draft:
        save = find_first(automation, root, UIA_NAME, "保存为草稿")
        if not save:
            raise RuntimeError("Save as draft button not found")
        invoke(UIA, save); time.sleep(6); saved = True

    return {
        "profile_id": profile["profile_id"],
        "headline": headline,
        "doi": article["doi"],
        "checks": checks
        | {
            "platform_recommendation": rec,
            "platform_recommendation_count": recommendation_count(rec),
            "original_link": doi_url,
            "collection": collection,
        },
        "saved_as_draft": saved,
        "published": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article-dir", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--hwnd", type=int, required=True)
    parser.add_argument("--save-draft", action="store_true")
    args = parser.parse_args()
    print(json.dumps(fill(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
