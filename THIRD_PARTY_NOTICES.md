# Third-Party Notices

This catalog (`school-catalog`) incorporates connector definitions, endpoint metadata, and authentication specifications adapted from third-party open-source software.

## Octop

Portions of the Chinese connector definitions in `plugins.json` (including MCP endpoint URLs, header schemas, OAuth discovery parameters, and stdio package specifications) are adapted from [Octop](F:/改造/octop).

连接器定义参考自 Octop，MIT License，Copyright (c) 2026 Octop。

```text
MIT License

Copyright (c) 2026 Octop

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## email-smtp-imap-mcp (`2.2.2`)

The personal mail connectors (`mail-qq`, `mail-163`, `mail-imap`) invoke [`email-smtp-imap-mcp@2.2.2`](https://www.npmjs.com/package/email-smtp-imap-mcp) ([GitHub](https://github.com/samihalawa/email-smtp-imap-mcp)) over stdio via `npx`.

```text
MIT License

Copyright (c) 2025 Sami Halawa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## yuque-mcp (`1.0.0`)

The Yuque connector (`yuque-mcp`) invokes [`yuque-mcp@1.0.0`](https://www.npmjs.com/package/yuque-mcp) ([GitHub](https://github.com/yuque/yuque-mcp-server)) over stdio via `npx`, licensed under the MIT License.

## Official Skill Upstream Mirrors (`skill` branch)

Skill packages and packs mirrored automatically into `catalog.json` and `skills/` via `scripts/sync_upstream.py` originate from the following official open-source repositories:

- [`anthropics/skills`](https://github.com/anthropics/skills) (`Apache-2.0` / repository license terms)
- [`anthropics/knowledge-work-plugins`](https://github.com/anthropics/knowledge-work-plugins) (`Apache-2.0`)
- [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official) (upstream plugin license terms)
- [`openai/skills`](https://github.com/openai/skills) (`Apache-2.0` / repository license terms)
