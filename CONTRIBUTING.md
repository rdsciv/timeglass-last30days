# Contributing

Thanks for helping make Work Wrapped better.

## Dev loop

```bash
python3 -m unittest discover -s tests -v
python3 skills/timeglass-last30days/scripts/last30work.py --demo --emit all --out ./out
```

## Guidelines

1. **No scraping.** This skill’s advantage is MCP-only simplicity. Don’t add browser scrapers.
2. **No secrets in fixtures or docs.** Synthetic data only under `fixtures/`.
3. **Keep the engine stdlib-only** unless there’s a strong reason (document it).
4. **SKILL.md is the agent contract.** If behavior changes for agents, update SKILL.md in the same PR.
5. **team_id ≠ workspace_id.** Parsers and docs must keep that distinction loud.

## PR checklist

- [ ] Tests pass
- [ ] `--demo` still produces HTML + markdown
- [ ] README / SKILL version notes updated if user-facing
- [ ] No tokens or personal work records committed
