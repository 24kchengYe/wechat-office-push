# wechat-office-push — 公众号推送 Skill for Claude Code

> **自动从论文 PDF 生成微信公众号推文，包括中文翻译、元数据提取、关键页面截图、DOI 联网验证。**

## 功能

将一个装有论文 PDF 的文件夹，一键转换为多篇格式规范的公众号推文（Markdown + 图片）。

```
输入: 论文PDF文件夹/
        ├── paper1.pdf
        ├── paper2.pdf
        └── paper3.pdf

输出: output/
        ├── paper1/
        │   ├── 推文.md          ← 完整推文内容
        │   ├── page_001.jpg     ← 论文关键页截图
        │   ├── page_004.jpg
        │   ├── qrcode.jpeg      ← 公众号二维码
        │   └── metadata.json    ← 提取的元数据
        ├── paper2/
        └── paper3/
```

### 自动化流程

| 步骤 | 内容 |
|------|------|
| 1 | 扫描文件夹中的 PDF |
| 2 | 提取标题、作者、摘要、期刊、DOI |
| 3 | **联网验证补全**（CrossRef + Semantic Scholar API），修正作者缺失、期刊名噪音等 |
| 4 | 自动选择 4-5 张关键页面（标题页 + 图表页）截图 |
| 5 | Claude 翻译标题和摘要为中文，撰写导读 |
| 6 | 按固定模板生成 Markdown 推文 |

### 支持的推送类别

- **论文推荐** (Paper Recommendation) — 已实现
- 会议推荐 — 规划中
- MOOC 慕课推送 — 规划中
- 征文启事 — 规划中
- 教研动态 — 规划中

## 使用方式

在 Claude Code 中直接说：

```
帮我做一个论文推送
推送一下 F:/papers/ 里面的论文
论文推荐，pdf在桌面上
```

Skill 会自动触发，引导你完成整个流程。

工作目录可自定义，首次使用时 Skill 会询问输入输出路径。

## 安装

### 从 Skills CLI

```bash
npx skills add <your-github-username>/wechat-office-push
```

### 手动安装

```bash
# macOS / Linux
git clone https://github.com/<your-github-username>/wechat-office-push.git ~/.claude/skills/wechat-office-push

# Windows
git clone https://github.com/<your-github-username>/wechat-office-push.git %USERPROFILE%\.claude\skills\wechat-office-push
```

### 依赖

```bash
pip install PyMuPDF requests
```

## 文件结构

```
wechat-office-push/
├── SKILL.md              ← Skill 定义（触发词、工作流、模板）
├── README.md
├── scripts/
│   ├── extract_pdf.py    ← PDF 元信息提取 + 关键页面截图
│   └── lookup_doi.py     ← CrossRef & Semantic Scholar 元数据验证
├── assets/
│   ├── qrcode.jpeg       ← 公众号二维码（用户自行替换）
│   └── logo.png          ← Logo（用户自行替换）
└── templates/
    └── paper_template.md  ← Markdown 推文模板
```

## 推文格式

每篇论文推荐推文包含以下固定结构：

1. **标题**：`论文推荐 | [中文标题]`
2. **导读**：固定开头 + 中文摘要改写（150-300字）
3. **论文相关**：英文题目、中文题目、作者（含通讯作者*标记）、期刊、DOI
4. **摘要 ABSTRACT**：英文原文
5. **论文展示**：4-5 张 PDF 关键页面截图
6. **固定尾部**：联系方式、二维码、责任编辑

## 需求

- Claude Code (VS Code / JetBrains / Cursor / Windsurf / Terminal)
- Python 3.8+
- PyMuPDF (`pip install PyMuPDF`)
- requests (`pip install requests`)

## Changelog

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

## License

MIT
