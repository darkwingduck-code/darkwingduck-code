#!/usr/bin/env python3
"""Generate a dependency-free language summary for a GitHub profile."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = os.environ.get("GITHUB_USERNAME", "darkwingduck-code")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
COLORS = {
    "Python": "#3572A5",
    "C++": "#f34b7d",
    "C#": "#178600",
    "C": "#555555",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "Shell": "#89e051",
    "Ruby": "#701516",
    "MATLAB": "#e16737",
    "Jupyter Notebook": "#DA5B0B",
}


def api(path: str):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-language-summary"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def collect() -> Counter[str]:
    totals: Counter[str] = Counter()
    page = 1
    while True:
        if TOKEN:
            path = f"/user/repos?visibility=all&affiliation=owner&per_page=100&page={page}"
        else:
            path = f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
        repos = api(path)
        if not repos:
            break
        for repo in repos:
            if repo["fork"] or repo["archived"]:
                continue
            totals.update(api(f"/repos/{USERNAME}/{repo['name']}/languages"))
        page += 1
    return totals


def render_svg(totals: Counter[str]) -> str:
    items = totals.most_common(8)
    total = sum(totals.values()) or 1
    rows = []
    for index, (language, size) in enumerate(items):
        percentage = size / total * 100
        y = 90 + index * 28
        color = COLORS.get(language, "#8b949e")
        rows.append(
            f'<circle cx="28" cy="{y - 5}" r="6" fill="{color}"/>'
            f'<text x="44" y="{y}" class="label">{language}</text>'
            f'<text x="490" y="{y}" text-anchor="end" class="value">{percentage:.1f}%</text>'
        )
    height = 112 + len(items) * 28
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="{height}" role="img" aria-label="Language composition">
<style>
  .card {{ fill: #ffffff; stroke: #d0d7de; }}
  .title {{ font: 600 18px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #1f2328; }}
  .subtitle,.value {{ font: 12px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #656d76; }}
  .label {{ font: 600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #1f2328; }}
  @media (prefers-color-scheme: dark) {{
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .title,.label {{ fill: #e6edf3; }}
    .subtitle,.value {{ fill: #8b949e; }}
  }}
</style>
<rect class="card" x="0.5" y="0.5" width="519" height="{height - 1}" rx="10"/>
<text x="24" y="34" class="title">Repository language composition</text>
<text x="24" y="56" class="subtitle">Public + private aggregate · forks and archives excluded</text>
{''.join(rows)}
</svg>'''


def main() -> None:
    totals = collect()
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    total = sum(totals.values()) or 1
    summary = {
        "username": USERNAME,
        "method": "GitHub Linguist bytes across accessible non-fork, non-archived repositories",
        "languages": [
            {"name": name, "bytes": size, "percentage": round(size / total * 100, 2)}
            for name, size in totals.most_common()
        ],
    }
    (assets / "languages.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (assets / "languages.svg").write_text(render_svg(totals), encoding="utf-8")


if __name__ == "__main__":
    main()
