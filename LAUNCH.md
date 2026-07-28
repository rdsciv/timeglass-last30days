# Launch playbook — make this go viral for Timeglass

Goal: turn this repo into top-of-funnel for [timeglass.ai](https://timeglass.ai) signups.

## Positioning (one line)

> `/last30days` researched the internet. `/timeglass-last30days` wraps **your** month — from Timeglass MCP, no scraping.

## Day-0 checklist

- [x] Public repo with polished README + hero
- [x] Zero-config `--demo` path (anyone can run in 30s)
- [x] HTML artifact people can screenshot
- [x] GitHub Pages landing + live demo
- [x] Agent Skills / Claude / Codex / Grok manifests
- [ ] Pin tweet + LinkedIn post with demo GIF/MP4 of HTML scroll
- [ ] Show HN / r/ClaudeAI / r/ChatGPTCoding / r/mcp
- [ ] Tag Timeglass team for RT / blog embed
- [ ] Submit to agentskills.io / ClawHub / awesome-mcp lists

## Content angles that travel

1. **Inversion of last30days** — “54k-star energy, inverted: not what people said, what *you* did.”
2. **Spotify Wrapped for billable work** — founders + agencies screenshot identity cards.
3. **MCP is the moat** — “we didn’t write scrapers; Timeglass already has the record.”
4. **Friday ritual** — “run Work Wrapped before you invoice.”
5. **Agent install one-liner** — `npx skills add rdsciv/timeglass-last30days -g`

## Demo GIF recipe (do this next)

```bash
python3 skills/timeglass-last30days/scripts/last30work.py --demo --emit all --out ./out
open out/work-wrapped.html
# Record 8–12s scroll of hero → projects → identity cards
# Post with clone command in first comment
```

## Funnel

```
Star / clone → --demo wow → connect Timeglass MCP → live Wrapped → daily capture habit → paid seat
```

Every README CTA should end at **timeglass.ai** or the AI connector docs — not just “star us.”

## What not to do

- Don’t imply you scrape private data.
- Don’t ship real customer fixtures.
- Don’t require pip hell for first run (stdlib stays sacred).
- Don’t fight last30days — ride it. Cross-link as complementary.
