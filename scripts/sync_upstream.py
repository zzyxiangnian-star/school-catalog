#!/usr/bin/env python3
"""
Automated Official Upstream Skill Mirror & Validator for school-catalog.

Syncs transparent official upstream repositories defined in `upstream-sources.json`
(OpenAI, Anthropic skills, Anthropic knowledge-work-plugins, Anthropic claude-plugins-official),
applies completeness & static security gates, builds deterministic `.zip` + `.icon.svg`
assets, merges with `catalog-overrides.json`, updates `catalog.json` / `README.md` /
`THIRD_PARTY_NOTICES.md`, and verifies every catalog entry's SHA256 and archive contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

VALID_CATEGORIES = {
    "coding",
    "productivity",
    "design",
    "documents",
    "automation",
    "data-analytics",
    "research",
    "other",
}

CATEGORY_COLORS = {
    "coding": "#3b82f6",
    "productivity": "#10b981",
    "design": "#ec4899",
    "documents": "#f59e0b",
    "automation": "#06b6d4",
    "data-analytics": "#8b5cf6",
    "research": "#6366f1",
    "other": "#64748b",
}

IGNORE_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    "dist",
    "build",
}
IGNORE_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
CODE_EXTS = {".py", ".sh", ".bash", ".js", ".ts", ".mjs", ".cjs", ".ps1"}

CRITICAL_CODE_PATTERNS = [
    ("remote_pipe_exec", re.compile(r"(?:curl|wget)\s+[^\n|]*\|\s*(?:ba)?sh\b", re.I)),
    ("encoded_exec_py", re.compile(r"(?:eval|exec)\s*\(\s*base64\.b64decode", re.I)),
    ("encoded_exec_sh", re.compile(r"base64\s+(?:-d|--decode)[^\n|]*\|\s*(?:ba)?sh\b", re.I)),
    ("reverse_shell", re.compile(r"(?:/dev/tcp/\d+\.\d+|nc\s+-e\s+/bin/|pty\.spawn\([\"']/(?:bin/)?(?:ba)?sh)", re.I)),
]

PROMPT_INJECTION_PATTERNS = [
    ("prompt_override", re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions|disregard\s+(?:all\s+)?prior\s+instructions", re.I)),
]


def _proxy_env() -> str | None:
    return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("https_proxy") or os.environ.get("http_proxy")


def _gh_api_repo(full_name: str, proxy: str | None) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{full_name}"
    headers = {"User-Agent": "school-catalog-sync", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "stars": int(data.get("stargazers_count", 0)),
                "license": (data.get("license") or {}).get("spdx_id"),
                "branch": data.get("default_branch", "main"),
            }
    except Exception:
        return {}


def ensure_repo_checkout(src: dict[str, Any], cache_dir: Path, proxy: str | None) -> tuple[Path, dict[str, Any]]:
    full_name = src["repository"]
    slug_dir = full_name.split("/")[-1]
    # Support both <owner>__<repo> and <repo> naming in cache
    candidates = [cache_dir / src["id"], cache_dir / slug_dir]
    if slug_dir == "skills" and full_name.startswith("openai/"):
        candidates.insert(0, cache_dir / "openai-skills")
    if slug_dir == "skills" and full_name.startswith("anthropics/"):
        candidates.insert(0, cache_dir / "anthropics-skills")

    repo_path = next((c for c in candidates if (c / ".git").exists()), cache_dir / src["id"])
    git_prefix = ["git"]
    if proxy:
        git_prefix += ["-c", f"http.proxy={proxy}", "-c", "http.version=HTTP/1.1"]

    if (repo_path / ".git").exists():
        subprocess.run(git_prefix + ["fetch", "--depth", "1", "origin", src["branch"]], cwd=repo_path, check=False, capture_output=True)
        subprocess.run(git_prefix + ["reset", "--hard", f"origin/{src['branch']}"], cwd=repo_path, check=False, capture_output=True)
    else:
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            git_prefix + ["clone", "--depth", "1", "--branch", src["branch"], f"https://github.com/{full_name}.git", str(repo_path)],
            check=True,
        )

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path, text=True).strip()
    api_meta = _gh_api_repo(full_name, proxy)
    return repo_path, {
        "repository": f"https://github.com/{full_name}",
        "full_name": full_name,
        "commit": commit,
        "stars": api_meta.get("stars", 0),
        "license": api_meta.get("license") or src.get("license"),
        "provider": src["provider"],
        "creatorName": src["creatorName"],
    }


def parse_frontmatter(skill_md: Path) -> tuple[bool, dict[str, str]]:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^\s*---\s*\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return False, {}
    data: dict[str, str] = {}
    cur_key = None
    cur_lines: list[str] = []
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if kv:
            if cur_key is not None:
                data[cur_key] = " ".join(cur_lines).strip().strip('"').strip("'")
            cur_key = kv.group(1).strip()
            val = kv.group(2).strip()
            cur_lines = [] if val in (">-", ">", "|", "|-") else [val]
        elif cur_key is not None and (line.startswith("  ") or line.startswith("\t")):
            cur_lines.append(line.strip())
    if cur_key is not None:
        data[cur_key] = " ".join(cur_lines).strip().strip('"').strip("'")
    return (bool(data.get("name")) and bool(data.get("description"))), data


def security_scan_dir(target_dir: Path) -> list[dict[str, str]]:
    critical: list[dict[str, str]] = []
    for p in target_dir.rglob("*"):
        if not p.is_file() or any(part in IGNORE_DIR_NAMES for part in p.relative_to(target_dir).parts):
            continue
        if p.stat().st_size > 1_000_000:
            continue
        ext = p.suffix.lower()
        if ext in CODE_EXTS:
            txt = p.read_text(encoding="utf-8", errors="replace")
            for rule, pat in CRITICAL_CODE_PATTERNS:
                if pat.search(txt):
                    critical.append({"file": p.relative_to(target_dir).as_posix(), "rule": rule})
        elif p.name.upper() == "SKILL.MD":
            txt = p.read_text(encoding="utf-8", errors="replace")
            for rule, pat in PROMPT_INJECTION_PATTERNS:
                if pat.search(txt):
                    critical.append({"file": p.relative_to(target_dir).as_posix(), "rule": rule})
    return critical


def infer_category(slug: str, desc: str) -> str:
    txt = f"{slug} {desc}".lower()
    if any(k in txt for k in ("figma", "design", "ui", "frontend", "art", "playground", "pet")):
        return "design"
    if any(k in txt for k in ("pdf", "docx", "pptx", "doc", "voice", "brand-voice", "artifact")):
        return "documents"
    if any(k in txt for k in ("deploy", "playwright", "hook", "discord", "telegram", "imessage", "migrate", "yeet", "installer")):
        return "automation"
    if any(k in txt for k in ("data", "sql", "analytics", "xlsx", "manufacturing", "session-report")):
        return "data-analytics"
    if any(k in txt for k in ("research", "math", "bio", "common-room")):
        return "research"
    if any(k in txt for k in ("code", "mcp", "security", "plugin", "api", "winui", "aspnet", "chatgpt", "zoom")):
        return "coding"
    return "productivity"


def make_svg_icon(slug: str, label: str, color: str, dest: Path) -> None:
    text = (label or slug[:2]).upper()[:2]
    font_size = "26" if len(text) == 1 else "22"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" fill="none">\n'
        f'  <rect width="64" height="64" rx="16" fill="{color}" fill-opacity="0.14"/>\n'
        f'  <rect x="1.5" y="1.5" width="61" height="61" rx="14.5" stroke="{color}" stroke-opacity="0.35" stroke-width="3"/>\n'
        f'  <text x="32" y="40" text-anchor="middle" font-family="system-ui,-apple-system,sans-serif" font-size="{font_size}" font-weight="700" fill="{color}">{text}</text>\n'
        f'</svg>\n'
    )
    dest.write_text(svg, encoding="utf-8")


def _write_zip_entry(zf: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    zi = zipfile.ZipInfo(arcname, date_time=(2026, 11, 19, 0, 0, 0))
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    zf.writestr(zi, data)


def _iter_files(root: Path, max_bytes: int = 4 * 1024 * 1024) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in IGNORE_DIR_NAMES for part in rel.parts) or p.name in IGNORE_FILE_NAMES:
            continue
        if p.stat().st_size > max_bytes:
            continue
        out.append((rel.as_posix(), p))
    return out


def discover_source_packages(src: dict[str, Any], repo_path: Path) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    excludes = set(src.get("exclude", []))
    slug_overrides = src.get("slugOverrides", {})

    if src["mode"] == "skills-dir":
        seen_names: set[str] = set()
        for rel_sub in src["paths"]:
            sub_dir = repo_path / rel_sub
            if not sub_dir.exists():
                continue
            for item in sorted(sub_dir.iterdir()):
                if not item.is_dir() or item.name in excludes or item.name.startswith("."):
                    continue
                if src.get("dedupeNames") and item.name in seen_names:
                    continue
                skill_md = item / "SKILL.md"
                if not skill_md.exists():
                    continue
                ok_fm, fm = parse_frontmatter(skill_md)
                if not ok_fm:
                    continue
                files = _iter_files(item)
                if not src.get("allowSingleMd") and len(files) < 2:
                    continue
                if security_scan_dir(item):
                    continue
                seen_names.add(item.name)
                slug = slug_overrides.get(item.name, item.name)
                discovered.append({
                    "slug": slug,
                    "kind": "skill",
                    "name": fm.get("name", item.name),
                    "description": fm.get("description", ""),
                    "rel_url_path": item.relative_to(repo_path).as_posix(),
                    "skill_dirs": [(item.name, item)],
                })

    elif src["mode"] == "claude-plugins":
        prefix = src.get("slugPrefix", "")
        for rel_sub in src["paths"]:
            base = repo_path if rel_sub == "." else (repo_path / rel_sub)
            if not base.exists():
                continue
            for item in sorted(base.iterdir()):
                if not item.is_dir() or item.name in excludes or item.name.startswith("."):
                    continue
                if not (item / ".claude-plugin" / "plugin.json").exists():
                    continue
                skill_mds = sorted(item.rglob("SKILL.md"))
                if not skill_mds:
                    continue
                if security_scan_dir(item):
                    continue
                pmeta = json.loads((item / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
                raw_slug = item.name
                slug = raw_slug if not prefix or raw_slug.startswith(prefix.rstrip("-")) else f"{prefix}{raw_slug}"
                slug = slug_overrides.get(raw_slug, slug)

                if len(skill_mds) == 1:
                    sdir = skill_mds[0].parent
                    ok_fm, fm = parse_frontmatter(skill_mds[0])
                    discovered.append({
                        "slug": slug,
                        "kind": "skill",
                        "name": pmeta.get("name") or fm.get("name") or raw_slug,
                        "description": pmeta.get("description") or fm.get("description") or "",
                        "rel_url_path": item.relative_to(repo_path).as_posix(),
                        "skill_dirs": [(sdir.name, sdir)],
                    })
                else:
                    sdirs = []
                    for smd in skill_mds:
                        ok_fm, _ = parse_frontmatter(smd)
                        if ok_fm:
                            sdirs.append((smd.parent.name, smd.parent))
                    if not sdirs:
                        continue
                    discovered.append({
                        "slug": slug,
                        "kind": "pack",
                        "name": pmeta.get("name") or raw_slug,
                        "description": pmeta.get("description") or "",
                        "rel_url_path": item.relative_to(repo_path).as_posix(),
                        "skill_dirs": sdirs,
                    })
    return discovered


def build_entry(
    pkg: dict[str, Any],
    repo_meta: dict[str, Any],
    existing_entry: dict[str, Any] | None,
    override: dict[str, Any] | None,
    default_section: str,
    skills_out: Path,
) -> dict[str, Any]:
    slug = pkg["slug"]
    ov = override or {}
    ex = existing_entry or {}

    name = ov.get("name") or ex.get("name") or pkg["name"]
    desc = ov.get("description") or ex.get("description") or pkg["description"]
    tagline = ov.get("tagline") or ex.get("tagline") or desc[:28]
    cat = ov.get("category") or ex.get("category") or infer_category(slug, pkg["description"])
    if cat not in VALID_CATEGORIES:
        cat = "other"
    section = ov.get("section") or ex.get("section") or default_section
    featured = ov.get("featured") if "featured" in ov else ex.get("featured", section == "for-you")
    icon_label = ov.get("iconLabel") or "".join(w[0] for w in re.split(r"[-_\s]+", slug) if w)[:2] or slug[:2]

    icon_path = skills_out / f"{slug}.icon.svg"
    make_svg_icon(slug, icon_label, CATEGORY_COLORS.get(cat, "#3b82f6"), icon_path)

    zip_path = skills_out / f"{slug}.zip"
    file_list: list[str] = []
    kind = pkg["kind"]

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if kind == "skill":
            _, sdir = pkg["skill_dirs"][0]
            for rel_posix, fp in _iter_files(sdir):
                _write_zip_entry(zf, rel_posix, fp.read_bytes())
                file_list.append(rel_posix)
        else:
            child_names = []
            seen_c = set()
            for cname, sdir in pkg["skill_dirs"]:
                cslug = re.sub(r"[^a-z0-9-]+", "-", cname.lower()).strip("-") or "skill"
                if cslug in seen_c:
                    idx = 2
                    while f"{cslug}-{idx}" in seen_c:
                        idx += 1
                    cslug = f"{cslug}-{idx}"
                seen_c.add(cslug)
                full_c = f"{slug}-{cslug}"
                child_names.append(full_c)
                for rel_posix, fp in _iter_files(sdir):
                    arc = f"skills/{full_c}/{rel_posix}"
                    _write_zip_entry(zf, arc, fp.read_bytes())
                    file_list.append(arc)
            bullets = "\n".join(f"- `{cn}`" for cn in child_names)
            safe_desc = desc.replace('"', "'")
            root_md = (
                f"---\nname: {slug}\ndescription: \"{safe_desc}\"\n---\n\n"
                f"# {name}\n\n{desc}\n\nSource: {repo_meta['repository']}\n\n"
                f"## Included Skills ({len(child_names)})\n\n{bullets}\n"
            )
            _write_zip_entry(zf, "SKILL.md", root_md.encode("utf-8"))
            file_list.insert(0, "SKILL.md")

    file_list = sorted(set(file_list))
    sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    entry: dict[str, Any] = {
        "id": f"school-skill-{slug}",
        "versionId": f"school-skill-{slug}-v1-{sha256[:12]}",
        "slug": slug,
        "name": name,
        "tagline": tagline,
        "description": desc,
        "category": cat,
        "icon": f"skills/{slug}.icon.svg",
        "bundle": f"skills/{slug}.zip",
        "bundleSha256": sha256,
        "version": 1,
        "featured": bool(featured),
        "files": file_list,
        "creatorName": repo_meta["creatorName"],
        "kind": kind,
        "stars": repo_meta["stars"] or ex.get("stars", 0),
        "section": section,
        "source": {
            "provider": repo_meta["provider"],
            "repository": repo_meta["repository"],
            "commit": repo_meta["commit"],
            "url": f"{repo_meta['repository']}/tree/{repo_meta['commit']}/{pkg['rel_url_path']}",
        },
    }
    if kind == "pack":
        entry["childCount"] = len(pkg["skill_dirs"])
    lic = repo_meta.get("license") or ex.get("license")
    if lic and lic != "NOASSERTION":
        entry["license"] = lic
    return entry


def verify_catalog(repo_root: Path) -> tuple[int, int, int]:
    cat = json.loads((repo_root / "catalog.json").read_text(encoding="utf-8"))
    skills = cat["skills"]
    seen_slugs = set()
    for e in skills:
        slug = e["slug"]
        assert slug not in seen_slugs, f"Duplicate slug: {slug}"
        seen_slugs.add(slug)
        bpath = repo_root / e["bundle"]
        ipath = repo_root / e["icon"]
        assert bpath.exists(), f"Missing bundle: {bpath}"
        assert ipath.exists(), f"Missing icon: {ipath}"
        sha = hashlib.sha256(bpath.read_bytes()).hexdigest()
        assert sha == e["bundleSha256"], f"SHA mismatch for {slug}"
        with zipfile.ZipFile(bpath, "r") as zf:
            names = sorted({n for n in zf.namelist() if not n.endswith("/")})
            assert names == sorted(set(e["files"])), f"Files mismatch for {slug}"
        if e.get("kind") == "pack":
            child_mds = [f for f in e["files"] if f.startswith("skills/") and f.endswith("/SKILL.md") and f.count("/") == 2]
            assert len(child_mds) == e.get("childCount"), f"childCount mismatch for {slug}"
    packs = sum(1 for s in skills if s.get("kind") == "pack")
    children = sum(int(s.get("childCount", 0)) for s in skills if s.get("kind") == "pack")
    standalone = len(skills) - packs
    return len(skills), packs, children


def update_readme(repo_root: Path, total: int, packs: int, children: int) -> None:
    standalone = total - packs
    readme_path = repo_root / "README.md"
    txt = readme_path.read_text(encoding="utf-8")
    txt = re.sub(
        r"- \*\*Skill Catalog Entries \(`catalog\.json`\)\*\*: .*?\n  - \*\*Skill Packs\*\*: .*?\n  - \*\*Standalone & Curated Bot Skills\*\*: .*?\n",
        f"- **Skill Catalog Entries (`catalog.json`)**: {total} total\n"
        f"  - **Skill Packs**: {packs} packs ({children} embedded child skills)\n"
        f"  - **Standalone & Curated Bot Skills**: {standalone} skills ({standalone - 40} GitHub standalone + 40 Chinese-localized Bot dependency skills by `sean`)\n",
        txt,
        count=1,
    )
    if "## Automated Official Upstream Sync" not in txt:
        txt += (
            "\n## Automated Official Upstream Sync\n\n"
            "- Official upstream repositories mirrored automatically via `upstream-sources.json`, `scripts/sync_upstream.py`, and `.github/workflows/sync-skills.yml`:\n"
            "  - `anthropics/skills`\n"
            "  - `anthropics/knowledge-work-plugins`\n"
            "  - `anthropics/claude-plugins-official`\n"
            "  - `openai/skills`\n"
        )
    readme_path.write_text(txt, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync official upstream skill repos into school-catalog")
    parser.add_argument("--cache-dir", type=Path, default=None, help="Directory to cache upstream git clones")
    parser.add_argument("--proxy", type=str, default=None, help="Optional HTTP/HTTPS proxy URL")
    parser.add_argument("--apply", action="store_true", help="Write updated bundles, catalog.json, and README.md")
    parser.add_argument("--refresh-existing", action="store_true", help="Rebuild existing official entries even if already present")
    parser.add_argument("--verify-only", action="store_true", help="Only verify current catalog.json integrity")
    args = parser.parse_args()

    if args.verify_only:
        total, packs, children = verify_catalog(REPO_ROOT)
        print(f"Verified OK: {total} entries ({packs} packs with {children} embedded child skills, {total - packs} standalone)")
        return

    proxy = args.proxy or _proxy_env()
    sources_cfg = json.loads((REPO_ROOT / "upstream-sources.json").read_text(encoding="utf-8"))
    overrides_cfg = json.loads((REPO_ROOT / "catalog-overrides.json").read_text(encoding="utf-8")).get("overrides", {})
    catalog_path = REPO_ROOT / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    existing_by_slug = {s["slug"]: s for s in catalog["skills"]}

    tmp_ctx = None
    if args.cache_dir:
        cache_dir = args.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
    else:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="school-upstream-")
        cache_dir = Path(tmp_ctx.name)

    try:
        skills_out = REPO_ROOT / "skills"
        synced_slugs: set[str] = set()
        added, updated, skipped = 0, 0, 0

        for src in sources_cfg["sources"]:
            repo_path, repo_meta = ensure_repo_checkout(src, cache_dir, proxy)
            pkgs = discover_source_packages(src, repo_path)
            print(f"[{src['id']}] discovered {len(pkgs)} valid official packages (stars={repo_meta['stars']}, commit={repo_meta['commit'][:8]})")
            for pkg in pkgs:
                slug = pkg["slug"]
                if slug in synced_slugs:
                    continue
                synced_slugs.add(slug)
                ex = existing_by_slug.get(slug)
                if ex is not None and not args.refresh_existing:
                    # Keep existing main entry untouched unless upstream commit changed & refresh requested
                    skipped += 1
                    continue
                if not args.apply:
                    print(f"  [dry-run] would {'update' if ex else 'add'}: {slug} ({pkg['kind']}, children={len(pkg['skill_dirs'])})")
                    continue
                entry = build_entry(pkg, repo_meta, ex, overrides_cfg.get(slug), src.get("defaultSection", "new"), skills_out)
                if ex is not None:
                    updated += 1
                else:
                    added += 1
                existing_by_slug[slug] = entry

        if args.apply:
            section_rank = {"hero": 0, "for-you": 1, "new": 2, "catalog": 3}
            all_entries = list(existing_by_slug.values())
            all_entries.sort(key=lambda e: (
                section_rank.get(e.get("section", "catalog"), 9),
                -(int(e.get("stars", 0)) if e.get("stars") is not None else -1),
                e.get("slug", ""),
            ))
            catalog["skills"] = all_entries
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            total, packs, children = verify_catalog(REPO_ROOT)
            update_readme(REPO_ROOT, total, packs, children)
            print(f"Sync complete! added={added}, updated={updated}, kept_existing={skipped} | total={total} ({packs} packs, {children} embedded, {total - packs} standalone)")
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    main()
