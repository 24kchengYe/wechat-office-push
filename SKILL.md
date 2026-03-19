---
name: wechat-office-push
description: "Generate WeChat public account (公众号) articles from academic PDFs and call-for-papers pages. Supports multiple content types: 论文推荐 (paper recommendation), 征文启事 (call for papers), and more. Use this skill whenever the user mentions: call for papers, CFP推送, 征文推送, 论文推荐, 征文启事, 公众号推送, 写推送, 推文, 公众号文章, WeChat article, 推送论文, 做一个推送, 帮我推论文, 论文推送, 生成推文, 会议推荐, MOOC推送, 教研动态, or any task related to creating content for a WeChat public account."
---

# 公众号推送 Skill

为微信公众号自动生成推送内容（论文推荐、征文启事等）。

## Supported Categories

1. **论文推荐** — 从学术论文 PDF 生成推荐推文
2. **征文启事** — 从会议/期刊征文信息生成 Call for Papers 推文
3. 会议推荐 *(planned)*
4. MOOC慕课推送 *(planned)*
5. 教研动态 *(planned)*

根据用户意图自动选择对应工作流。如果用户提到"征文"、"call for papers"、"CFP"，走征文启事流程；否则默认走论文推荐流程。

## Scripts & Assets

- **Scripts directory**: `~/.claude/skills/wechat-office-push/scripts/`
  - `extract_pdf.py` -- Extracts text, metadata, and key page images from academic paper PDFs
  - `lookup_doi.py` -- Looks up DOI metadata via CrossRef and Semantic Scholar APIs
- **Assets directory**: `~/.claude/skills/wechat-office-push/assets/`
  - `qrcode.jpeg` -- WeChat QR code (used in article footer)
  - `logo.png` -- Account logo

## Dependencies

Before first use, ensure dependencies are installed:
```bash
pip install PyMuPDF requests
```

## Default Paths

- **论文推荐默认目录**: 用户指定或当前工作目录
- **征文启事默认目录**: 用户指定或当前工作目录
- 论文推荐 Input: PDF files in the working directory (or user-specified path)
- 征文启事 Input: 用户提供的官网链接 (URL)
- Output: **JSON 文件** (`article.json`) + images in subfolders

**责任编辑**: 首次使用时询问用户，后续复用。

---

## Workflow 1: 论文推荐 (Paper Recommendation)

### Step 1: Determine Input

1. **Input path**: Folder containing paper PDFs (user-specified or current working directory)
2. **Output path**: Where to save results (default: same as input, with subfolders per paper)

### Step 2: Extract PDF Content

For each `.pdf` file found in the input folder, run:

```bash
python "~/.claude/skills/wechat-office-push/scripts/extract_pdf.py" "<pdf_path>" "<output_dir>/<paper_subfolder>" --max-images 5
```

This extracts:
- Metadata: title, authors, abstract, journal, DOI
- 4-5 key page images (title page + figure/table pages) rendered as JPG
- Saves `metadata.json` with all extracted info

### Step 3: Online DOI Verification & Completion

**ALWAYS run this step** for every paper to verify and complete metadata.

```bash
python "~/.claude/skills/wechat-office-push/scripts/lookup_doi.py" --title "<paper_title>" [--doi "<doi_if_found>"] [--author "<first_author>"]
```

**Merge logic** -- use online results to fill in or correct PDF-extracted metadata:
- `authors`: **always prefer online result** (PDF extraction often misses names due to superscripts)
- `corresponding_authors`: combine sources -- CrossRef may identify corresponding authors via email, and `extract_pdf.py` extracts from PDF text
- `journal`: **always prefer online result** (PDF extraction often includes trailing noise)
- `doi`: use online result if PDF extraction missed it
- `title`: prefer PDF extraction, but cross-check with online result
- `abstract`: keep from PDF extraction (online APIs rarely return abstracts)

If a field cannot be resolved, mark it as `[待补充]` and notify the user.

**Corresponding author identification** -- determine through:
1. `corresponding_authors` from online lookup
2. `corresponding_author` from `metadata.json`
3. Visual check of title page image for `*` markers or "Corresponding author" footnotes
4. If still unclear, mark as `[通讯作者待确认]` and ask the user

### Step 4: Generate Chinese Content

1. **Translate the title** to Chinese (学术翻译风格，准确专业)
2. **Write the 导读**: Chinese summary based on the English abstract
   - 流畅自然的中文学术语言
   - 概述研究目的、方法、主要发现
   - 约 150-300 字
3. **Mark corresponding author**: Add `*` after the corresponding author's name in the author list
4. **Final review**: compare all metadata against the title page image

### Step 5: Assemble JSON

Generate a JSON file `article.json` in the paper's output folder, following this structure:

```json
{
  "type": "论文推荐",
  "title": "论文推荐 | [中文标题]",
  "account": "[公众号名称]",
  "date": "YYYY年M月D日",
  "time": "HH:MM",
  "导读": "本期为大家推荐的内容为论文《[English Title]》（[中文标题]），发表在 [Journal Name] 期刊，欢迎大家学习与交流。[中文导读段落]",
  "论文相关": {
    "题目_en": "[English Title]",
    "题目_cn": "[中文标题]",
    "作者": "[Author1, Author2, Author3*]",
    "发表刊物": "[Journal Name]",
    "DOI": "https://doi.org/xx.xxxx/xxxxx"
  },
  "摘要": "[Full English Abstract]",
  "论文展示": ["page_001.jpg", "page_002.jpg", "page_003.jpg"],
  "footer": {
    "qrcode": "qrcode.jpeg",
    "责任编辑": "[编辑姓名]",
    "阅读原文": "https://doi.org/xx.xxxx/xxxxx"
  }
}
```

### Step 6: Copy Fixed Assets

```bash
cp "~/.claude/skills/wechat-office-push/assets/qrcode.jpeg" "<output_dir>/<paper_subfolder>/qrcode.jpeg"
cp "~/.claude/skills/wechat-office-push/assets/logo.png" "<output_dir>/<paper_subfolder>/logo.png"
```

### Step 7: Present Results

After processing all PDFs:
1. Show a summary table: title, authors, journal, DOI for each paper
2. Show the generated JSON content for user review
3. Ask if any content needs adjustment (title translation, 导读, etc.)
4. Confirm output files are saved

---

## Workflow 2: 征文启事 (Call for Papers)

### 输入与触发

当用户提到"征文"、"call for papers"、"CFP"时走此流程。

- **输入**: 用户提供的官网链接（期刊/会议征文页面 URL）
- **输出**: JSON 文件 + 相关图片，保存到 `[用户指定路径]/征文启事/[专刊简称]/`
- **责任编辑**: 首次使用时询问用户，后续复用

### CFP Step 1: 获取征文信息

使用 WebFetch 或浏览器工具访问用户提供的 URL，提取以下关键信息：

- **专刊/会议名称** (英文 + 中文翻译)
- **期刊名称** (Journal Name)
- **选题依据 / Rationale** — 为什么这个专刊重要
- **主题范围 / Scope of Topics** — 征文涵盖哪些方向
- **投稿指南 / Guidelines** — 稿件要求（字数、格式、投稿方式等）
- **时间表 / Timeline** — 截稿日期、审稿周期、出版日期等
- **客座编辑 / Guest Editors** — 姓名、单位、邮箱
- **相关链接** — 投稿入口、期刊主页等

如果页面信息不完整，标记为 `[待补充]` 并提示用户。

### CFP Step 2: 生成双语内容

将英文征文信息翻译为中文，保持学术准确性：

1. **专刊名称翻译**: 简洁专业的中文标题
2. **各章节双语呈现**: 每段先英文原文，后中文翻译
3. **翻译风格**: 学术正式，术语准确，不过度意译
4. **导读段落**: 用中文概述这个征文启事的重要性、主题、截稿日期等关键信息（150-250字）

### CFP Step 3: 组装 JSON

生成 `article.json` 文件，结构如下：

```json
{
  "type": "征文启事",
  "title": "征文启事 | [期刊简称]专刊《[专刊中文名称]》等你来",
  "subtitle": "Call for papers",
  "account": "[公众号名称]",
  "date": "YYYY年M月D日",
  "time": "HH:MM",
  "导读": "本期为大家推介的是期刊《[期刊中文名]》（[期刊英文名]）专刊《[专刊中文名]》（[专刊英文名]）的征文启事，包含Rationale（选题依据）、The scope of Topics（主题范围）、Guidelines（投稿指南）、Timeline（时间表）等内容。欢迎您的咨询、建议与投稿！",
  "sections": [
    {
      "heading": "Rationale(选题依据)",
      "content_en": "[英文 Rationale 原文]",
      "content_cn": "[中文翻译]"
    },
    {
      "heading": "The scope of Topics（主题范围）",
      "content_en": "[英文 Scope 说明 + topic 列表]",
      "content_cn": "[中文翻译]",
      "topics": ["topic1", "topic2", "..."]
    },
    {
      "heading": "Guidelines(投稿指南)",
      "content_en": "[英文 Guidelines 原文，含投稿链接]",
      "content_cn": "请依据网站要求提交完整论文，并在cover letter中注明向专刊《[专刊中文名]》投稿。"
    },
    {
      "heading": "Timeline(时间表)",
      "content_en": "Full paper submission: [date]\nOnline Publication: On acceptance\nSpecial Issue publication: [year]",
      "content_cn": ""
    },
    {
      "heading": "Guest editors(客座编辑)",
      "intro_en": "You are also encouraged to contact the guest editors to discuss the issues related to the submission:",
      "intro_cn": "如有任何投稿相关问题，欢迎联系本特刊客座编辑进行咨询：",
      "editors": [
        {
          "name": "[Name]",
          "email": "[email]",
          "affiliation": "[University/Institute, Country]"
        }
      ]
    }
  ],
  "links": {
    "专刊链接": "[CFP page URL]",
    "期刊主页链接": "[journal homepage URL]",
    "投稿系统": "[submission system URL]"
  },
  "footer": {
    "qrcode": "qrcode.jpeg",
    "责任编辑": "[编辑姓名]",
    "contact": "[用户自定义联系方式]"
  }
}
```

**章节标题格式说明**: heading 字段用 `[ heading ]` 方括号包裹输出，英文名后跟中文括号。如 `[ Rationale(选题依据) ]`。

### CFP Step 4: 复制固定资源

```bash
cp "~/.claude/skills/wechat-office-push/assets/qrcode.jpeg" "<output_dir>/qrcode.jpeg"
cp "~/.claude/skills/wechat-office-push/assets/logo.png" "<output_dir>/logo.png"
```

### CFP Step 5: 展示结果

1. 展示生成的完整 JSON 内容
2. 检查是否有 `[待补充]` 字段，提醒用户
3. 询问是否需要调整翻译、导读或其他内容
4. 确认文件已保存

### 征文启事格式说明

- 标题格式固定为 "征文启事 | [期刊简称]专刊《[中文名称]》等你来"
- 导读固定格式："本期为大家推介的是期刊《期刊中文名》（期刊英文名）专刊《专刊中文名》（专刊英文名）的征文启事，包含Rationale（选题依据）、The scope of Topics（主题范围）、Guidelines（投稿指南）、Timeline（时间表）等内容。欢迎您的咨询、建议与投稿！"
- 章节正文：英文原文在前，中文翻译紧跟其后
- Guest editors 列出完整信息（姓名、单位、邮箱）
- footer 包含公众号联系信息（由用户配置）
- "阅读原文"链接指向期刊主页（不是 DOI）

---

## Important Notes

- 公众号名称由用户配置，首次使用时询问，后续复用
- 论文推荐导读固定开头："本期为大家推荐的内容为论文《...》（...），发表在 ... 期刊，欢迎大家学习与交流。" 不要改动此格式
- "题 目" 中间有一个全角空格，保持原样
- "摘 要" 中间也有全角空格，保持原样
- 通讯作者在姓名后加 `*` 标记
- DOI 链接应为完整的 https://doi.org/... 格式
- 日期格式为：YYYY年M月D日（如 2025年3月12日），时间格式为 HH:MM
- 使用当天日期和当前时间（约整到分钟）作为默认发布时间
- 论文展示图片目标 4-5 张，优先选择标题页和含图表的页面
- 责任编辑首次使用时询问用户，后续复用

## Error Handling

- If PyMuPDF is not installed: prompt `pip install PyMuPDF`
- If no PDFs found in input folder: inform user and ask for correct path
- If metadata extraction fails for a field: mark as `[待补充]` and ask user
- If DOI lookup fails: mark DOI as `[待查找]` and remind user to manually check
- If abstract extraction fails: try reading from the first 2 pages more carefully

## Example Usage

User: "帮我推一篇论文"
--> 论文推荐流程, ask user for input path or use current working directory, process PDFs

User: "论文推荐，pdf在桌面上"
--> Use Desktop path, find PDFs, process and generate

User: "推送 F:/papers/xxx.pdf 到公众号"
--> Use specified path, process the PDF, generate output

User: "征文启事，链接是 https://www.journals.elsevier.com/xxx"
--> 征文启事流程, 访问链接，提取征文信息，生成双语 JSON

User: "帮我推一个CFP https://xxx.com/call-for-papers"
--> 同上

User: "征文推送，这个期刊在征稿 [URL]"
--> 同上
