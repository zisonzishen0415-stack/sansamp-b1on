#!/usr/bin/env python3
"""Query Commons imageinfo for candidate bass recordings (url/license/desc).

Titles are passed on argv to keep the URL short.
"""
import json
import os
import sys
import urllib.parse

names = sys.argv[1:]
q = urllib.parse.quote("|".join(names))
url = ("https://commons.wikimedia.org/w/api.php?action=query&titles=" + q +
       "&prop=imageinfo&iiprop=url|extmetadata&format=json")
print(url)
os.system(f'curl.exe -s -A "Mozilla/5.0" -x socks5h://127.0.0.1:10808 "{url}" '
          f'-o "{os.environ["TEMP"]}\\cm_info.json"')

d = json.load(open(os.environ["TEMP"] + r"\cm_info.json", encoding="utf-8"))
for pid, page in d.get("query", {}).get("pages", {}).items():
    ii = page.get("imageinfo", [{}])[0]
    em = ii.get("extmetadata", {})

    def g(k):
        v = em.get(k, {}).get("value", "")
        return v[:220].replace("\n", " ")

    print("=" * 70)
    print(page.get("title"))
    print("  url     :", ii.get("url"))
    print("  license :", g("LicenseShortName"))
    print("  artist  :", g("Artist"))
    print("  desc    :", g("ImageDescription"))
