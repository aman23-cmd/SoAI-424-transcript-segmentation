import csv, json, urllib.parse, urllib.request

path = "data/videos.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8")))
for r in rows:
    if r["title"].strip():
        continue
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(r["url"], safe="")
    try:
        data = json.load(urllib.request.urlopen(url, timeout=15))
        r["title"] = data["title"]
        print(r["video_id"], "|", data["title"], "|", data["author_name"])
    except Exception as e:
        print(r["video_id"], "FAILED", e)

with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["video_id", "title", "url", "subject", "licence", "split"])
    w.writeheader()
    w.writerows(rows)