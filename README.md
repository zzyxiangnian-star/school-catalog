# school-catalog

Remote marketplace catalog for **school** (Bots, Skills, Skill Packs, and MCP Plugins).

## Summary

- **Skill Catalog Entries (`catalog.json`)**: 148 total
  - **Skill Packs**: 24 packs (269 embedded child skills)
  - **Standalone & Curated Bot Skills**: 124 skills (45 GitHub standalone + 40 Chinese-localized Bot dependency skills by `sean` + 23 Grokbot-matrix specialized Bot skills + 1 official `NVIDIA/SkillEvaluator` skill + 15 China-ready OpenBot workflow skills by `school`)
- **MCP Plugins (`plugins.json`)**: 88 plugins (37 HTTP, 51 stdio, including 9 Chinese connectors adapted from Octop, 3 personal mail IMAP/SMTP connectors, 7 Grokbot ecosystem MCPs, and 9 China-ready stdio MCP connectors)
- **Built-in Bots (`agents.json`)**: 66 Chinese-localized Bot templates (27 by `sean` + 23 Grokbot multi-domain practical sub-Bots `#01–#23` + 16 by `school`, including 1 `Skill 审查员` and 15 China-ready desktop assistant Bots)

## Structure

- `agents.json` — Built-in / curated Bot (Assistant) definitions (`schemaVersion: 1`)
- `catalog.json` — Curated Skill and Skill Pack index (`schemaVersion: 1`, `catalogVersion: "v1"`), ordered with hero (`data`), featured (`for-you`), new, and remaining catalog items sorted by GitHub stars descending
- `plugins.json` — Curated MCP / Plugin catalog (`schemaVersion: 1`, `catalogVersion: "v1"`)
- `skills/` — Skill bundle archives (`<slug>.zip`) and icons (`<slug>.icon.svg`)
- `THIRD_PARTY_NOTICES.md` — Third-party attributions and license notices (Octop, `email-smtp-imap-mcp`, `yuque-mcp`, `NVIDIA/SkillEvaluator`)
