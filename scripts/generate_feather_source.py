#!/usr/bin/env python3
"""Generate a Feather/AltStore-compatible source from GitHub Release IPA assets."""
import datetime as dt
import json
import os
import re
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "owen-tariq/craft-ipad-apps")
TOKEN = os.environ.get("GH_TOKEN", "")
NAMES = ["PhotoCraft", "VectorCraft", "DesignCraft", "LightCraft", "FilmCraft", "EffectCraft", "FigCraft", "WordCraft", "GridCraft", "DeckCraft", "PdfCraft", "SoundCraft", "CADCraft"]
BASE = "https://raw.githubusercontent.com/" + REPO + "/main"
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "Craft-iPad-Feather-Source"}
if TOKEN:
    HEADERS["Authorization"] = "Bearer " + TOKEN

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as response:
        return json.load(response)

releases = []
page = 1
while True:
    batch = get(f"https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}")
    if not batch:
        break
    releases.extend(r for r in batch if not r.get("draft"))
    if len(batch) < 100:
        break
    page += 1

apps = []
for name in NAMES:
    versions = []
    seen = set()
    for release in releases:
        for asset in release.get("assets", []):
            filename = asset["name"]
            match = re.fullmatch(re.escape(name) + r"-v(\d+\.\d+\.\d+)-iPad\.ipa", filename, re.I)
            legacy = filename.lower() == (name + "-iPad.ipa").lower()
            if not match and not legacy:
                continue
            version = match.group(1) if match else "1.0.0"
            if version in seen:
                continue
            seen.add(version)
            versions.append({
                "version": version,
                "date": (asset.get("created_at") or release.get("published_at") or "2026-01-01")[:10],
                "downloadURL": asset["browser_download_url"],
                "size": asset["size"],
                "localizedDescription": f"{name} iPadOS build from {release['tag_name']}; upstream version {version if match else 'not recorded'}."
            })
    if not versions:
        continue
    versions.sort(key=lambda x: (tuple(map(int, x["version"].split("."))), x["date"]), reverse=True)
    app_id = name.lower()
    apps.append({
        "name": name,
        "bundleIdentifier": f"com.craftsuite.{app_id}",
        "developerName": "storytold / Craft iPad Apps contributors",
        "subtitle": f"{name} for iPadOS",
        "localizedDescription": f"iPadOS wrapper for {name}. Unofficial community build.",
        "iconURL": f"https://raw.githubusercontent.com/storytold/{app_id}/main/assets/app-icon/{app_id}-1024.png",
        "tintColor": "5865F2",
        "category": "productivity",
        "version": versions[0]["version"],
        "versionDate": versions[0]["date"],
        "downloadURL": versions[0]["downloadURL"],
        "size": versions[0]["size"],
        "versions": versions,
        "minOSVersion": "15.0",
    })

source = {
    "name": "Craft iPad Apps",
    "identifier": "com.craftsuite.feather.source",
    "subtitle": "13 ArtCraft iPadOS apps",
    "description": "Unofficial iPadOS IPA builds. Includes version history from GitHub Releases.",
    "iconURL": BASE + "/ios-wrapper/Sources/Assets.xcassets/AppIcon.appiconset/AppIcon.png",
    "website": "https://github.com/" + REPO,
    "sourceURL": BASE + "/feather-source.json",
    "apps": apps,
    "news": [],
}
with open("feather-source.json", "w", encoding="utf-8") as output:
    json.dump(source, output, indent=2, ensure_ascii=False)
    output.write("\n")
print("Generated Feather source with", len(apps), "apps and", sum(len(a["versions"]) for a in apps), "versions")
