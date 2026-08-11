# Security and privacy policy

## Never commit

- WeChat passwords, QR-login captures, cookies, session data, request headers or backend URLs containing `token=`;
- personal email addresses used only for Git authorship; use the GitHub noreply address instead;
- local absolute paths, temporary WeChat folders, `wxid_*` identifiers or Codex/legacy-agent session data;
- unpublished manuscripts, downloaded PDFs, generated drafts, screenshots or publication ledgers containing private work;
- third-party API keys or credentials.

Public organization contacts intentionally present in `profiles/*.json` are content data, not login credentials. Personal editor names and machine paths belong in `profiles/local/`, which is ignored by Git.

## Before sharing or changing visibility

Run:

```powershell
python scripts\audit_repository.py
```

The repository should remain private until the rights holder confirms that QR codes, logos, historical rich-text templates and article excerpts may be redistributed publicly. GitHub collaborator access is the default succession path.

## Reporting

Report a suspected credential or privacy leak privately to the repository administrator. Do not open a public issue containing the leaked value. If a credential was committed, revoke it first, then rewrite history and force-push only after making a recoverable local bundle.
