
from gemini_client import generate_materials, generate_materials_fallback, call_gemini, _parse_model_output, local_generate_summary, local_generate_flashcards, local_generate_quiz
from generate_pdf import create_study_pdf
from crew_integration import orchestrate_agent_flow
import json
import re
import html


def _generate_topic_content(topic: str) -> str:
    """Generate educational content for a topic using Gemini. Falls back to structured content if API fails."""
    prompt = (
        f"You are an educational content expert. Write a comprehensive and clear explanation "
        f"about the following topic. The explanation should cover key concepts, definitions, "
        f"examples, and practical applications. Write approximately 300-400 words.\n\n"
        f"Topic: {topic}\n\n"
        f"Provide a detailed educational explanation that someone learning about this topic "
        f"for the first time can understand."
    )
    
    try:
        content = call_gemini(prompt, max_tokens=2048)
        if content and content.strip():
            return content.strip()
    except Exception as e:
        print(f"Gemini API failed, using fallback for topic '{topic}': {str(e)[:100]}")
    
    # Fallback: Create a structured educational outline
    fallback_content = f"""
# {topic}

## Introduction
{topic} is an important concept in learning and development. Understanding the fundamentals of {topic} is essential for building a strong foundation in this subject area.

## Key Concepts
1. Basic principles of {topic}
2. How {topic} relates to real-world applications
3. Common misconceptions and clarifications
4. Practical examples of {topic}

## Why {topic} Matters
{topic} is valuable because it provides insights into {topic.lower()}. Understanding this topic helps in making informed decisions and solving complex problems.

## Practical Applications
- Understanding the theory behind {topic}
- Learning different approaches and methodologies
- Developing critical thinking skills
- Building expertise in this domain

## Getting Started with {topic}
To effectively learn {topic}:
1. Start with fundamental concepts
2. Practice with real-world examples
3. Apply knowledge to solve problems
4. Continuously review and refine understanding

## Next Steps
Continue exploring related concepts and deepening your understanding of {topic} through practice and application.
"""
    
    return fallback_content.strip()


def _deeply_clean_text_from_wrappers(obj):
    """Recursively extract clean text from wrapper objects, handling 'response:GenerateContentResponse' patterns."""
    import re
    if isinstance(obj, str):
        s = obj.strip()
        # If wrapped, try to extract "text" field values
        if ('GenerateContentResponse' in s or 'response:' in s or '"text"' in s) and len(s) > 50:
            try:
                # Extract all "text": "..." values — handle escaped content
                # Pattern: "text": "...content..." where content may have \", \\, \n, etc
                matches = re.findall(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', s)
                if matches:
                    # Join all extracted text, unescape common sequences
                    extracted_parts = []
                    for m in matches:
                        # Unescape sequences
                        unesc = m.replace('\\n', '\n').replace('\\r', '\r').replace('\\"', '"').replace('\\\\', '\\')
                        # Unescape unicode \uXXXX
                        unesc = re.sub(r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), unesc)
                        if unesc.strip():
                            extracted_parts.append(unesc)
                    
                    if extracted_parts:
                        extracted = '\n\n'.join(extracted_parts).strip()
                        # Sanity check: should look like readable text, not more junk
                        if extracted and len(extracted) > 10 and not extracted.startswith('{'):
                            return extracted
            except Exception as e:
                pass
        return s
    elif isinstance(obj, list):
        return [_deeply_clean_text_from_wrappers(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _deeply_clean_text_from_wrappers(v) for k, v in obj.items()}
    return obj


def generate_study_pack(topic: str, youtube_url: str = None, transcript_text: str = None, export_pdf: bool = False, use_agent: bool = False):
    """Orchestrator: fetch transcript (or use provided), call model (or agent flow), optionally export PDF.

    If `use_agent` is True, the lightweight `crew_integration.orchestrate_agent_flow` will be used
    to simulate an agentic multi-step pipeline (chunking, stepwise generation, simple retries).
    
    If no transcript_text or youtube_url provided, generate content from topic using Gemini.
    """
    transcript = transcript_text or ''
    
    # # If we have a YouTube URL, try to fetch it
    # if youtube_url and not transcript_text:
    #     try:
    #         transcript = get_transcript_for_youtube(youtube_url)
    #     except Exception as e:
    #         return {
    #             'topic': topic,
    #             'error': f'Failed to fetch YouTube transcript: {str(e)}'
    #         }
    
    # If still no transcript, generate content from topic using Gemini
    if not transcript.strip():
        transcript = _generate_topic_content(topic)

    if use_agent:
        materials = orchestrate_agent_flow(topic=topic, transcript=transcript, youtube_url=youtube_url)
    else:
        materials = generate_materials(transcript, topic)

    # If materials are empty (model returned no summary/flashcards/quiz), use local fallback generator
    try:
        empty_summary = not (isinstance(materials.get('summary'), str) and materials.get('summary').strip()) if isinstance(materials, dict) else True
        empty_flash = not (isinstance(materials.get('flashcards'), list) and len(materials.get('flashcards')) > 0) if isinstance(materials, dict) else True
        empty_quiz = not (isinstance(materials.get('quiz'), list) and len(materials.get('quiz')) > 0) if isinstance(materials, dict) else True
        if empty_summary and empty_flash and empty_quiz:
            # prefer the dedicated fallback which returns the full materials shape
            try:
                materials = generate_materials_fallback(transcript, topic)
            except Exception:
                # as a last resort, assemble minimal materials using local helpers
                materials = {
                    'summary': local_generate_summary(transcript, topic),
                    'flashcards': local_generate_flashcards(transcript, topic, n=8),
                    'quiz': local_generate_quiz(transcript, topic, n=5),
                    'study_plan': {
                        'levels': [
                            {'level': 'Beginner', 'duration_days': 7, 'focus': 'Key concepts and definitions'},
                            {'level': 'Intermediate', 'duration_days': 14, 'focus': 'Practice problems and examples'},
                            {'level': 'Mastery', 'duration_days': 30, 'focus': 'Projects and advanced topics'}
                        ]
                    }
                }
    except Exception:
        # If checking fails for any reason, ignore and continue with whatever materials we have
        pass

    # If the model returned diagnostic wrapper text (e.g., 'GenerateContentResponse')
    # it's likely the parsing failed and produced polluted fields — use fallback.
    try:
        def _contains_wrapper(m):
            if not isinstance(m, dict):
                return False
            for k, v in m.items():
                if isinstance(v, str) and ('GenerateContentResponse' in v or 'response:' in v):
                    return True
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            for kk, vv in item.items():
                                if isinstance(vv, str) and ('GenerateContentResponse' in vv or 'response:' in vv):
                                    return True
                        elif isinstance(item, str) and ('GenerateContentResponse' in item or 'response:' in item):
                            return True
            return False

        # Aggressive check: if the serialized materials contains debug wrapper text, fallback
        serialized = ''
        try:
            serialized = json.dumps(materials)
        except Exception:
            serialized = str(materials)

        if isinstance(materials, dict) and (_contains_wrapper(materials) or 'GenerateContentResponse' in serialized or 'response:' in serialized):
            # Try to extract human-readable text from serialized wrapper before falling back.
            def _extract_text_from_wrapper(s: str) -> str:
                try:
                    # Find all occurrences like '"text": "..."' inside the serialized wrapper
                    parts = re.findall(r'\"text\"\s*:\s*\"((?:\\\\.|[^\"\\\\])*)\"', s, flags=re.S)
                    if parts:
                        # Unescape common escapes and join
                        cleaned = []
                        for p in parts:
                            # Replace escaped newlines and quotes
                            unescaped = p.encode('utf-8').decode('unicode_escape')
                            # Convert any HTML entities just in case
                            unescaped = html.unescape(unescaped)
                            cleaned.append(unescaped)
                        return "\n\n".join(cleaned).strip()
                except Exception:
                    return ''
                return ''

            extracted = _extract_text_from_wrapper(serialized)
            # As a first quick sanitization step, strip any obvious serialized wrapper suffixes
            def _sanitize_strings(obj):
                if isinstance(obj, str):
                    s = obj
                    # remove common wrapper markers and everything after them
                    for marker in ('response:\nGenerateContentResponse', 'GenerateContentResponse(', 'result=protos.GenerateContentResponse'):
                        idx = s.find(marker)
                        if idx != -1:
                            s = s[:idx].strip()
                    return s
                if isinstance(obj, list):
                    return [_sanitize_strings(x) for x in obj]
                if isinstance(obj, dict):
                    return {k: _sanitize_strings(v) for k, v in obj.items()}
                return obj

            try:
                materials = _sanitize_strings(materials)
            except Exception:
                pass
            used_extraction = False
            if extracted:
                try:
                    parsed = _parse_model_output(extracted)
                    if isinstance(parsed, dict) and parsed:
                        materials = parsed
                        used_extraction = True
                    else:
                        # Place extracted text into summary as a best-effort
                        if isinstance(materials, dict):
                            materials['summary'] = extracted
                            used_extraction = True
                except Exception:
                    # if parsing fails, still use the raw extracted text
                    if isinstance(materials, dict):
                        materials['summary'] = extracted
                        used_extraction = True

            if not used_extraction:
                try:
                    materials = generate_materials_fallback(transcript, topic)
                except Exception:
                    materials = {
                        'summary': local_generate_summary(transcript, topic),
                        'flashcards': local_generate_flashcards(transcript, topic, n=8),
                        'quiz': local_generate_quiz(transcript, topic, n=5),
                        'study_plan': {
                            'levels': [
                                {'level': 'Beginner', 'duration_days': 7, 'focus': 'Key concepts and definitions'},
                                {'level': 'Intermediate', 'duration_days': 14, 'focus': 'Practice problems and examples'},
                                {'level': 'Mastery', 'duration_days': 30, 'focus': 'Projects and advanced topics'}
                            ]
                        }
                    }
    except Exception:
        pass

    # If the model returned a raw candidates object (GenerateContentResponse shape),
    # try to extract the JSON payload from the first candidate's content parts.
    def _try_unpack_candidates(m):
        if not isinstance(m, dict):
            return None
        # Common shape: {'candidates': [ {'content': {'parts': [ {'text': '...'} ] } }, ... ] }
        cand_list = m.get('candidates')
        if not cand_list or not isinstance(cand_list, list):
            return None
        first = cand_list[0]
        try:
            # content may be nested dicts depending on client version
            content = None
            if isinstance(first, dict):
                content = first.get('content') or first.get('message') or first.get('text')
            else:
                content = str(first)

            text = ''
            if isinstance(content, dict):
                parts = content.get('parts') or []
                for p in parts:
                    if isinstance(p, dict):
                        text += p.get('text', '')
                    else:
                        text += str(p)
            else:
                text = str(content)

            parsed = _parse_model_output(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
        return None

    unpacked = _try_unpack_candidates(materials)
    if unpacked:
        materials = unpacked

    # Final deep-clean: extract all text from wrapper objects
    try:
        materials = _deeply_clean_text_from_wrappers(materials)
    except Exception:
        pass

    response = {
        'topic': topic,
        'materials': materials
    }

    if export_pdf:
        pdf_path = create_study_pdf(topic, materials)
        response['pdf_path'] = pdf_path

    return response
