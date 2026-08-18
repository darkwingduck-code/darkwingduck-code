#!/usr/bin/env python3
"""Generate the rolling committed-code activity card for the profile README."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

USERNAME = os.environ.get("GITHUB_USERNAME", "darkwingduck-code")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
WINDOW_DAYS = int(os.environ.get("ACTIVITY_WINDOW_DAYS", "30"))
COLORS = {"Python": "#3572A5", "TypeScript": "#3178C6", "PowerShell": "#5391FE", "JavaScript": "#D4B830", "TeX": "#3D6117", "Rust": "#DEA584", "CSS": "#663399", "HTML": "#E34C26", "C++": "#F34B7D", "C#": "#178600", "C": "#555555", "Shell": "#89E051", "MATLAB": "#E16737", "Jupyter Notebook": "#DA5B0B", "Other": "#8B949E"}
EXTENSIONS = {".py": "Python", ".pyi": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".ps1": "PowerShell", ".psm1": "PowerShell", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".tex": "TeX", ".rs": "Rust", ".css": "CSS", ".scss": "CSS", ".html": "HTML", ".htm": "HTML", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".cs": "C#", ".c": "C", ".h": "C", ".sh": "Shell", ".bash": "Shell", ".m": "MATLAB", ".ipynb": "Jupyter Notebook"}
EXCLUDED_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock", "cargo.lock", "composer.lock"}
EXCLUDED_PARTS = {"node_modules", "vendor", "dist", "build", "coverage", ".next", "__pycache__", "generated", "fixtures", "snapshots"}


def api(path: str) -> Any:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-activity-summary", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urlopen(Request(f"https://api.github.com{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def paginated(path: str, params: dict[str, str]) -> list[Any]:
    results: list[Any] = []
    page = 1
    while True:
        query = urlencode({**params, "per_page": "100", "page": str(page)})
        try:
            batch = api(f"{path}?{query}")
        except HTTPError as error:
            if error.code == 409:
                return results
            raise
        results.extend(batch)
        if len(batch) < 100:
            return results
        page += 1


def owned_repositories() -> list[dict[str, Any]]:
    path = "/user/repos" if TOKEN else f"/users/{quote(USERNAME)}/repos"
    params = {"visibility": "all", "affiliation": "owner"} if TOKEN else {"type": "owner"}
    return [repo for repo in paginated(path, params) if not repo["fork"] and not repo["archived"] and repo.get("size", 0) > 0]


def language_for(filename: str) -> str | None:
    path = PurePosixPath(filename)
    if path.name.lower() in EXCLUDED_NAMES or {part.lower() for part in path.parts} & EXCLUDED_PARTS:
        return None
    return EXTENSIONS.get(path.suffix.lower(), "Other")


def collect(since: datetime, until: datetime) -> Counter[str]:
    totals: Counter[str] = Counter()
    dates = {"author": USERNAME, "since": since.isoformat().replace("+00:00", "Z"), "until": until.isoformat().replace("+00:00", "Z")}
    for repo in owned_repositories():
        owner, name = quote(repo["owner"]["login"]), quote(repo["name"])
        for commit in paginated(f"/repos/{owner}/{name}/commits", dates):
            detail = api(f"/repos/{owner}/{name}/commits/{commit['sha']}")
            for changed in detail.get("files", []):
                language = language_for(changed["filename"])
                if language:
                    totals[f"{language}:additions"] += changed.get("additions", 0)
                    totals[f"{language}:deletions"] += changed.get("deletions", 0)
    return totals


def render_svg(totals: Counter[str], since: datetime, until: datetime) -> str:
    languages = sorted(
        {key.rsplit(":", 1)[0] for key in totals},
        key=lambda item: totals[f"{item}:additions"] + totals[f"{item}:deletions"],
        reverse=True,
    )[:6]
    additions = sum(value for key, value in totals.items() if key.endswith(":additions"))
    deletions = sum(value for key, value in totals.items() if key.endswith(":deletions"))
    rows = []
    for index, language in enumerate(languages):
        y = 130 + index * 27
        color, safe = COLORS.get(language, COLORS["Other"]), escape(language)
        rows.append(
            f'<circle cx="30" cy="{y - 5}" r="5" fill="{color}"/>'
            f'<text x="43" y="{y}" class="label">{safe}</text>'
            f'<text x="490" y="{y}" text-anchor="end" class="value">'
            f'+{totals[f"{language}:additions"]:,} / -{totals[f"{language}:deletions"]:,}</text>'
        )
    period = f"{since.date().isoformat()} → {until.date().isoformat()}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="320" viewBox="0 0 520 320" role="img" aria-labelledby="activity-title activity-desc">
<title id="activity-title">Committed code activity by language</title>
<desc id="activity-desc">Aggregate public and private activity from {period}.</desc>
<style>
.card{{fill:#fff;stroke:#d0d7de}}.title{{font:600 18px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#1f2328}}.metric{{font:700 22px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#1f2328}}.label{{font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#1f2328}}.subtitle,.value,.footer{{font:12px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#656d76}}@media(prefers-color-scheme:dark){{.card{{fill:#0d1117;stroke:#30363d}}.title,.metric,.label{{fill:#e6edf3}}.subtitle,.value,.footer{{fill:#8b949e}}}}
</style>
<rect class="card" x=".5" y=".5" width="519" height="319" rx="10"/>
<text x="24" y="34" class="title">Committed code activity</text>
<text x="24" y="55" class="subtitle">Public + private aggregate · forks and archives excluded</text>
<text x="24" y="86" class="metric">+{additions:,}</text><text x="158" y="86" class="metric">−{deletions:,}</text>
<text x="24" y="104" class="subtitle">lines added</text><text x="158" y="104" class="subtitle">lines deleted</text>
{''.join(rows)}
<text x="24" y="300" class="footer">Period: {period} · committed diff lines, not keystrokes</text>
</svg>'''


def main() -> None:
    until = datetime.now(timezone.utc)
    since = until - timedelta(days=WINDOW_DAYS)
    totals = collect(since, until)
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "activity.svg").write_text(render_svg(totals, since, until) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
