import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = "history.db"


def init_db():
    """Creates the database tables if they don't already exist. Call this once at startup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            video_url TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            total_segments INTEGER,
            mode TEXT DEFAULT 'semantic'
        )
    """)

    # Migration: older databases don't have the 'mode' column yet.
    # Existing rows were all produced by the semantic method.
    cursor.execute("PRAGMA table_info(video_history)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "mode" not in existing_columns:
        cursor.execute("ALTER TABLE video_history ADD COLUMN mode TEXT DEFAULT 'semantic'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_history_id INTEGER NOT NULL,
            start_time REAL,
            end_time REAL,
            transcript_text TEXT,
            notes TEXT,
            relevance_score REAL,
            FOREIGN KEY (video_history_id) REFERENCES video_history (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_id INTEGER NOT NULL,
            question TEXT,
            options TEXT,
            correct_answer TEXT,
            difficulty TEXT,
            FOREIGN KEY (segment_id) REFERENCES segments (id)
        )
    """)

    conn.commit()
    conn.close()


def save_processed_video(video_id: str, video_url: str, segments_data: list, mode: str = "semantic"):
    """
    Saves a fully processed video (with notes, relevance scores, and quiz
    questions already attached to each segment dict) into the database.

    mode: 'semantic' (our method) or 'baseline' (fixed-size windows).

    segments_data: list of dicts, each with keys:
        start_time, end_time, transcript_text, notes, relevance_score,
        questions (list of {question, options, correct_answer, difficulty})
    Returns the video_history_id.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO video_history (video_id, video_url, processed_at, total_segments, mode) VALUES (?, ?, ?, ?, ?)",
        (video_id, video_url, datetime.now(timezone.utc).isoformat(), len(segments_data), mode),
    )
    video_history_id = cursor.lastrowid

    for seg in segments_data:
        cursor.execute(
            """INSERT INTO segments
               (video_history_id, start_time, end_time, transcript_text, notes, relevance_score)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                video_history_id,
                seg.get("start_time"),
                seg.get("end_time"),
                seg.get("transcript_text"),
                seg.get("notes"),
                seg.get("relevance_score"),
            ),
        )
        segment_id = cursor.lastrowid

        for q in seg.get("questions", []):
            if "question" not in q:
                continue  # skip error entries
            cursor.execute(
                """INSERT INTO quiz_questions
                   (segment_id, question, options, correct_answer, difficulty)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    segment_id,
                    q.get("question"),
                    json.dumps(q.get("options", [])),
                    q.get("correct_answer"),
                    q.get("difficulty"),
                ),
            )

    conn.commit()
    conn.close()
    return video_history_id


def get_all_history():
    """Returns a list of all previously processed videos (summary only)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM video_history ORDER BY processed_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_video_detail(video_history_id: int):
    """Returns full detail (segments + notes + quiz questions) for one processed video."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM video_history WHERE id = ?", (video_history_id,))
    video = cursor.fetchone()
    if video is None:
        conn.close()
        return None

    cursor.execute("SELECT * FROM segments WHERE video_history_id = ?", (video_history_id,))
    segments = cursor.fetchall()

    result_segments = []
    for seg in segments:
        seg_dict = dict(seg)
        cursor.execute("SELECT * FROM quiz_questions WHERE segment_id = ?", (seg["id"],))
        questions = cursor.fetchall()
        seg_dict["questions"] = [
            {
                "question": q["question"],
                "options": json.loads(q["options"]) if q["options"] else [],
                "correct_answer": q["correct_answer"],
                "difficulty": q["difficulty"],
            }
            for q in questions
        ]
        result_segments.append(seg_dict)

    conn.close()

    return {
        "video": dict(video),
        "segments": result_segments,
    }