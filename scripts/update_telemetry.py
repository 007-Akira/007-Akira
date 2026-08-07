#!/usr/bin/env python3
"""Generate the profile telemetry card from the GitHub REST API."""

from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = os.environ.get("GITHUB_USERNAME", "007-Akira")
OUTPUT = Path(os.environ.get("TELEMETRY_OUTPUT", "assets/github-telemetry.svg"))
STREAK_OUTPUT = Path(os.environ.get("STREAK_OUTPUT", "assets/github-streak.svg"))
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


def fetch_contributions() -> tuple[int, int]:
    request = Request(
        f"https://github.com/users/{USERNAME}/contributions",
        headers={"User-Agent": "github-profile-telemetry"},
    )
    with urlopen(request, timeout=30) as response:
        page = response.read().decode("utf-8")

    total_match = re.search(
        r'<h2[^>]+id="js-contribution-activity-description"[^>]*>\s*([\d,]+)\s+contributions',
        page,
    )
    if not total_match:
        raise ValueError("Could not find the contribution total")
    total = int(total_match.group(1).replace(",", ""))

    levels = {
        date.fromisoformat(day): int(level)
        for day, level in re.findall(
            r'data-date="(\d{4}-\d{2}-\d{2})"[^>]+data-level="(\d)"', page
        )
    }
    if not levels:
        raise ValueError("Could not find contribution calendar days")

    # A streak stays current through today or yesterday, matching the familiar
    # GitHub streak-card behavior before a day has ended.
    cursor = min(date.today(), max(levels))
    if levels.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    streak = 0
    while levels.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return total, streak


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


def render_streak(total: int, streak: int) -> str:
    day_word = "DAY" if streak == 1 else "DAYS"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 200" role="img" aria-labelledby="title desc">
  <title id="title">{USERNAME} contribution streak</title>
  <desc id="desc">Current contribution streak of {streak} days and {total} total contributions in the last year.</desc>
  <defs>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#173638"/></pattern>
    <radialGradient id="fire-glow"><stop stop-color="#ffb000" stop-opacity=".28"/><stop offset="1" stop-color="#ff5a00" stop-opacity="0"/></radialGradient>
    <linearGradient id="fire" x1="0" y1="1" x2="0" y2="0"><stop stop-color="#b600f8"/><stop offset=".48" stop-color="#ff5a00"/><stop offset="1" stop-color="#ffd166"/></linearGradient>
    <style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}.p{{animation:p 3s ease-in-out infinite}}.f{{animation:f 1.8s ease-in-out infinite;transform-origin:130px 110px}}@keyframes p{{50%{{opacity:.35}}}}@keyframes f{{50%{{transform:scale(1.04);opacity:.82}}}}@media(prefers-reduced-motion:reduce){{.p,.f{{animation:none}}}}</style>
  </defs>
  <rect width="520" height="200" rx="12" fill="#0d1515"/>
  <rect width="520" height="200" rx="12" fill="url(#grid)" opacity=".4"/>
  <rect x="1" y="1" width="518" height="198" rx="11" fill="none" stroke="#3a494b"/>
  <circle cx="22" cy="22" r="5" fill="#34fc0d" class="p"/>
  <text x="38" y="28" fill="#00dbe7" font-size="14" font-weight="700">CONTRIBUTION_STREAK.dat // ONLINE</text>
  <path d="M18 43H502" stroke="#253638"/>
  <text x="130" y="68" text-anchor="middle" fill="#849495" font-size="11">CURRENT STREAK</text>
  <circle cx="130" cy="108" r="53" fill="url(#fire-glow)" class="f"/>
  <path d="M83 108c-9-13 1-24 9-30-1 8 4 12 8 8 5-5 1-13 9-22 1 10 13 13 13 26 0 14-10 25-23 25-7 0-12-2-16-7z" fill="url(#fire)" opacity=".92" class="f"/>
  <path d="M177 108c9-13-1-24-9-30 1 8-4 12-8 8-5-5-1-13-9-22-1 10-13 13-13 26 0 14 10 25 23 25 7 0 12-2 16-7z" fill="url(#fire)" opacity=".92" class="f"/>
  <circle cx="76" cy="72" r="2.5" fill="#ffd166" class="p"/><circle cx="184" cy="78" r="2" fill="#ff5a00" class="p"/>
  <circle cx="130" cy="108" r="38" fill="#0d1515" stroke="url(#fire)" stroke-width="2"/>
  <text x="130" y="119" text-anchor="middle" fill="#e1fdff" font-size="42" font-weight="700">{streak}</text>
  <text x="130" y="140" text-anchor="middle" fill="#34fc0d" font-size="11">{day_word}</text>
  <path d="M260 59V153" stroke="#253638"/>
  <text x="390" y="68" text-anchor="middle" fill="#849495" font-size="11">TOTAL CONTRIBUTIONS</text>
  <text x="390" y="119" text-anchor="middle" fill="#e1fdff" font-size="42" font-weight="700">{compact(total)}</text>
  <text x="390" y="140" text-anchor="middle" fill="#b600f8" font-size="11">LAST 365 DAYS</text>
  <text x="24" y="174" fill="#849495" font-size="10">AUTO-REFRESHED DAILY</text>
  <text x="496" y="174" text-anchor="end" fill="#34fc0d" font-size="10">CALENDAR SYNCED</text>
  <path d="M24 188h182" stroke="#00dbe7" stroke-width="3"/><path d="M206 188h110" stroke="#b600f8" stroke-width="3"/><path d="M316 188h180" stroke="#34fc0d" stroke-width="3"/>
</svg>
'''


def main() -> None:
    user, _ = get_json(f"/users/{USERNAME}")
    if not isinstance(user, dict):
        raise TypeError("GitHub user response was not an object")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(user, fetch_repositories()), encoding="utf-8")
    total, streak = fetch_contributions()
    STREAK_OUTPUT.write_text(render_streak(total, streak), encoding="utf-8")
    print(f"Updated {OUTPUT} and {STREAK_OUTPUT}")


if __name__ == "__main__":
    main()
