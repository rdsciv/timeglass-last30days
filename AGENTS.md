# AGENTS.md

## Product

This repo is an **agent skill** that builds a **Work Wrapped** (Spotify-Wrapped-style monthly review) from **Timeglass MCP**. No scraping.

## Do

- Run `python3 skills/timeglass-last30days/scripts/last30work.py --demo` when validating without credentials
- Follow `skills/timeglass-last30days/SKILL.md` for user-facing synthesis shape
- Keep secrets out of git; use env vars

## Don't

- Scrape email/calendar/browser as a substitute for Timeglass
- Pass `workspace_id` where `team_id` is required
- Print bearer tokens
- Invent hours not present in engine/MCP output
