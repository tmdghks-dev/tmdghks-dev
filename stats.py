"""Render 'productive time' and 'GitHub stats' cards as SVG (gist-box style).

usage: GITHUB_TOKEN=... python3 stats.py <user> <out_dir>
"""
import json, os, sys, urllib.request
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

USER, OUT = sys.argv[1], sys.argv[2]
TZ = ZoneInfo("Asia/Seoul")


def api(path, body=None):
    req = urllib.request.Request(
        "https://api.github.com/" + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                 "Accept": "application/vnd.github+json"},
    )
    return json.load(urllib.request.urlopen(req))


def search_count(q):
    return api(f"search/issues?q={q}+author:{USER}&per_page=1")["total_count"]


# commit hours (search API caps at 1000 results)
hours, total_commits = [], 0
for page in range(1, 11):
    r = api(f"search/commits?q=author:{USER}&per_page=100&page={page}")
    total_commits = r["total_count"]
    hours += [datetime.fromisoformat(i["commit"]["committer"]["date"]).astimezone(TZ).hour
              for i in r["items"]]
    if len(hours) >= total_commits or not r["items"]:
        break

buckets = [("🌞", "Morning", range(6, 12)), ("🌆", "Daytime", range(12, 18)),
           ("🌃", "Evening", range(18, 24)), ("🌙", "Night", range(0, 6))]
counts = [sum(h in rng for h in hours) for *_, rng in buckets]
n = max(sum(counts), 1)
owl = counts[2] + counts[3] > counts[0] + counts[1]

user = api("graphql", {"query": f'''{{user(login:"{USER}"){{
  repositories(ownerAffiliations:OWNER,first:100){{nodes{{stargazerCount}}}}
  repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,ISSUE]){{totalCount}}}}}}'''})["data"]["user"]
stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])


def card(title, rows, path):
    W, top, lh = 440, 58, 24
    H = top + lh * len(rows) + 22
    lines = "".join(
        f'<text x="40" y="{top + 22 + i * lh}" class="n">{i + 1}</text>'
        f'<text x="62" y="{top + 22 + i * lh}" xml:space="preserve">{escape(row)}</text>'
        for i, row in enumerate(rows))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>text{{font:13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#e6edf3}}.n{{fill:#6e7681}}.t{{font:600 15px -apple-system,Segoe UI,sans-serif;fill:#a78bfa}}</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="#0d1117" stroke="#30363d"/>
<text x="20" y="33" class="t">{escape(title)}</text>
<rect x="20" y="{top - 6}" width="{W - 40}" height="{lh * len(rows) + 14}" rx="6" fill="#161b22"/>
{lines}</svg>'''
    open(os.path.join(OUT, path), "w").write(svg)


def bar(c):
    filled = round(c / n * 15)
    return "█" * filled + "░" * (15 - filled)


card("I'm a night owl 🦉" if owl else "I'm an early bird 🐤",
     [f"{e} {name:<8}{c:>3} commits  {bar(c)} {c / n * 100:5.1f}%"
      for (e, name, _), c in zip(buckets, counts)],
     "productive-time.svg")

card("Seunghwan's GitHub Stats", [
    f"⭐ Total Stars:      {stars:>6}",
    f"➕ Total Commits:    {total_commits:>6}",
    f"🔀 Total PRs:        {search_count('type:pr'):>6}",
    f"🚩 Total Issues:     {search_count('type:issue'):>6}",
    f"📦 Contributed to:   {user['repositoriesContributedTo']['totalCount']:>6}",
], "github-stats.svg")
