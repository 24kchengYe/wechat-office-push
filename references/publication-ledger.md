# 论文推送发布台账

## 事实层级

1. 以期刊实时目录界定候选论文。
2. 以微信公众号后台“已发表记录”判定是否已发布。
3. 以微信公众号草稿箱判定是否存在待发草稿。
4. 以本地输出目录判定是否已经制作。

四种状态必须分开记录。发现本地产物与后台状态冲突时，保留两者并按上述层级解释，不得覆盖成单一“已完成”状态。

## 后台检索规则

- 首选 DOI；若后台搜索不索引 DOI，则搜索完整英文标题。
- 再选一个不易变化的 3–8 词英文短语，例如方法名或标题后半句。
- 中文标题只作辅助。中英文标点、连字符、全角字符和翻译差异可能造成假阴性。
- 单次搜索为 0 不能直接判定未发布；至少两种独立查询均为 0 后才标记 `not_found`。
- 搜索命中后核对标题主体、期刊语境和日期，排除同名文章。

## JSON 台账结构

```json
{
  "schema_version": 1,
  "journal": "Transactions in Urban Data, Science, and Technology",
  "catalog_url": "https://sage.cnpereading.com/toc/tusa",
  "last_checked": "YYYY-MM-DDTHH:MM:SS+08:00",
  "items": [
    {
      "doi": "10.1177/...",
      "title_en": "...",
      "issue_bucket": "Vol. 5(2)",
      "journal_status": "current_issue",
      "local_status": "not_started",
      "local_path": "",
      "draft_status": "none",
      "draft_title": "",
      "wechat_status": "not_found",
      "publish_date": "",
      "article_url": "",
      "last_checked": "YYYY-MM-DDTHH:MM:SS+08:00",
      "evidence": ["backend search: exact English title = 0"]
    }
  ]
}
```

允许值：

- `journal_status`: `current_issue`, `online_first`, `archived`
- `local_status`: `not_started`, `generated`, `verified`
- `draft_status`: `none`, `saved`, `needs_review`
- `wechat_status`: `unknown`, `not_found`, `published`

## 操作要求

- 以 DOI（转小写、去除 `https://doi.org/`）作为唯一键。
- 每次后台或目录核对后更新 `last_checked` 和 `evidence`。
- 只有看到后台已发表记录才能写 `wechat_status=published`。
- 只有成功保存并重新打开草稿确认内容存在，才能写 `draft_status=saved`。
- 群发后再次回到已发表记录核验，再把草稿状态清空并写入发布日期和文章地址。
