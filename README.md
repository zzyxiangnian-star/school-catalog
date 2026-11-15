# school-catalog

Remote marketplace catalog for **school** (Bots, Skills, Skill Packs, and MCP Plugins).

## Summary

- **Skill Catalog Entries (`catalog.json`)**: 69 total
  - **Skill Packs**: 24 packs (269 embedded child skills)
  - **Standalone Skills**: 45 skills
- **MCP Plugins (`plugins.json`)**: 60 plugins (29 HTTP, 31 stdio)
- **Built-in Bots (`agents.json`)**: 0 entries

## Structure

- `agents.json` — Built-in / curated Bot (Assistant) definitions (`schemaVersion: 1`)
- `catalog.json` — Curated Skill and Skill Pack index (`schemaVersion: 1`, `catalogVersion: "v1"`), ordered with hero (`data`), featured (`for-you`), new, and remaining catalog items sorted by GitHub stars descending
- `plugins.json` — Curated MCP / Plugin catalog (`schemaVersion: 1`, `catalogVersion: "v1"`)
- `skills/` — Skill bundle archives (`<slug>.zip`) and icons (`<slug>.icon.svg`)
