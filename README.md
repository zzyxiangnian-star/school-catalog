# school-catalog

Remote marketplace catalog for **school** (Bots, Skills, Skill Packs, and MCP Plugins).

## Summary

- **Skill Catalog Entries (`catalog.json`)**: 159 total
  - **Skill Packs**: 39 packs (386 embedded child skills)
  - **Standalone & Curated Bot Skills**: 120 skills (80 GitHub standalone + 40 Chinese-localized Bot dependency skills by `sean`)
- **MCP Plugins (`plugins.json`)**: 72 plugins (37 HTTP, 35 stdio, including 9 Chinese connectors adapted from Octop and 3 personal mail IMAP/SMTP connectors)
- **Built-in Bots (`agents.json`)**: 27 Chinese-localized Bot templates (`creatorName: "sean"`)

## Structure

- `agents.json` — Built-in / curated Bot (Assistant) definitions (`schemaVersion: 1`)
- `catalog.json` — Curated Skill and Skill Pack index (`schemaVersion: 1`, `catalogVersion: "v1"`), ordered with hero (`data`), featured (`for-you`), new, and remaining catalog items sorted by GitHub stars descending
- `plugins.json` — Curated MCP / Plugin catalog (`schemaVersion: 1`, `catalogVersion: "v1"`)
- `skills/` — Skill bundle archives (`<slug>.zip`) and icons (`<slug>.icon.svg`)
- `THIRD_PARTY_NOTICES.md` — Third-party attributions and MIT License notices (Octop, `email-smtp-imap-mcp`, `yuque-mcp`)

## Automated Official Upstream Sync

- Official upstream repositories mirrored automatically via `upstream-sources.json`, `scripts/sync_upstream.py`, and `.github/workflows/sync-skills.yml`:
  - `anthropics/skills`
  - `anthropics/knowledge-work-plugins`
  - `anthropics/claude-plugins-official`
  - `openai/skills`
