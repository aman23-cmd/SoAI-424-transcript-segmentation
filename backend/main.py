import os
import json
import time
import random
from urllib.parse import urlparse, parse_qs

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from sentence_transformers import SentenceTransformer
from youtube_transcript_api import YouTubeTranscriptApi

import db
import evaluation

# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in .env file. Note generation will fail.")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Smart Video Learning Assistant API")

# Initialize the database (creates tables if they don't exist)
db.init_db()

# Load the embedding model ONCE when the server starts.
print("Loading sentence embedding model... (this happens once at startup)")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model loaded successfully!")

VALID_DIFFICULTIES = ("easy", "medium", "hard", "mixed")


@app.get("/")
def read_root():
    return {"status": "Backend is running!", "message": "Smart Video Learning Assistant API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Transcript + segmentation
# ---------------------------------------------------------------------------

def extract_video_id(url: str) -> str:
    parsed_url = urlparse(url)

    if "youtu.be" in parsed_url.netloc:
        return parsed_url.path.lstrip("/")

    if "youtube.com" in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        if "v" in query_params:
            return query_params["v"][0]

    raise ValueError("Could not extract video ID from URL")


def fetch_raw_transcript(video_id: str):
    ytt_api = YouTubeTranscriptApi()
    transcript_data = ytt_api.fetch(video_id)

    return [
        {
            "text": snippet.text,
            "start": snippet.start,
            "duration": snippet.duration,
        }
        for snippet in transcript_data
    ]


def group_into_chunks(raw_segments, captions_per_chunk: int = 5):
    chunks = []
    for i in range(0, len(raw_segments), captions_per_chunk):
        group = raw_segments[i:i + captions_per_chunk]
        chunk_text = " ".join([seg["text"] for seg in group])
        chunk_start = group[0]["start"]
        last = group[-1]
        chunk_end = last["start"] + last["duration"]

        chunks.append({
            "text": chunk_text,
            "start": chunk_start,
            "end": chunk_end,
        })
    return chunks


def cosine_similarity(vec_a, vec_b):
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    return dot_product / (norm_a * norm_b)


def semantic_segment(chunks, similarity_threshold: float = 0.45,
                     min_words: int = 80, max_words: int = 250):
    if len(chunks) == 0:
        return []

    chunk_texts = [c["text"] for c in chunks]
    embeddings = embedding_model.encode(chunk_texts)

    segments = []
    current_segment_chunks = [chunks[0]]
    current_words = len(chunks[0]["text"].split())

    for i in range(1, len(chunks)):
        similarity = cosine_similarity(embeddings[i - 1], embeddings[i])
        chunk_words = len(chunks[i]["text"].split())

        topic_changed = similarity < similarity_threshold and current_words >= min_words
        too_long = current_words >= max_words

        if topic_changed or too_long:
            segments.append(current_segment_chunks)
            current_segment_chunks = [chunks[i]]
            current_words = chunk_words
        else:
            current_segment_chunks.append(chunks[i])
            current_words += chunk_words

    segments.append(current_segment_chunks)

    final_segments = []
    for seg_chunks in segments:
        combined_text = " ".join([c["text"] for c in seg_chunks])
        final_segments.append({
            "start_time": round(seg_chunks[0]["start"], 2),
            "end_time": round(seg_chunks[-1]["end"], 2),
            "text": combined_text,
            "word_count": len(combined_text.split()),
        })

    # Clamp end_time to next segment's start_time (caption durations overlap)
    for i in range(len(final_segments) - 1):
        final_segments[i]["end_time"] = min(
            final_segments[i]["end_time"], final_segments[i + 1]["start_time"]
        )

    return final_segments


def fixed_segment(chunks, words_per_segment: int = 165):
    """
    BASELINE: splits the transcript into fixed-size word windows,
    ignoring meaning. 165 words matches the average segment size of the
    semantic method, so the comparison is fair.
    """
    if len(chunks) == 0:
        return []

    groups = []
    current = []
    current_words = 0

    for c in chunks:
        current.append(c)
        current_words += len(c["text"].split())
        if current_words >= words_per_segment:
            groups.append(current)
            current = []
            current_words = 0

    if current:
        groups.append(current)

    final_segments = []
    for seg_chunks in groups:
        combined_text = " ".join([c["text"] for c in seg_chunks])
        final_segments.append({
            "start_time": round(seg_chunks[0]["start"], 2),
            "end_time": round(seg_chunks[-1]["end"], 2),
            "text": combined_text,
            "word_count": len(combined_text.split()),
        })

    for i in range(len(final_segments) - 1):
        final_segments[i]["end_time"] = min(
            final_segments[i]["end_time"], final_segments[i + 1]["start_time"]
        )

    return final_segments


# ---------------------------------------------------------------------------
# Gemini calls (retry + model fallback)
# ---------------------------------------------------------------------------

# Models to try in order. Stable models first so we don't waste time retrying
# an overloaded model on every single call.
GEMINI_MODEL_CHAIN = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]


def call_gemini_with_retry(prompt: str, max_retries_per_model: int = 3):
    """
    Calls the Gemini API with automatic retry (on temporary overload errors)
    and automatic fallback across a chain of models. If a model is permanently
    unavailable (e.g. deprecated/404), moves to the next model in the chain
    instead of giving up. Raises the last error only if every model fails.
    """
    last_error = None

    for model_name in GEMINI_MODEL_CHAIN:
        model_failed_permanently = False

        for attempt in range(max_retries_per_model):
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                last_error = e
                error_str = str(e)
                is_overload = (
                    "503" in error_str
                    or "UNAVAILABLE" in error_str
                    or "high demand" in error_str.lower()
                    or "RESOURCE_EXHAUSTED" in error_str
                    or "429" in error_str
                )
                if is_overload:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"[{model_name}] overloaded, retrying in {wait_time:.1f}s "
                          f"(attempt {attempt + 1}/{max_retries_per_model})...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[{model_name}] permanent error ({type(e).__name__}), "
                          f"moving to next model in chain...")
                    model_failed_permanently = True
                    break

        if not model_failed_permanently:
            print(f"[{model_name}] failed after {max_retries_per_model} overload retries, "
                  f"falling back to next model...")

    raise last_error


def generate_notes_for_segment(segment_text: str) -> str:
    """Sends a transcript segment to Gemini and asks for concise study notes."""
    prompt = f"""You are an educational assistant that converts lecture transcript segments into clear, concise study notes.

Given the following transcript segment from a lecture video, write structured notes as bullet points. Focus only on the key concepts, facts, and steps explained. Do not include filler words, repetition, or transcript artifacts. Keep it concise (3-6 bullet points).

Transcript segment:
\"\"\"{segment_text}\"\"\"

Notes:"""

    return call_gemini_with_retry(prompt)


def generate_quiz_for_segment(segment_text: str, difficulty: str = "medium", num_questions: int = 2):
    """
    Generates multiple-choice quiz questions from a transcript segment,
    at a specified difficulty level. Returns a list of question dicts.
    """
    prompt = f"""You are an educational assistant that creates multiple-choice quiz questions from lecture transcript segments.

Difficulty level: {difficulty}
- "easy" = direct, fact-based recall questions
- "medium" = conceptual questions requiring understanding
- "hard" = analytical questions requiring reasoning or applying the concept

Based on the transcript segment below, generate exactly {num_questions} multiple-choice question(s) at {difficulty} difficulty.

Respond with ONLY valid JSON (no markdown formatting, no backticks, no extra text) in this exact structure:
[
  {{
    "question": "question text here",
    "options": ["option A", "option B", "option C", "option D"],
    "correct_answer": "the exact text of the correct option",
    "difficulty": "{difficulty}"
  }}
]

Transcript segment:
\"\"\"{segment_text}\"\"\"
"""

    raw_text = call_gemini_with_retry(prompt)

    # Clean up in case the model wraps it in markdown code fences anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        questions = json.loads(raw_text)
    except json.JSONDecodeError:
        raise ValueError(f"Model did not return valid JSON. Raw response: {raw_text[:200]}")

    # Shuffle options so the correct answer isn't always in position A/B.
    # correct_answer is stored as text, so shuffling is safe.
    for q in questions:
        if isinstance(q.get("options"), list):
            random.shuffle(q["options"])

    return questions


def pick_difficulty(difficulty: str, index: int) -> str:
    """For 'mixed', cycle easy -> medium -> hard across segments."""
    if difficulty == "mixed":
        return ("easy", "medium", "hard")[index % 3]
    return difficulty


def compute_relevance_score(original_text: str, generated_notes: str) -> float:
    """
    Cosine similarity between sentence embeddings of the transcript segment
    and the generated notes. Range 0 (unrelated) to 1 (identical meaning).
    """
    embeddings = embedding_model.encode([original_text, generated_notes])
    score = cosine_similarity(embeddings[0], embeddings[1])
    return round(float(score), 4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/transcript")
def get_transcript(video_url: str):
    try:
        video_id = extract_video_id(video_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        segments = fetch_raw_transcript(video_id)
        full_text = " ".join([seg["text"] for seg in segments])

        return {
            "video_id": video_id,
            "segment_count": len(segments),
            "segments": segments,
            "full_text": full_text,
        }

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch transcript. Error type: {type(e).__name__}. Message: {str(e)}"
        )


@app.get("/segments")
def get_semantic_segments(video_url: str, captions_per_chunk: int = 5, similarity_threshold: float = 0.45):
    try:
        video_id = extract_video_id(video_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        raw_segments = fetch_raw_transcript(video_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch transcript. Error type: {type(e).__name__}. Message: {str(e)}"
        )

    chunks = group_into_chunks(raw_segments, captions_per_chunk=captions_per_chunk)
    segments = semantic_segment(chunks, similarity_threshold=similarity_threshold)

    return {
        "video_id": video_id,
        "raw_caption_count": len(raw_segments),
        "chunk_count": len(chunks),
        "final_segment_count": len(segments),
        "segments": segments,
    }


@app.get("/notes")
def get_notes(video_url: str, captions_per_chunk: int = 5, similarity_threshold: float = 0.45, max_segments: int = 5):
    """Transcript -> semantic segments -> AI notes for each segment."""
    try:
        video_id = extract_video_id(video_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        raw_segments = fetch_raw_transcript(video_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch transcript. Error type: {type(e).__name__}. Message: {str(e)}"
        )

    chunks = group_into_chunks(raw_segments, captions_per_chunk=captions_per_chunk)
    segments = semantic_segment(chunks, similarity_threshold=similarity_threshold)
    segments_to_process = segments[:max_segments]

    results = []
    for seg in segments_to_process:
        try:
            notes = generate_notes_for_segment(seg["text"])
        except Exception as e:
            notes = f"[Error generating notes: {type(e).__name__}: {str(e)}]"

        results.append({
            "start_time": seg["start_time"],
            "end_time": seg["end_time"],
            "transcript_text": seg["text"],
            "notes": notes,
        })

    return {
        "video_id": video_id,
        "total_segments_found": len(segments),
        "segments_processed": len(results),
        "results": results,
    }


@app.get("/quiz")
def get_quiz(
    video_url: str,
    captions_per_chunk: int = 5,
    similarity_threshold: float = 0.45,
    max_segments: int = 5,
    difficulty: str = "medium",
    questions_per_segment: int = 2,
):
    """
    Transcript -> semantic segments -> MCQ quiz for each segment.
    difficulty: easy, medium, hard, or mixed (cycles easy/medium/hard).
    """
    if difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail="difficulty must be 'easy', 'medium', 'hard', or 'mixed'")

    try:
        video_id = extract_video_id(video_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        raw_segments = fetch_raw_transcript(video_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch transcript. Error type: {type(e).__name__}. Message: {str(e)}"
        )

    chunks = group_into_chunks(raw_segments, captions_per_chunk=captions_per_chunk)
    segments = semantic_segment(chunks, similarity_threshold=similarity_threshold)
    segments_to_process = segments[:max_segments]

    results = []
    for i, seg in enumerate(segments_to_process):
        seg_difficulty = pick_difficulty(difficulty, i)
        try:
            questions = generate_quiz_for_segment(
                seg["text"], difficulty=seg_difficulty, num_questions=questions_per_segment
            )
        except Exception as e:
            questions = [{"error": f"{type(e).__name__}: {str(e)}"}]

        results.append({
            "start_time": seg["start_time"],
            "end_time": seg["end_time"],
            "transcript_text": seg["text"],
            "questions": questions,
        })

    return {
        "video_id": video_id,
        "total_segments_found": len(segments),
        "segments_processed": len(results),
        "difficulty": difficulty,
        "results": results,
    }


@app.get("/process")
def process_video(
    video_url: str,
    captions_per_chunk: int = 5,
    similarity_threshold: float = 0.45,
    max_segments: int = 5,
    difficulty: str = "medium",
    questions_per_segment: int = 2,
    mode: str = "semantic",
):
    """
    Full pipeline: transcript -> segments -> notes + quiz + relevance
    score per segment -> saved to history (SQLite).
    difficulty: easy, medium, hard, or mixed (cycles easy/medium/hard).
    mode: 'semantic' (our method) or 'baseline' (fixed-size windows).
    """
    if difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail="difficulty must be 'easy', 'medium', 'hard', or 'mixed'")

    if mode not in ("semantic", "baseline"):
        raise HTTPException(status_code=400, detail="mode must be 'semantic' or 'baseline'")

    try:
        video_id = extract_video_id(video_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        raw_segments = fetch_raw_transcript(video_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch transcript. Error type: {type(e).__name__}. Message: {str(e)}"
        )

    chunks = group_into_chunks(raw_segments, captions_per_chunk=captions_per_chunk)
    if mode == "baseline":
        segments = fixed_segment(chunks)
    else:
        segments = semantic_segment(chunks, similarity_threshold=similarity_threshold)
    segments_to_process = segments[:max_segments]

    results = []
    for i, seg in enumerate(segments_to_process):
        if i > 0:
            time.sleep(1.5)  # small gap between segments to avoid rate-limit bursts

        try:
            notes = generate_notes_for_segment(seg["text"])
            relevance_score = compute_relevance_score(seg["text"], notes)
        except Exception as e:
            notes = f"[Error generating notes: {type(e).__name__}: {str(e)}]"
            relevance_score = None

        time.sleep(0.5)  # small gap before the quiz call for this segment

        seg_difficulty = pick_difficulty(difficulty, i)
        try:
            questions = generate_quiz_for_segment(
                seg["text"], difficulty=seg_difficulty, num_questions=questions_per_segment
            )
        except Exception as e:
            questions = [{"error": f"{type(e).__name__}: {str(e)}"}]

        results.append({
            "start_time": seg["start_time"],
            "end_time": seg["end_time"],
            "transcript_text": seg["text"],
            "notes": notes,
            "relevance_score": relevance_score,
            "questions": questions,
        })

    video_history_id = db.save_processed_video(video_id, video_url, results, mode=mode)

    return {
        "video_history_id": video_history_id,
        "video_id": video_id,
        "total_segments_found": len(segments),
        "segments_processed": len(results),
        "results": results,
    }


@app.get("/history")
def get_history():
    """Returns a list of all previously processed videos."""
    return {"history": db.get_all_history()}


@app.get("/history/{video_history_id}")
def get_history_detail(video_history_id: int):
    """Returns the full saved detail (segments, notes, quiz) for one processed video."""
    detail = db.get_video_detail(video_history_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="No history found with this ID")
    return detail


@app.get("/evaluation")
def get_evaluation():
    """Aggregate stats across all processed videos (paper Results tables)."""
    return evaluation.get_evaluation_summary()