#!/usr/bin/env python3
"""Generate a dependency-free language summary for a GitHub profile."""

from __future__ import annotations

import json
import os
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


USERNAME = os.environ.get("GITHUB_USERNAME", "darkwingduck-code")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178C6",
    "PowerShell": "#5391FE",
    "JavaScript": "#D4B830",
    "TeX": "#3D6117",
    "Rust": "#DEA584",
    "CSS": "#663399",
    "HTML": "#E34C26",
    "C++": "#F34B7D",
    "C#": "#178600",
    "C": "#555555",
    "Shell": "#89E051",
    "Ruby": "#701516",
    "MATLAB": "#E16737",
    "Jupyter Notebook": "#DA5B0B",
}


def api(path: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-language-summary",
        "X-GitHub-Api-Version": "2022-11-28",
    }
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
    bar_x = 24.0
    bar_width = 472.0
    cursor = bar_x
    segments = []
    legend = []

    for index, (language, size) in enumerate(items):
        safe_language = escape(language)
        percentage = size / total * 100
        color = COLORS.get(language, "#8B949E")
        width = bar_width * size / total
        segments.append(
            f'<rect x="{cursor:.2f}" y="72" width="{width:.2f}" height="14" fill="{color}">'
            f'<title>{safe_language}: {percentage:.1f}%</title></rect>'
        )
        cursor += width

        column = index // 4
        row = index % 4
        x = 24 + column * 248
        y = 119 + row * 30
        legend.append(
            f'<circle cx="{x + 6}" cy="{y - 5}" r="6" fill="{color}"/>'
            f'<text x="{x + 20}" y="{y}" class="label">{safe_language}</text>'
            f'<text x="{x + 224}" y="{y}" text-anchor="end" class="value">{percentage:.1f}%</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="266" viewBox="0 0 520 266" role="img" aria-labelledby="title desc">
<title id="title">Repository language composition</title>
<desc id="desc">Top languages by GitHub Linguist bytes across accessible non-fork, non-archived repositories.</desc>
<style>
  .card {{ fill: #ffffff; stroke: #d0d7de; }}
  .bar-background {{ fill: #eaeef2; }}
  .title {{ font: 600 18px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #1f2328; }}
  .subtitle,.value,.footer {{ font: 12px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #656d76; }}
  .label {{ font: 600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #1f2328; }}
  @media (prefers-color-scheme: dark) {{
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .bar-background {{ fill: #21262d; }}
    .title,.label {{ fill: #e6edf3; }}
    .subtitle,.value,.footer {{ fill: #8b949e; }}
  }}
</style>
<rect class="card" x="0.5" y="0.5" width="519" height="265" rx="10"/>
<text id="title-text" x="24" y="34" class="title">Repository language mix</text>
<text x="24" y="55" class="subtitle">Public + private aggregate · forks and archives excluded</text>
<defs><clipPath id="bar-clip"><rect x="24" y="72" width="472" height="14" rx="7"/></clipPath></defs>
<rect class="bar-background" x="24" y="72" width="472" height="14" rx="7"/>
<g clip-path="url(#bar-clip)">{''.join(segments)}</g>
{''.join(legend)}
<text x="24" y="247" class="footer">Updated weekly · GitHub Linguist bytes · repository mix ≠ proficiency</text>
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
    (assets / "languages.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (assets / "languages.svg").write_text(render_svg(totals) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
