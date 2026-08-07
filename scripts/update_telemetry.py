#!/usr/bin/env python3
"""Generate the profile telemetry card from the GitHub REST API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = os.environ.get("GITHUB_USERNAME", "007-Akira")
OUTPUT = Path(os.environ.get("TELEMETRY_OUTPUT", "assets/github-telemetry.svg"))
API = "https://api.github.com"


def get_json(path: str) -> tuple[object, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-telemetry",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API}{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response), dict(response.headers.items())


def fetch_repositories() -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        data, _ = get_json(
            f"/users/{USERNAME}/repos?type=owner&sort=full_name&per_page=100&page={page}"
        )
        if not isinstance(data, list):
            raise TypeError("GitHub repositories response was not a list")
        repositories.extend(data)
        if len(data) < 100:
            return repositories
        page += 1


def compact(value: int) -> str:
    if value < 1_000:
        return str(value)
    if value < 1_000_000:
        return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return f"{value / 1_000_000:.1f}M".replace(".0M", "M")


def render(user: dict, repositories: list[dict]) -> str:
    # Stars on forks belong to the upstream project, so only source repositories
    # are included in totals attributed to this profile.
    sources = [repo for repo in repositories if not repo.get("fork")]
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in sources)
    forks = sum(int(repo.get("forks_count", 0)) for repo in sources)
    metrics = (
        ("TOTAL STARS GAINED", compact(stars), "#ffd166"),
        ("PUBLIC REPOSITORIES", compact(len(repositories)), "#00dbe7"),
        ("REPOSITORY FORKS", compact(forks), "#b600f8"),
        ("FOLLOWERS", compact(int(user.get("followers", 0))), "#34fc0d"),
    )
    blocks = []
    for index, (label, value, colour) in enumerate(metrics):
        x = 24 + index * 122
        blocks.append(
            f'<text x="{x}" y="91" fill="{colour}" font-size="27" '
            f'font-weight="700">{value}</text>'
            f'<text x="{x}" y="112" fill="#849495" font-size="9">{label}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 200" role="img" aria-labelledby="title desc">
  <title id="title">{USERNAME} GitHub telemetry</title>
  <desc id="desc">Live GitHub statistics including {stars} total stars gained across source repositories.</desc>
  <defs>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#173638"/></pattern>
    <style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}.p{{animation:p 3s ease-in-out infinite}}@keyframes p{{50%{{opacity:.35}}}}@media(prefers-reduced-motion:reduce){{.p{{animation:none}}}}</style>
  </defs>
  <rect width="520" height="200" rx="12" fill="#0d1515"/>
  <rect width="520" height="200" rx="12" fill="url(#grid)" opacity=".4"/>
  <rect x="1" y="1" width="518" height="198" rx="11" fill="none" stroke="#3a494b"/>
  <circle cx="22" cy="22" r="5" fill="#34fc0d" class="p"/>
  <text x="38" y="28" fill="#00dbe7" font-size="14" font-weight="700">GITHUB_TELEMETRY.dat // ONLINE</text>
  <path d="M18 43H502" stroke="#253638"/>
  <text x="24" y="62" fill="#849495" font-size="10">PUBLIC REPOSITORY SIGNALS // AUTO-REFRESHED DAILY</text>
  {''.join(blocks)}
  <path d="M24 132H496" stroke="#253638"/>
  <text x="24" y="155" fill="#849495" font-size="10">UPLINK</text>
  <text x="24" y="178" fill="#e1fdff" font-size="15">github.com/{USERNAME}</text>
  <text x="496" y="178" text-anchor="end" fill="#34fc0d" font-size="11">SIGNAL VERIFIED</text>
  <path d="M24 188h182" stroke="#00dbe7" stroke-width="3"/><path d="M206 188h110" stroke="#b600f8" stroke-width="3"/><path d="M316 188h72" stroke="#34fc0d" stroke-width="3"/><path d="M388 188h108" stroke="#ffd166" stroke-width="3"/>
</svg>
'''


def main() -> None:
    user, _ = get_json(f"/users/{USERNAME}")
    if not isinstance(user, dict):
        raise TypeError("GitHub user response was not an object")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(user, fetch_repositories()), encoding="utf-8")
    print(f"Updated {OUTPUT}")


if __name__ == "__main__":
    main()
