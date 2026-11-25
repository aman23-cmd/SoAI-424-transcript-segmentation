import csv
from pathlib import Path

VIDEOS_FILE = Path("data/videos.csv")

def to_seconds(ts: str) -> int:
    parts = [int(p) for p in ts.strip().split(":")]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError("Invalid format")

def main():
    ann = input("Annotator (A1 / A2): ").strip().upper()
    if ann not in ("A1", "A2"):
        print("Please enter A1 or A2 only.")
        return

    out_file = Path(f"data/annotations_{ann}.csv")
    if not out_file.exists():
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["video_id", "boundary_time_sec", "topic_label", "annotator"])

    with open(VIDEOS_FILE, encoding="utf-8") as f:
        videos = [r for r in csv.DictReader(f) if r["video_id"].strip()]

    while True:
        counts = {}
        with open(out_file, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                counts[r["video_id"]] = counts.get(r["video_id"], 0) + 1

        print("\n--- Videos ---")
        for idx, v in enumerate(videos, 1):
            vid = v["video_id"].strip()
            print(f"{idx:2d}. {vid} ({counts.get(vid, 0)} marked) - {v['title'][:50]}")

        choice = input("\nSelect video number (or 'q' to quit): ").strip()
        if choice.lower() == "q":
            break
        if not choice.isdigit() or not (1 <= int(choice) <= len(videos)):
            print("Invalid video number.")
            continue

        vid = videos[int(choice) - 1]["video_id"].strip()
        print(f"\nSelected: {vid}  (press Enter on empty timestamp to go back)")

        while True:
            ts = input("  Timestamp (mm:ss): ").strip()
            if not ts:
                break
            try:
                sec = to_seconds(ts)
            except ValueError:
                print("  Invalid format! Example: 05:12")
                continue

            label = input("  Topic label: ").strip()
            with open(out_file, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([vid, sec, label, ann])
            print(f"  -> Saved: {vid}, {sec}s, {label}")

if __name__ == "__main__":
    main()