---
name: wechat-office-push
description: "Generate WeChat public account (公众号) articles from academic PDFs and call-for-papers pages. Supports multiple content types: 论文推荐 (paper recommendation), 征文启事 (call for papers), and more. Use this skill whenever the user mentions: call for papers, CFP推送, 征文推送, 论文推荐, 征文启事, 公众号推送, 写推送, 推文, 公众号文章, WeChat article, 推送论文, 做一个推送, 帮我推论文, 论文推送, 生成推文, 会议推荐, MOOC推送, 教研动态, or any task related to creating content for a WeChat public account."
---

# 公众号推送 Skill

为微信公众号自动生成推送内容（论文推荐、征文启事等）。每篇推送先维护一份经核验的 `article_source.json`，再按账号 profile 输出 `推文.md`、`推文.txt` 和 `article.json`；同一论文投放多个公众号时不得复制两份事实源。

## Supported Categories

1. **论文推荐** — 从学术论文 PDF 生成推荐推文
2. **征文启事** — 从会议/期刊征文信息生成 Call for Papers 推文
3. 会议推荐 *(planned)*
4. MOOC慕课推送 *(planned)*
5. 教研动态 *(planned)*

如果用户提到"征文"、"call for papers"、"CFP"，走征文启事流程；否则默认走论文推荐流程。

## Scripts & Assets

- **Scripts**: `<skill_dir>/scripts/`
  - `extract_pdf.py` — 从 PDF 提取元数据、摘要和关键页图片
  - `lookup_doi.py` — 通过 CrossRef / Semantic Scholar 验证并补全 DOI 元数据
  - `download_sage_pdf.py` — 通过 sage.cnpereading.com 镜像站按 DOI 下载 SAGE 期刊 PDF（SAGE 官站 403 付费墙时使用）
  - `publication_ledger.py` — 维护 DOI 级制作/草稿/发布台账并与期刊目录比对
  - `render_paper_article.py` — 从经核验的 `article_source.json` 生成三格式推送并复制账号二维码
  - `fill_wechat_template.py` — 以账号专属模板填充 TUS 常规论文推送，设置推荐语/原文链接/可选合集并保存草稿；永不发布
  - `fill_team_research_template.py` — 从结构化 Word 稿生成 BCL 长篇“团队研究”版式，保留 BCL 通用页尾；永不发布
- **Templates**: `<skill_dir>/templates/`
  - `paper_template.md` / `paper_template.txt` / `paper_template.json` — 论文推荐三种输出模板
  - `bcl_normal_paper_template.cfhtml.gz.b64` — BCL 普通论文推荐历史模板；制作时默认移除项目/单元推广区
  - `tus_paper_template.cfhtml.gz.b64` — TUS 账号常规论文历史模板
  - `bcl_team_research_template.cfhtml.gz.b64` — BCL 长篇团队研究历史模板
- **Profiles**: `<skill_dir>/profiles/`
  - `bcl.json` — 北京城市实验室BCL 账号配置（公众号名/责任编辑/尾部信息/二维码等）
  - `tus.json` — 城市数据科学与技术汇刊TUS 账号配置；该账号论文推送不选择合集
  - `bcl-paper-template.json` / `tus-paper-template.json` — 账号模板字段、图片槽位和合集规则
  - 新建其它账号时追加 `<profile_id>.json`
- **Assets**: `<skill_dir>/assets/`
  - `qrcode.jpeg` — 默认二维码（BCL 复制到输出目录时重命名为 `bcl_qrcode.jpeg`）
  - `logo.png` — 账号 logo
- **References**: `<skill_dir>/references/`
  - `publication-ledger.md` — 发布事实层级、台账字段与公众号后台检索规则

## Dependencies

```bash
pip install PyMuPDF requests beautifulsoup4
```

## Profile 机制

首次使用时，检查用户是否使用已知 profile（如 BCL）。若是，从 `profiles/<id>.json` 直接读取：
- `account_name` — 公众号名称
- `default_editor` — 默认责任编辑
- `qrcode_filename` — 二维码在输出目录中的文件名
- `footer_text` — 固定尾部文本（逐行数组）
- `contact` — 邮箱/微博/微信号/网址
- `default_working_dir` — 默认工作目录

**BCL 默认值**：
- 公众号名称：北京城市实验室BCL
- 责任编辑：[责任编辑待配置]
- 工作目录：`<work_dir>`
- QR 文件：`bcl_qrcode.jpeg`

若用户使用新账号，询问一次后保存为新的 profile。

### BCL + TUS 双账号约定

- 本地只维护一份经核验论文事实源；账号差异仅存在于 profile、模板、页尾、推荐语和合集设置中。
- 账号输出放在 `output/<paper_slug>/accounts/<profile_id>/`，根目录源文件与 PDF/图片不复制、不删除。
- 大批量任务先在一个账号完成全部独立草稿和核验，再切换账号批量创建另一账号草稿，减少误投和频繁切号。
- BCL 的常规论文推荐必须选择 `论文推荐` 合集；TUS 自有公众号的论文推送明确不选合集。
- 两个账号都只保存草稿并等待用户确认，不得因“批量完成”推断为允许发表。

### 三类论文推送分流（先分类，再选账号与模板）

处理论文前先判断其制作类别；“组内论文”不等于 TUS 论文，也不等于长篇团队研究稿。

1. **TUS 期刊论文**：来源为 *Transactions in Urban Data, Science, and Technology*。同一事实源生成 BCL 与 TUS 两个账号草稿，均使用 TUS 常规短版论文结构；BCL 选择 `论文推荐` 合集，TUS 不选合集。
2. **组内重要论文（有整理后的完整稿）**：用户提供结构化 Word/图文解读稿，且要求重点推送。只做 BCL，使用历史“团队研究”长版；按稿件章节组织正文，不压缩为 TUS 短版，并选择 `论文推荐` 合集。
3. **组内普通论文（只有论文 PDF）**：只做 BCL，克隆 BCL 已发表的普通“论文推荐”历史文章，使用正常论文推荐版式；不得生成 TUS 草稿，也不得套用长篇团队研究模板，并选择 `论文推荐` 合集。

如果材料形态与用户分类冲突，以用户明确指定的类别为准；无法判断时优先检查是否属于 TUS、是否有完整 Word 解读稿，不要仅凭作者来自组内就自动升级为长篇格式。

---

## Workflow 1: 论文推荐 (Paper Recommendation)

### Step 0: 去重检查（新增，重要）

**在开始处理 PDF 之前**，若用户的推送任务来自某期刊的 Online First / Current Issue 等列表源（如"TUS 期刊最新一期"），**必须先做去重**：

1. 读取 `references/publication-ledger.md`。
2. 从期刊实时目录获取英文标题、DOI、期次/Online First 状态，禁止用旧缓存替代。
3. 若用户已经登录公众号后台，优先检查“已发表记录”；只有无法访问后台时，才请用户提供截图或标题列表。
4. 对每篇至少使用 DOI、完整英文标题和一个稳定英文短语交叉检索。中文译名只能作为辅助，不能单独判定未发布。
5. 按以下事实层级判定：
   - 公众号后台已发表记录：是否已发布的唯一事实源；
   - 公众号草稿箱：是否已存草稿；
   - 本地输出文件：是否已制作，不能据此推断发布状态；
   - 期刊实时目录：候选论文范围。
6. 用 `publication_ledger.py` 更新 DOI 台账，明确区分 `local_status`、`draft_status`、`wechat_status`。
7. 做映射表并标记“🆕 未推送”“📝 已存草稿”“✅ 已发布”“⚠️ 待人工确认”。
8. 只对“🆕 未推送”的论文继续后续流程；批量任务在用户确认范围后再下载 PDF。

这一步防止重复劳动和重复推送。

### Step 1: 确定输入

1. **输入路径**: 包含 PDF 的文件夹（用户指定或当前工作目录）
2. **输出路径**: 默认 `<输入目录上一级>/output/<paper_slug>/`，每篇一个子文件夹

### Step 1.5: 若 PDF 需自动下载（SAGE 期刊）

用户若只给了 DOI 列表或期刊页面，未提供 PDF：
- SAGE 官方 PDF (journals.sagepub.com) 常见 403（付费墙）
- **改用 sage.cnpereading.com 镜像**：由脚本解析文章页的 `articleId`，再访问当前下载接口；旧 DOI 接口仅作回退
- 使用内置脚本：
  ```bash
  python "<skill_dir>/scripts/download_sage_pdf.py" <doi> --out <target_dir> --name <filename.pdf>
  ```
- 脚本会验证 PDF 魔数（`%PDF-`）确保下载到的是真 PDF
- 批量下载用 `--doi-list dois.txt`

### Step 2: 提取 PDF 内容

对每个 `.pdf` 文件运行：

```bash
python "<skill_dir>/scripts/extract_pdf.py" "<pdf_path>" "<output_dir>/<paper_subfolder>" --max-images 5
```

提取内容：metadata、4-5 张关键页图片（标题页 + 图表页）、`metadata.json`。

### Step 3: 在线 DOI 验证与补全

**必须对每篇执行**：

```bash
python "<skill_dir>/scripts/lookup_doi.py" --doi "<doi>"
# 或按标题查：--title "<paper_title>"
```

**合并规则**（extract_pdf.py 对作者和 title 提取常有缺陷，必须用 lookup_doi 覆盖）：
- `title` — **总是优先用 lookup_doi 返回的完整标题**（PDF 抽取常被换行截断或掺入附属文本）
- `authors` — **总是优先用 lookup_doi**（PDF 抽取常因上标/仿宋字体缺失姓名）
- `journal` — **总是优先用 lookup_doi**（PDF 抽取常带结尾杂质）
- `doi` — lookup_doi 补全缺失
- `abstract` — 保留 PDF 提取的（CrossRef 很少返回摘要）
- `year` — 用 lookup_doi 返回的发表年份

### Step 3.5: 旧文首发年份提醒（新增）

若 `lookup_doi` 返回的 `year` 与当前年份相差 ≥ 2 年，但论文却出现在当前 Online First 列表：
- 在 `article.json` 的 `论文相关.备注` 字段写明："首次在线发表于 YYYY 年，当前重新列入 Online First"
- 提醒用户决定是否在导读里加一句说明

### Step 4: 通讯作者识别（必须视觉验证）

按以下顺序：
1. `lookup_doi.py` 返回的 `corresponding_authors`
2. `extract_pdf.py` 的 `corresponding_author` 字段
3. **视觉检查标题页图片** (`page_001.jpg`) 的 `Corresponding author:` 段落 — **这一步是强制的**，CrossRef 常不返回通讯作者
4. 如仍无法确定，标为 `[通讯作者待确认]` 并询问用户

确定后在作者列表中该姓名后加 `*` 标记。

### Step 5: 生成中文内容

1. **翻译英文标题为中文学术名**（准确专业，不过度意译）
2. **撰写中文导读**（基于英文摘要）：
   - 流畅自然的中文学术语言
   - 概述研究背景/方法/主要发现
   - 约 150-300 字
3. **最终视觉核对**：把标题、作者、通讯作者、DOI 与 `page_001.jpg` 逐字段对比

### Step 6: 生成三种格式输出文件

对每篇论文在 `output/<paper_slug>/` 下同时生成：

优先把人工核验后的标题、作者、通讯作者、摘要、导读和图片列表保存为 `article_source.json`，再运行：

```bash
python "<skill_dir>/scripts/render_paper_article.py" \
  "<output_dir>/<paper_slug>/article_source.json" \
  --output-dir "<output_dir>/<paper_slug>" \
  --profile "<skill_dir>/profiles/bcl.json" \
  --qrcode-source "<skill_dir>/assets/qrcode.jpeg"
```

#### 6a. `推文.md`（markdown 版，便于 git diff 和阅读）

按 `templates/paper_template.md` 填充。

#### 6b. `推文.txt`（纯文本版，用于复制粘贴到公众号编辑器）

按 `templates/paper_template.txt` 填充。关键约定：
- 零 markdown 语法
- 用 `━━━` 全角粗线分节（用户可在编辑器中保留或删除）
- 段落名用 `【导读】`、`【论文相关】`、`【摘 要 ABSTRACT】`、`【论文展示（部分）】` 等中文方括号
- 图片位置用 `【配图：page_001.jpg】` 占位（编辑器中手动替换为实际图片）
- "题 目 ："、"摘 要 ABSTRACT" 中间的全角空格严格保持
- 尾部固定信息从 profile 的 `footer_text` 数组逐行注入

#### 6c. `article.json`（结构化数据，给未来自动化上传/索引脚本使用）

按 `templates/paper_template.json` 填充。关键字段：
- 顶层：`type` / `title_cn` / `title_en` / `headline` / `account` / `date` / `time` / `导读`
- `论文相关`：`题目_cn` / `题目_en` / `作者`（含 `*`）/ `作者列表`（数组）/ `通讯作者` / `通讯作者邮箱` / `通讯作者单位` / `DOI` / `DOI链接` / `发表年份` / `备注`（可选）
- `摘要`：英文原文
- `论文展示`：图片文件名数组
- `footer`：从 profile 注入（`qrcode` / `account_intro` / `email` / `weibo` / `wechat_id` / `website` / `责任编辑` / `阅读原文`）

### Step 7: 复制固定资源

```bash
cp "<skill_dir>/assets/qrcode.jpeg" \
   "<output_dir>/<paper_subfolder>/<profile.qrcode_filename>"
```

注意使用 profile 中的 `qrcode_filename`（BCL 是 `bcl_qrcode.jpeg`，不是默认的 `qrcode.jpeg`）。

### Step 8: 展示结果

1. 汇总表：title / authors / 通讯作者 / journal / DOI
2. 列出每个 output 子文件夹的文件清单（确认三种格式都在）
3. 询问是否需要调整翻译、导读、时间戳等
4. 确认后结束

### Step 9: 录入公众号草稿（仅在用户明确要求时）

1. 先在公众号后台再次按 DOI 或英文标题检索，防止制作期间出现重复发布。
2. 按“三类论文推送分流”确定账号和模板；优先使用公众号后台“新的创作 → 选择已有内容”，从已发表的**同类**推送生成副本，以完整继承标题层级、段落、字号、颜色、分隔线、固定装饰图和页尾。普通组内论文只能选 BCL 普通论文推荐历史稿，不能选 TUS 短版或团队研究长版。
3. 只替换副本中的标题、导读、论文信息、摘要和论文页图；保留当前账号固定资源。TUS 常规论文版式优先使用 `scripts/fill_wechat_template.py`，由 profile 决定账号模板与合集规则；旧的 `fill_wechat_template.ps1` 仅保留为受信任的 BCL 兼容入口。
4. 用户提供完整 Word 解读稿且指定 BCL 历史长篇样式时，使用 `scripts/fill_team_research_template.py`：按 Word 标题样式识别“摘要/方法/结果与讨论/研究意义”，按 Caption 顺序插入 `fig1`—`fig5`，删除模板论文的项目专属推广区，只保留 BCL 通用页尾。不得强行套用 TUS 的“导读—论文相关—Abstract—论文展示”短版结构。
5. 历史模板中的专题/单元引流属于可选项目推广区，例如“更多相关的研究工作详见 BCL 的【Healthy Cities】单元链接”。普通论文推荐默认删除整个推广区；只有用户对本篇明确指定某个 BCL 单元时才保留或替换，不能因为模板里存在就沿用。
6. 平台推荐语默认复用正文导读首段；TUS 常规论文优先使用固定句式。按公众号计数规则检查 120 字限制，只有超限时才最小压缩套话，不得删改已核验题目。BCL 长篇稿可用 120 字内的中文研究概述。
7. “原文链接”是正文内 DOI 之外的独立设置，必须显式改为本篇 `https://doi.org/<DOI>`。保存前同时核对正文 DOI、原文链接和事实源三者一致。
8. 合集是账号级规则：BCL 的论文推荐（包括长篇团队研究论文解读）选择 `论文推荐`；TUS 账号不选合集；非论文内容不默认加入该合集。
9. 对照结构化源和标题页复核标题、作者、通讯作者、DOI；保存后确认推荐语不超过 `120/120`、原文链接正确、合集符合当前 profile、新题目/作者/图片存在且旧模板题目和 DOI 不存在。
10. 点击“保存为草稿”后，以 `publication_ledger.py set --account <profile_id>` 更新对应账号的 `draft_status=saved`、草稿标题和证据；不得用 BCL 状态覆盖 TUS 状态。
11. 所有填充脚本默认只填充和校验；只有用户明确授权保存草稿时才传保存参数。脚本没有发表、群发或定时发表能力。
12. **默认停在草稿或预览页面等待用户确认。不得点击群发、发布、定时群发或任何等效按钮，除非用户在看过最终稿后再次明确授权。**
13. 批量任务逐篇保存为独立草稿；不得把多篇论文误合并为一篇多图文，除非用户明确要求。
14. 公众号可能自动保存调试副本。最终交付前按“标题 + 更新时间”检查草稿列表；疑似残留只能报告，未经用户明确授权不得删除。已授权清理时也必须逐篇确认标题与更新时间，并在删除后复核正式草稿仍在、草稿总数变化符合预期。

---

## Workflow 2: 征文启事 (Call for Papers)

### 输入与触发

当用户提到"征文"、"call for papers"、"CFP"时走此流程。

- **输入**: 用户提供的官网链接（期刊/会议征文页面 URL）
- **输出**: `<工作目录>/征文启事/<专刊简称>/` 下同时生成 `推文.md` / `推文.txt` / `article.json` + 可选图片
- **Profile**: 同论文推荐流程，从 `profiles/<id>.json` 读取

### CFP Step 1: 获取征文信息

使用 WebFetch 访问用户提供的 URL，提取：
- 专刊/会议名称（英文 + 中文翻译）
- 期刊名称
- Rationale（选题依据）
- Scope of Topics（主题范围）
- Guidelines（投稿指南）
- Timeline（时间表）
- Guest Editors（客座编辑，含姓名/单位/邮箱）
- 相关链接（投稿入口、期刊主页）

缺失字段标 `[待补充]`。

### CFP Step 2: 生成双语内容

1. 专刊名称翻译
2. 各章节双语呈现（英文原文在前，中文翻译紧跟）
3. 翻译风格：学术正式，术语准确
4. 导读段落：150-250 字

### CFP Step 3: 生成三种格式输出

同样产出 `推文.md` / `推文.txt` / `article.json`。JSON 结构：

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
      "content_en": "...",
      "content_cn": "..."
    },
    {
      "heading": "The scope of Topics（主题范围）",
      "content_en": "...",
      "content_cn": "...",
      "topics": ["topic1", "topic2"]
    },
    {
      "heading": "Guidelines(投稿指南)",
      "content_en": "...",
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
        { "name": "...", "email": "...", "affiliation": "..." }
      ]
    }
  ],
  "links": {
    "专刊链接": "...",
    "期刊主页链接": "...",
    "投稿系统": "..."
  },
  "footer": { "qrcode": "...", "责任编辑": "...", "contact": "..." }
}
```

### CFP Step 4: 复制资源 + 展示结果

同论文推荐流程。

### 征文启事格式说明

- 标题格式固定为 "征文启事 | [期刊简称]专刊《[中文名称]》等你来"
- 导读固定开头："本期为大家推介的是期刊《..."
- 章节正文：英文原文在前，中文翻译紧跟
- Guest editors 列完整信息
- "阅读原文"指向期刊主页（不是 DOI）

---

## Important Notes

- **公众号名称** 从 profile 读取；新账号首次使用时创建新 profile
- **论文推荐导读固定开头**："本期为大家推荐的内容为论文《...》（...），发表在 ... 期刊，欢迎大家学习与交流。" 不要改动
- **"题 目"、"摘 要"** 中间有一个全角空格，三种格式都保持原样
- **通讯作者** 在姓名后加 `*` 标记
- **DOI** 链接用完整 `https://doi.org/...` 格式
- **日期格式**：YYYY年M月D日（如 2026年4月11日），时间 HH:MM，默认用当天
- **论文展示图片** 目标 4-5 张，优先标题页和图表页
- **责任编辑** 从 profile 读取
- **输出必须是三种格式**：`推文.md` / `推文.txt` / `article.json`，缺一不可

## Error Handling

- PyMuPDF 未安装：提示 `pip install PyMuPDF`
- 输入目录无 PDF：告知用户并要求正确路径
- 某字段提取失败：标 `[待补充]` 并询问
- DOI 查询失败：标 `[待查找]` 并提醒手动核对
- SAGE PDF 下载 403：切换到 `download_sage_pdf.py` 走 cnpereading 镜像
- `extract_pdf.py` 的 title/authors 提取异常（极常见）：无条件用 `lookup_doi.py` 覆盖
- 通讯作者识别失败：必须视觉检查标题页图片

## Example Usage

```
User: "帮我推一篇论文"
→ 论文推荐流程，询问 PDF 路径，加载 BCL profile，处理

User: "TUS 期刊有几篇新的 Online First，帮我推一下，这几张是草稿箱截图，不要重复"
→ Step 0 去重 → Step 1.5 自动下载 PDF → Step 2-8 三格式输出

User: "推送 F:/papers/xxx.pdf"
→ 直接从 Step 2 开始

User: "征文启事，链接 https://www.journals.elsevier.com/xxx"
→ 征文启事流程
```
