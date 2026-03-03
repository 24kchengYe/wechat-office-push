---
name: wechat-article-push
description: "Generate WeChat public account (公众号) article/push content. Use this skill whenever the user mentions: 公众号推送, 论文推荐, paper recommendation, 写推送, 推文, 公众号文章, WeChat article, 推送论文, 做一个推送, 帮我推论文, 论文推送, 生成推文, 会议推荐, MOOC推送, 征文启事, 教研动态, or any task related to creating content for a WeChat public account. Currently supports '论文推荐' (paper recommendation) category."
---

# 公众号推送 Skill

为微信公众号生成推送内容，支持论文推荐、会议推荐、MOOC推送等多种类别。

## Supported Categories

Currently: **论文推荐** (Paper Recommendation)
Future: 会议推荐, MOOC慕课推送, 征文启事, 教研动态

## Dependencies

Before first use, ensure dependencies are installed:
```bash
pip install PyMuPDF requests
```

## Default Paths

- **默认工作目录**: `F:/BCL/公众号/论文推荐`
- Input: PDF files in the working directory (or user-specified path)
- Output: Markdown + images in subfolders within the working directory (or user-specified output path)

If the user does not specify paths, ask if they want to use the default or provide custom paths.

## Workflow: 论文推荐 (Paper Recommendation)

### Step 1: Determine Input

Ask the user for:
1. **Input path**: Folder containing paper PDFs (default: `F:/BCL/公众号/论文推荐`)
2. **Output path**: Where to save results (default: same as input, with subfolders per paper)

**责任编辑** defaults to **张业成**, no need to ask unless the user specifies otherwise.

### Step 2: Process Each PDF

For each `.pdf` file found in the input folder, run:

```bash
python "<skill_dir>/scripts/extract_pdf.py" "<pdf_path>" "<output_dir>/<paper_subfolder>" --max-images 5
```

Where `<skill_dir>` is: `C:/Users/ASUS/.claude/skills/bcl-paper-push`

This script will:
- Extract metadata: title, authors, abstract, journal, DOI
- Auto-select 4-5 key pages (title page + figure/table pages)
- Render those pages as JPG images
- Save `metadata.json` with all extracted info

### Step 3: Online Verification & Completion

**ALWAYS run this step** for every paper to verify and complete metadata extracted from PDF.
The script queries CrossRef and Semantic Scholar APIs to find authoritative metadata.

```bash
python "<skill_dir>/scripts/lookup_doi.py" --title "<paper_title>" [--doi "<doi_if_found>"] [--author "<first_author>"]
```

- If DOI was extracted from PDF: pass `--doi` for direct lookup (most accurate)
- If DOI was not found: pass `--title` to search by title
- The script returns: `title`, `authors`, `doi`, `doi_url`, `journal`, `year`

**Merge logic** — use the online result to fill in or correct PDF-extracted metadata:
- `authors`: **always prefer online result** (PDF extraction often misses names due to superscripts)
- `journal`: **always prefer online result** (PDF extraction often includes trailing noise)
- `doi`: use online result if PDF extraction missed it
- `title`: prefer PDF extraction (usually correct), but cross-check with online result
- `abstract`: keep from PDF extraction (online APIs rarely return abstracts)

If the online lookup also fails for a field, mark it as `[待补充]` and notify the user.

### Step 4: Generate Chinese Content

Using the verified metadata, Claude should:

1. **Translate the title** to Chinese (学术翻译风格，准确专业)
2. **Write the 导读 (introduction)**: A Chinese-language summary based on the English abstract. This should be:
   - 流畅自然的中文学术语言
   - 概述论文的研究目的、方法、主要发现
   - 长度约 150-300 字
3. **Final review**: compare all metadata against the title page image to catch any remaining errors

### Step 5: Assemble Markdown

For each paper, generate a Markdown file following this EXACT template structure:

```markdown
# 论文推荐 | [中文标题]

北京城市实验室BCL [YYYY年M月D日] [HH:MM]

---

**导读**本期为大家推荐的内容为论文《[English Title]》（[中文标题]），发表在 [Journal Name] 期刊，欢迎大家学习与交流。[中文导读段落]

---

## 论文相关

**题 目 ：** [English Title]

（[中文标题]）

**作者：** [Author1, Author2, Author3*]

**发表刊物：** [Journal Name]

**DOI：**

[https://doi.org/xx.xxxx/xxxxx]

---

## 摘 要 ABSTRACT

[Full English Abstract]

---

## 论文展示（部分）

![论文第1页](page_001.jpg)

![论文第X页](page_XXX.jpg)

[... more page images ...]

---

更多内容，请点击微信下方菜单即可查询。

请搜索微信号"Beijingcitylab"关注。

![BCL二维码](bcl_qrcode.jpeg)

Email：BeijingCityLab@gmail.com Emaillist: BCL@freelist.org

新浪微博：北京城市实验室BCL

微信号：beijingcitylab

网址: http://www.beijingcitylab.com

责任编辑：[编辑姓名]

[阅读原文](DOI_URL)
```

### Step 6: Copy Fixed Assets

Copy the BCL QR code image to each paper's output folder:
```bash
cp "<skill_dir>/assets/bcl_qrcode.jpeg" "<output_dir>/<paper_subfolder>/bcl_qrcode.jpeg"
```

### Step 7: Present Results

After processing all PDFs:
1. Show a summary table listing each paper with: title, authors, journal, DOI
2. Show the generated Markdown content for user review
3. Ask if any content needs adjustment (title translation, 导读内容, etc.)
4. Confirm the output files are saved

## Important Notes

- 导读的固定开头是："导读本期为大家推荐的内容为论文《...》（...），发表在 ... 期刊，欢迎大家学习与交流。" 不要改动这个格式。
- "题 目" 中间有一个全角空格，保持原样。
- "摘 要" 中间也有全角空格，保持原样。
- 通讯作者在姓名后加 `*` 标记。
- DOI 链接应为完整的 https://doi.org/... 格式。
- 日期格式为：YYYY年M月D日（如 2025年3月12日），时间格式为 HH:MM。
- 使用当天日期和当前时间（约整到分钟）作为默认发布时间。
- 论文展示图片目标 4-5 张，优先选择标题页和含图表的页面。
- 固定尾部内容不要修改，除了"责任编辑"需要填入用户提供的编辑姓名。
- 责任编辑默认填写"张业成"，用户指定其他人时才修改。

## Error Handling

- If PyMuPDF is not installed: prompt `pip install PyMuPDF`
- If no PDFs found in input folder: inform user and ask for correct path
- If metadata extraction fails for a field: mark as `[待补充]` and ask user to manually provide
- If DOI lookup fails: mark DOI as `[待查找]` and remind user to manually check
- If abstract extraction fails: try reading it from the first 2 pages of the PDF more carefully

## Example Usage

User: "帮我做一个论文推送"
→ Trigger this skill, ask for input path and editor name, process PDFs, generate Markdown

User: "推送一下 F:/papers/ 里面的论文"
→ Use F:/papers/ as input, process all PDFs, generate output

User: "论文推荐，pdf在桌面上"
→ Use Desktop path, find PDFs, process and generate
