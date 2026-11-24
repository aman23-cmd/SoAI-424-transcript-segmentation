import csv

path = "data/videos.csv"

rows = list(csv.DictReader(open(path, encoding="utf-8")))

for r in rows:
    title = r["title"].lower()

    if r["subject"].strip():
        continue

    if "python" in title:
        if "data structures" in title or "linked list" in title or "tree" in title:
            r["subject"] = "Data Structures"
        else:
            r["subject"] = "Python"

    elif "java" in title:
        r["subject"] = "Java"

    elif "dbms" in title or "database" in title:
        r["subject"] = "DBMS"

    elif "object oriented" in title or "oop" in title:
        r["subject"] = "Object-Oriented Programming"

    else:
        r["subject"] = "Computer Science"

with open(path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["video_id", "title", "url", "subject", "licence", "split"]
    )
    writer.writeheader()
    writer.writerows(rows)

print("Subjects filled successfully!")