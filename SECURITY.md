# Security and privacy policy

## Never commit

- WeChat passwords, QR-login captures, cookies, session data, request headers or backend URLs containing `token=`;
- personal email addresses used only for Git authorship; use the GitHub noreply address instead;
- local absolute paths, temporary WeChat folders, `wxid_*` identifiers or AI assistant session data;
- unpublished manuscripts, downloaded PDFs, generated drafts, screenshots or publication ledgers containing private work;
- third-party API keys or credentials.

Public organization contacts intentionally present in `profiles/*.json` are content data, not login credentials. Personal editor names and machine paths belong in `profiles/local/`, which is ignored by Git.

## Public repository boundary

Run:

```powershell
python scripts\audit_repository.py
```

The repository is designed to be safe for public visibility after this audit passes. Public account QR codes, logos, organization contact details and published layout examples are not authentication secrets. They remain subject to the brand and content terms in `ASSET_NOTICE.md`; public visibility does not grant permission to impersonate BCL/TUS or republish third-party article content.

GitHub collaborator access is needed only for maintainers who require write access. Reading and installation do not require an invitation while the repository is public.

## Reporting

Report a suspected credential or privacy leak privately to the repository administrator. Do not open a public issue containing the leaked value. If a credential was committed, revoke it first, then rewrite history and force-push only after making a recoverable local bundle.
