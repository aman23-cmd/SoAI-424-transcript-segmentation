import csv
from pathlib import Path

VIDEOS_FILE = Path("data/videos.csv")
OUT_FILE = Path("data/queries.csv")

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
    if not OUT_FILE.exists():
        with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["video_id", "question", "answer_start_sec", "answer_end_sec"])

    with open(VIDEOS_FILE, encoding="utf-8") as f:
        videos = [r for r in csv.DictReader(f) if r["video_id"].strip()]

    while True:
        counts = {}
        with open(OUT_FILE, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                vid_id = r["video_id"].strip()
                if vid_id:
                    counts[vid_id] = counts.get(vid_id, 0) + 1

        print("\n--- Videos (Target: 5 queries each) ---")
        for idx, v in enumerate(videos, 1):
            vid = v["video_id"].strip()
            print(f"{idx:2d}. {vid} ({counts.get(vid, 0)}/5) - {v['title'][:50]}")

        choice = input("\nSelect video number (or 'q' to quit): ").strip()
        if choice.lower() == "q":
            break
        if not choice.isdigit() or not (1 <= int(choice) <= len(videos)):
            print("Invalid video number.")
            continue

        vid = videos[int(choice) - 1]["video_id"].strip()
        print(f"\nSelected: {vid}  (press Enter on empty question to go back)")

        while True:
            q = input("  Question: ").strip()
            if not q:
                break

            start_ts = input("  Answer start (mm:ss): ").strip()
            end_ts = input("  Answer end (mm:ss): ").strip()
            try:
                start_sec = to_seconds(start_ts)
                end_sec = to_seconds(end_ts)
                if end_sec <= start_sec:
                    print("  Error: end time must be greater than start time.")
                    continue
            except ValueError:
                print("  Invalid time format! Example: 05:12")
                continue

            with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([vid, q, start_sec, end_sec])
            print(f"  -> Saved: {vid} [{start_sec}s - {end_sec}s]")

if __name__ == "__main__":
    main()