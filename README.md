# wechat-office-push — BCL / TUS 公众号论文推送 Skill

> **为微信公众号自动生成推送内容，支持论文推荐、征文启事等多种类别。**

这是供 BCL / TUS 公众号负责人传承使用的私有工作流。当前支持三类论文分流：TUS 期刊论文同时生成 BCL + TUS 两个账号草稿；有完整整理稿的组内重要论文只生成 BCL 长篇“团队研究”草稿；只有 PDF 的组内普通论文只生成 BCL 正常“论文推荐”草稿。同一篇论文只维护一份经核验事实源，BCL 论文推送选择“论文推荐”合集，TUS 自有公众号不选择合集。所有自动填充脚本都不会发布文章。

> 仓库默认保持 **Private**。交接给下一位负责人时使用 GitHub collaborator；完整步骤见 [HANDOFF.md](HANDOFF.md)。

除常规 TUS 论文短版外，还支持从完整 Word 稿生成 BCL 长篇“团队研究”版式：自动识别摘要、方法、结果与讨论、研究意义以及 5 张图的 Caption 顺序，并保留 BCL 通用页尾。

## 功能

### 论文推荐

将论文 PDF 一键转换为格式规范的公众号推文（JSON + 图片），包含中文翻译、元数据提取、关键页面截图、DOI 联网验证。

```
输入: 论文PDF文件夹/
        ├── paper1.pdf
        ├── paper2.pdf
        └── paper3.pdf

输出: output/
        ├── paper1/
        │   ├── article.json      ← 结构化推文数据
        │   ├── page_001.jpg      ← 论文关键页截图
        │   ├── page_004.jpg
        │   ├── qrcode.jpeg       ← 公众号二维码
        │   └── metadata.json     ← 提取的元数据
        ├── paper2/
        └── paper3/
```

### 征文启事 (Call for Papers)

从期刊/会议征文页面 URL 自动生成双语征文启事推文。

```
输入: 征文启事官网链接 (URL)

输出: output/[专刊简称]/
        ├── article.json      ← 结构化推文数据（含双语内容）
        ├── article.md        ← 排版好的推文 Markdown
        ├── qrcode.jpeg       ← 公众号二维码
        └── logo.png          ← 公众号 Logo
```

### 自动化流程

**论文推荐：**

| 步骤 | 内容 |
|------|------|
| 1 | 扫描文件夹中的 PDF |
| 2 | 提取标题、作者、摘要、期刊、DOI |
| 3 | **联网验证补全**（CrossRef + Semantic Scholar API），修正作者缺失、期刊名噪音等 |
| 4 | 自动选择 4-5 张关键页面（标题页 + 图表页）截图 |
| 5 | AI Agent 翻译标题和摘要为中文，撰写导读 |
| 6 | 生成 JSON 结构化推文 |

**征文启事：**

| 步骤 | 内容 |
|------|------|
| 1 | 访问用户提供的征文页面 URL |
| 2 | 提取 Rationale、Scope、Guidelines、Timeline、Guest Editors |
| 3 | 生成双语内容（英文原文 + 中文翻译） |
| 4 | 按模板组装 JSON + Markdown 推文 |

### 支持的推送类别

- ✅ **论文推荐** (Paper Recommendation)
- ✅ **BCL + TUS 双账号独立草稿**
- ✅ **BCL 长篇团队研究 Word 模板**
- ✅ **征文启事** (Call for Papers)
- 📋 会议推荐 — 规划中
- 📋 MOOC 慕课推送 — 规划中
- 📋 教研动态 — 规划中

## 使用方式

在 Codex、legacy-agent Code 或其它支持 Skill 的 AI Agent 中直接说：

```
# 论文推荐
帮我做一个论文推送
推送一下 F:/papers/ 里面的论文
论文推荐，pdf在桌面上

# 征文启事
征文启事，链接是 https://journals.sagepub.com/page/tus/calls-for-papers
帮我推一个CFP https://xxx.com/call-for-papers
征文推送，这个期刊在征稿 [URL]
```

### 默认路径

- 论文推荐：用户指定路径或当前工作目录
- 征文启事：用户指定路径或当前工作目录

## 安装

### GitHub 私有仓库安装（推荐）

先由管理员添加 collaborator，再克隆：

```powershell
gh repo clone 24kchengYe/wechat-office-push "$env:USERPROFILE\.codex\skills\wechat-office-push"
cd "$env:USERPROFILE\.codex\skills\wechat-office-push"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 从 Skills CLI（仅在仓库可访问时）

```bash
npx skills add 24kchengYe/wechat-office-push
```

### 手动安装

```bash
# Codex, macOS / Linux
git clone https://github.com/24kchengYe/wechat-office-push.git ~/.codex/skills/wechat-office-push

# Codex, Windows
git clone https://github.com/24kchengYe/wechat-office-push.git %USERPROFILE%\.codex\skills\wechat-office-push

# legacy-agent Code 也可克隆到 ~/.legacy-agent/skills/wechat-office-push
```

### 依赖

```bash
python -m pip install -r requirements.txt
```

Python 要求为 3.10+，推荐 3.11。PDF 提取和本地渲染可跨平台运行；公众号后台自动填充依赖 Windows UI Automation，因此仅支持 Windows。

### 首次配置与预检

不要直接把个人姓名和本机路径写进跟踪的基础 profile：

```powershell
New-Item -ItemType Directory -Force profiles\local | Out-Null
Copy-Item profiles\bcl.json profiles\local\bcl.json
# 编辑 profiles/local/bcl.json，填写当前责任编辑与工作目录
python scripts\preflight.py --profile profiles\local\bcl.json --backend --strict
```

`profiles/local/` 被 Git 忽略。公众号登录必须由负责人现场扫码，仓库不保存密码、Cookie 或后台 token。

## 文件结构

```
wechat-office-push/
├── SKILL.md              ← Skill 定义（触发词、工作流、模板）
├── README.md
├── scripts/
│   ├── extract_pdf.py    ← PDF 元信息提取 + 关键页面截图
│   ├── lookup_doi.py     ← CrossRef & Semantic Scholar 元数据验证
│   ├── preflight.py      ← 安装、profile 与后台依赖预检
│   └── audit_repository.py ← 当前文件与 Git 历史隐私审计
├── assets/
│   ├── qrcode.jpeg       ← 公众号二维码
│   └── logo.png          ← 公众号 Logo
├── profiles/
│   ├── bcl.json           ← BCL 账号配置
│   └── tus.json           ← TUS 账号配置（不选合集）
├── HANDOFF.md             ← 新负责人完整交接步骤
├── SECURITY.md            ← 隐私与凭据边界
├── requirements.txt
├── tests/
└── templates/
    ├── paper_template.md  ← Markdown 推文模板
    ├── tus_paper_template.cfhtml.gz.b64
    └── bcl_team_research_template.cfhtml.gz.b64
```

## 输出格式

### 论文推荐 JSON 结构

```json
{
  "type": "论文推荐",
  "title": "论文推荐 | [中文标题]",
  "导读": "...",
  "论文相关": { "题目_en": "...", "题目_cn": "...", "作者": "...", "发表刊物": "...", "DOI": "..." },
  "摘要": "...",
  "论文展示": ["page_001.jpg", "..."],
  "footer": { "责任编辑": "[编辑姓名]", "阅读原文": "..." }
}
```

### 征文启事 JSON 结构

```json
{
  "type": "征文启事",
  "title": "征文启事 | [期刊简称]专刊《[中文名]》等你来",
  "导读": "...",
  "sections": [
    { "heading": "Rationale(选题依据)", "content_en": "...", "content_cn": "..." },
    { "heading": "The scope of Topics（主题范围）", "content_en": "...", "content_cn": "...", "topics": ["..."] },
    { "heading": "Guidelines(投稿指南)", "content_en": "...", "content_cn": "..." },
    { "heading": "Timeline(时间表)", "content_en": "...", "content_cn": "..." },
    { "heading": "Guest editors(客座编辑)", "editors": [{ "name": "...", "affiliation": "...", "email": "..." }] }
  ],
  "footer": { "责任编辑": "[编辑姓名]", "contact": "[用户自定义联系方式]" }
}
```

## 需求

- Codex、legacy-agent Code 或其它支持 Skill 的 AI Agent
- Python 3.10+（推荐 3.11）
- 依赖见 `requirements.txt`
- 自动录入公众号后台：Windows + 人工扫码登录

## 交接与隐私

- 交接入口：[HANDOFF.md](HANDOFF.md)
- 隐私与泄漏处理：[SECURITY.md](SECURITY.md)
- 提交或共享前运行：`python scripts/audit_repository.py`
- `output/`、论文 PDF、截图、草稿、Cookie、后台 token、`wxid_*` 和 `profiles/local/` 永不进入 Git
- 未确认 BCL/TUS 二维码、Logo、历史排版模板和文章片段的公开授权前，仓库保持 Private

## Changelog

### v0.5.0 — 2026-08-11

- **feat**: 增加 BCL + TUS 三类论文路由、普通论文与团队研究历史模板
- **feat**: 增加交接手册、本机 profile、依赖预检、隐私审计与本地回归测试
- **fix**: 移除长篇脚本中的特定论文作者、引文、推荐语和年份硬编码
- **security**: 个人责任编辑和本机路径不再进入跟踪配置

### v0.4.0 — 2026-03-12

- **feat**: 新增征文启事 (Call for Papers) 工作流
- **feat**: 输出格式改为 JSON (`article.json`) + Markdown (`article.md`)
- **feat**: 合并旧版推送技能，统一为单一技能
- **feat**: 默认路径改为用户指定路径或当前工作目录
- **feat**: 责任编辑改为首次使用时询问用户
- **feat**: 征文启事支持双语内容（英文原文 + 中文翻译）
- **feat**: 联系信息块改为可配置占位符

### v0.3.0 — 2026-03-03

- **fix**: 脱敏处理，移除所有个人信息和特定组织信息
- **feat**: 责任编辑改为首次使用时询问，而非硬编码
- **feat**: 模板尾部信息改为可配置占位符

### v0.2.0 — 2026-03-03

- **refactor**: 重命名为 `wechat-office-push`，适用于任意公众号
- **feat**: 更通用的 skill 描述
- **feat**: 通讯作者自动标注（`*` 标记），支持 PDF 文本检测 + CrossRef API 双重识别

### v0.1.0 — 2026-03-03

- **feat**: 初始版本
- PDF 元数据提取（标题、作者、摘要、期刊、DOI）
- 关键页面自动选择与截图（标题页 + 图表页，4-5张）
- CrossRef & Semantic Scholar 联网验证补全
- 中文标题翻译 + 导读生成
- 固定模板 Markdown 输出

## Repository status and licensing

本仓库当前为私有内部工作流，尚未授予公开再分发许可。代码、BCL/TUS 账号资产与历史排版模板的权利边界不同；若未来公开，应先拆分或取得相应授权，再补充正式 `LICENSE` 与资产声明。

