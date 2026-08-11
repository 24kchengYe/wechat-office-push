# 公众号推送技能交接手册

本仓库是 BCL 与 TUS 公众号论文推送的唯一技能源。它保存可复用流程、账号基础配置、排版模板和安全校验；不保存公众号密码、扫码登录态、Cookie、后台 token、未公开论文或个人工作目录。

## 1. 权限与安装

仓库默认保持 **Private**。新负责人应由仓库管理员添加为 GitHub collaborator，不要通过压缩包长期分叉：

```powershell
gh repo clone 24kchengYe/wechat-office-push "$env:USERPROFILE\.codex\skills\wechat-office-push"
cd "$env:USERPROFILE\.codex\skills\wechat-office-push"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果使用 legacy-agent Code，可把同一仓库克隆到 `~/.legacy-agent/skills/wechat-office-push`。不要维护两套互相漂移的副本。

## 2. 创建本机配置

跟踪的 `profiles/bcl.json` 与 `profiles/tus.json` 是无个人信息的基础配置。本机参数放在被 Git 忽略的 `profiles/local/`：

```powershell
New-Item -ItemType Directory -Force profiles\local | Out-Null
Copy-Item profiles\bcl.json profiles\local\bcl.json
Copy-Item profiles\tus.json profiles\local\tus.json
```

在 `profiles/local/bcl.json` 填写当前责任编辑和本机工作目录。不得在 profile 中写公众号账号密码、Cookie 或后台 URL 中的 token。

随后运行：

```powershell
python scripts\preflight.py --profile profiles\local\bcl.json --backend --strict
python scripts\preflight.py --profile profiles\local\tus.json --backend --strict
```

## 3. 外部授权

接手人需要分别获得以下权限，均不通过 Git 分发：

1. BCL 公众号后台操作权限；
2. TUS 公众号后台操作权限；
3. GitHub 私有仓库 collaborator 权限；
4. 论文 PDF 或整理稿的合法访问权限。

公众号登录只允许负责人现场扫码。技能不应读取、导出或保存登录凭据。

## 4. 三类论文路由

| 类型 | 输入 | 目标账号 | 模板 | 合集 |
|---|---|---|---|---|
| TUS 期刊论文 | PDF/DOI/期刊目录 | BCL + TUS | TUS 常规论文版式 | BCL 选“论文推荐”；TUS 不选 |
| 组内重要论文 | 完整 Word 解读稿 + 图片 | 仅 BCL | 团队研究长版 | “论文推荐” |
| 组内普通论文 | 论文 PDF | 仅 BCL | BCL 正常论文推荐 | “论文推荐” |

模板中的 Healthy Cities 等专题推广区默认删除，只有本篇任务明确要求时才保留。

## 5. 每篇推送的完成定义

1. 标题、作者、通讯作者、期刊和 DOI 已由 PDF 标题页与在线来源交叉核验；
2. 本地只维护一份 `article_source.json`，账号差异进入 `accounts/<profile_id>/`；
3. 推荐语不超过公众号 120 字计数；
4. 正文 DOI 与后台“原文链接”一致；
5. 合集符合账号规则；
6. 新标题、作者和图片存在，旧模板标题、作者和 DOI 不存在；
7. 保存为草稿并重新打开核验；
8. 未经用户在最终稿后再次明确授权，不发布、不群发、不定时发送。

## 6. 日常更新

开始工作前：

```powershell
git pull --ff-only
python scripts\audit_repository.py
```

更新技能后：

```powershell
python -m unittest discover -s tests -v
python scripts\audit_repository.py
git status --short
```

只提交技能、模板、基础 profile 和测试。不要提交 `output/`、论文、截图、草稿、登录信息或 `profiles/local/`。

## 7. 故障与移交

- 公众号编辑器改版后，自动化必须失败退出，不能用模糊坐标继续保存。
- 模板替换后，先在无发布权限或测试草稿中验证标题、图片槽位、推荐语、原文链接和合集。
- 离任时只转移 GitHub 与公众号的正式权限，不转移浏览器 Cookie、Codex 会话或个人电脑目录。
- 需要公开仓库时，先确认 BCL/TUS 二维码、Logo、历史排版模板和文章片段的公开授权；未确认前保持 Private。
