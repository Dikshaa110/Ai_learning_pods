"""Lightweight crew.ai-style orchestrator.

This module simulates an agentic flow by running small steps sequentially:
- chunk the transcript
- call the model (or fallback) for each chunk to produce partial outputs
- aggregate partial outputs into final materials
- basic retry logic for transient errors

The goal is to provide a place to plug a real crew.ai integration later without changing the rest
of the codebase.
"""
from typing import List
import time
import json
import os
from gemini_client import generate_materials

# Optional crew.ai integration: if CREW_API_KEY is set, we'll delegate orchestration
USE_CREW = bool(os.environ.get('CREW_API_KEY'))
if USE_CREW:
    from crew_client import create_and_run_workflow


def _chunk_text(text: str, max_chars: int = 3000) -> List[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        start = end
    return chunks


def _safe_call_generate(chunk: str, topic: str, retries: int = 2, backoff: float = 0.8):
    for attempt in range(1, retries + 1):
        try:
            # generate_materials expects full transcript, but we call it per-chunk to simulate stepwise work
            out = generate_materials(chunk, topic)
            return out
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(backoff * attempt)
    return None


def orchestrate_agent_flow(topic: str, transcript: str = '', youtube_url: str = None) -> dict:
    """Run a simple multi-step flow over transcript chunks and merge results.

    Returns a materials dict similar to generate_materials.
    """
    # If crew.ai configured, delegate orchestration to crew.ai (remote workflow)
    if USE_CREW:
        try:
            resp = create_and_run_workflow(topic=topic, transcript=transcript, youtube_url=youtube_url)
            # Expect crew.ai response to contain materials similarly shaped to our local output
            if isinstance(resp, dict) and resp.get('materials'):
                return resp.get('materials')
        except Exception:
            # If remote orchestrator fails, fallback to local orchestration
            pass

    # If transcript is empty, call generate on empty to let fallback produce something
    if not transcript:
        return generate_materials('', topic)

    chunks = _chunk_text(transcript)
    partial_summaries = []
    partial_flashcards = []
    partial_quiz = []

    for i, ch in enumerate(chunks):
        try:
            out = _safe_call_generate(ch, topic)
        except Exception:
            # if a chunk fails, skip it
            continue

        # The model might return a dict or a text summary; handle common cases
        if isinstance(out, dict):
            s = out.get('summary')
            if s:
                partial_summaries.append(s)
            partial_flashcards.extend(out.get('flashcards', []))
            partial_quiz.extend(out.get('quiz', []))
        else:
            # treat it as text summary
            partial_summaries.append(str(out))

    # Merge summaries by joining and asking the generator to synthesize (here: simple join)
    merged_summary = '\n\n'.join(partial_summaries) if partial_summaries else ''

    # If merged is long, make a final generate call to synthesize (best-effort)
    try:
        final = generate_materials(merged_summary, topic)
        if isinstance(final, dict) and final.get('summary'):
            final_summary = final.get('summary')
            final_flashcards = final.get('flashcards', []) + partial_flashcards
            final_quiz = final.get('quiz', []) + partial_quiz
        else:
            final_summary = merged_summary
            final_flashcards = partial_flashcards
            final_quiz = partial_quiz
    except Exception:
        final_summary = merged_summary
        final_flashcards = partial_flashcards
        final_quiz = partial_quiz

    study_plan = {
        'levels': [
            {'level': 'Beginner', 'duration_days': 7, 'focus': 'Key concepts and definitions'},
            {'level': 'Intermediate', 'duration_days': 14, 'focus': 'Practice problems and examples'},
            {'level': 'Mastery', 'duration_days': 30, 'focus': 'Projects and advanced topics'}
        ]
    }

    return {
        'summary': final_summary,
        'flashcards': final_flashcards,
        'quiz': final_quiz,
        'study_plan': study_plan
    }
