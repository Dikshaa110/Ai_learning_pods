# import os
# import json
# import time
# import re
# from typing import Optional
# from collections import Counter

# import requests

# # Try to import official Google Generative AI client if available
# _HAS_GOOGLE_CLIENT = False
# try:
#     import google.generativeai as genai
#     _HAS_GOOGLE_CLIENT = True
# except Exception:
#     _HAS_GOOGLE_CLIENT = False


# API_KEY = os.getenv("GOOGLE_API_KEY")

# MODEL = os.environ.get('GEN_MODEL', 'gemini-1.5-flash')


# def _extract_json(text: str) -> Optional[str]:
#     """Try to extract JSON object from model output by finding first '{' and last '}'."""
#     if not text:
#         return None
#     # find first JSON object
#     start = text.find('{')
#     end = text.rfind('}')
#     if start != -1 and end != -1 and end > start:
#         candidate = text[start:end+1]
#         return candidate
#     return None


# def _parse_model_output(text: str):
#     # try direct json parse
#     try:
#         return json.loads(text)
#     except Exception:
#         # try to extract json substring
#         j = _extract_json(text)
#         if j:
#             try:
#                 return json.loads(j)
#             except Exception:
#                 return None
#     return None


# def _sentences(text):
#     s = re.split(r'(?<=[.!?]) +', text)
#     return [x.strip() for x in s if x.strip()]


# def local_generate_summary(text: str, topic: str) -> str:
#     sentences = _sentences(text)
#     if not sentences:
#         return 'No transcript available to summarize.'
#     words = [w.lower() for w in re.findall(r"\w+", text) if len(w) > 3]
#     freq = Counter(words)

#     def score(sent):
#         return sum(freq.get(w.lower(), 0) for w in re.findall(r"\w+", sent))

#     s_sorted = sorted(sentences, key=score, reverse=True)
#     top = s_sorted[:6]
#     return ' '.join(top)


# def local_generate_flashcards(text: str, topic: str, n=10):
#     sentences = _sentences(text)
#     cards = []
#     for i, s in enumerate(sentences[:n]):
#         q = f"What is a key point about '{topic}' from this sentence?"
#         a = s
#         cards.append({'q': q, 'a': a})
#     return cards


# def local_generate_quiz(text: str, topic: str, n=10):
#     sentences = _sentences(text)
#     quiz = []
#     for i in range(min(n, len(sentences))):
#         correct = sentences[i]
#         wrong = sentences[i+1] if i+1 < len(sentences) else (sentences[0] if sentences else 'No data')
#         ques = f"Which statement best summarizes: '{topic}' (pick the best)"
#         options = [correct, wrong]
#         quiz.append({'question': ques, 'options': options, 'answer': 0, 'explanation': correct})
#     return quiz


# def generate_materials_fallback(transcript: str, topic: str):
#     summary = local_generate_summary(transcript, topic)
#     flashcards = local_generate_flashcards(transcript, topic, n=12)
#     quiz = local_generate_quiz(transcript, topic, n=10)
#     study_plan = {
#         'levels': [
#             {'level': 'Beginner', 'duration_days': 7, 'focus': 'Key concepts and definitions'},
#             {'level': 'Intermediate', 'duration_days': 14, 'focus': 'Practice problems and examples'},
#             {'level': 'Mastery', 'duration_days': 30, 'focus': 'Projects and advanced topics'}
#         ]
#     }
#     return {
#         'summary': summary,
#         'flashcards': flashcards,
#         'quiz': quiz,
#         'study_plan': study_plan
#     }


# def _build_prompt(transcript: str, topic: str) -> str:
#     # Primary instruction: produce ONLY a single valid JSON object exactly matching the schema below.
#     # Strict rules:
#     # - Return JSON only (no markdown, no backticks, no explanatory text).
#     # - Use the exact keys: summary, flashcards, quiz, study_plan.
#     # - summary: string (4-6 short sentences, ~60-120 words).
#     # - flashcards: list of {q: string, a: string}, 6-12 items when possible.
#     # - quiz: list of {question: string, options: [string], answer: int index, explanation: string}, 3-8 items.
#     # - study_plan: {levels: [{level: string, duration_days: int, focus: string}, ...]} (3 levels: Beginner/Intermediate/Mastery).

#     header = (
#         "You are a study-pack generator.\n"
#         "RETURN ONLY a single VALID JSON object. No text outside the JSON. No markdown.\n"
#         "Schema (types & constraints):\n"
#         "{\n"
#         "  \"summary\": <string - 4-6 short sentences>,\n"
#         "  \"flashcards\": [ { \"q\": <string>, \"a\": <string> }, ... ],\n"
#         "  \"quiz\": [ { \"question\": <string>, \"options\": [<string>], \"answer\": <int index>, \"explanation\": <string> }, ... ],\n"
#         "  \"study_plan\": { \"levels\": [ {\"level\": <string>, \"duration_days\": <int>, \"focus\": <string> }, ... ] }\n"
#         "}\n\n"
#     )

#     # Short, strictly JSON few-shot examples (examples MUST be valid JSON objects only).
#     ex1_t = "Intro to recursion: functions call themselves to solve subproblems; example: factorial."
#     ex1_out = {
#         "summary": "Recursion is a method where functions call themselves to break problems into smaller parts. A common example is factorial, where n! = n * (n-1)! and the base case stops recursion. Understanding base case and recursive step is key.",
#         "flashcards": [
#             {"q": "What is recursion?", "a": "A technique where a function calls itself to handle smaller instances of the same problem."},
#             {"q": "Give an example of recursion.", "a": "Factorial calculation: n! = n * (n-1)!."}
#         ],
#         "quiz": [
#             {"question": "Which best describes recursion?", "options": ["A function calling itself","A loop only"], "answer": 0, "explanation": "Recursion is when a function calls itself, often with a base case to stop."}
#         ],
#         "study_plan": {"levels": [{"level": "Beginner", "duration_days": 3, "focus": "Understand base case and recursive step"}]}
#     }

#     ex2_t = "Study techniques: spaced repetition, active recall, interleaving improve memory retention."
#     ex2_out = {
#         "summary": "Spaced repetition, active recall, and interleaving are evidence-based techniques that improve long-term retention by practicing retrieval and spacing study sessions.",
#         "flashcards": [
#             {"q": "What is spaced repetition?", "a": "Scheduling reviews at increasing intervals to strengthen memory."}
#         ],
#         "quiz": [
#             {"question": "Which technique improves long-term retention?", "options": ["Spaced repetition","Cramming"], "answer": 0, "explanation": "Spaced repetition spaces reviews to improve retention over time."}
#         ],
#         "study_plan": {"levels": [{"level": "Beginner", "duration_days": 5, "focus": "Learn core techniques: active recall and spaced repetition"}]}
#     }

#     # Build final prompt joining header, examples, and the actual transcript/topic.
#     prompt = header
#     prompt += "EXAMPLE_1_TRANSCRIPT:\n" + ex1_t + "\n"
#     prompt += "EXAMPLE_1_OUTPUT_JSON:\n" + json.dumps(ex1_out, ensure_ascii=False) + "\n\n"
#     prompt += "EXAMPLE_2_TRANSCRIPT:\n" + ex2_t + "\n"
#     prompt += "EXAMPLE_2_OUTPUT_JSON:\n" + json.dumps(ex2_out, ensure_ascii=False) + "\n\n"
#     prompt += "NOW PRODUCE JSON FOR THE FOLLOWING TRANSCRIPT AND TOPIC:\n"
#     prompt += "TRANSCRIPT:\n" + transcript + "\n\n"
#     prompt += f"TOPIC: {topic}\n\n"
#     prompt += "RETURN a single VALID JSON object matching the schema above."
#     return prompt


# # def _call_google_client(prompt: str, max_tokens: int = 1024) -> Optional[str]:
# #     """Try calling the official google.generativeai client when available."""
# #     if not _HAS_GOOGLE_CLIENT or not API_KEY:
# #         return None

# #     try:
# #         # configure client
# #         try:
# #             genai.configure(api_key=API_KEY)
# #         except Exception:
# #             pass

# #         # Some versions of the library expose different helper names; try common ones
# #         # Preferred approach: try high-level helpers, then fall back to GenerativeModel.
# #         try:
# #             resp = genai.generate_text(model=MODEL, prompt=prompt, max_output_tokens=max_tokens)
# #             # extract text candidate
# #             if isinstance(resp, dict):
# #                 return resp.get('candidates', [{}])[0].get('content') or resp.get('output')
# #             return str(resp)
# #         except Exception:
# #             pass

# #         try:
# #             resp = genai.text.generate(model=MODEL, prompt=prompt, max_output_tokens=max_tokens)
# #             if isinstance(resp, dict):
# #                 return resp.get('candidates', [{}])[0].get('content') or resp.get('output')
# #             return str(resp)
# #         except Exception:
# #             pass

# #         # Newer client versions provide a GenerativeModel class with `generate_content`.
# #         try:
# #             gen = genai.GenerativeModel(MODEL)
# #             resp = gen.generate_content(prompt)

# #             # Try to extract readable text from the response
# #             try:
# #                 # response.result.candidates -> candidate.content.parts[].text
# #                 parts = resp.result.candidates[0].content.parts
# #                 text = ''.join([getattr(p, 'text', str(p)) for p in parts])
# #                 return text
# #             except Exception:
# #                 return str(resp)
# #         except Exception:
# #             return None
# #     except Exception:
# #         return None
# def _call_google_client(prompt: str, max_tokens: int = 1024) -> Optional[str]:
#     if not _HAS_GOOGLE_CLIENT or not API_KEY:
#         return None
    
#     try:
#         genai.configure(api_key=API_KEY)

#         model = genai.GenerativeModel(MODEL)
#         resp = model.generate_content({
#             "contents": [
#                 {
#                     "role": "user",
#                     "parts": [{"text": prompt}]
#                 }
#             ],
#             "generation_config": {
#                 "max_output_tokens": max_tokens
#             }
#         })

#         return resp.text
#     except Exception:
#         return None



# # def _call_rest(prompt: str, max_tokens: int = 1024) -> Optional[str]:
# #     if not API_KEY:
# #         return None
# #     url = f"https://generativelanguage.googleapis.com/v1beta2/models/{MODEL}:generateText?key={API_KEY}"
# #     payload = {
# #         'prompt': prompt,
# #         'maxOutputTokens': max_tokens,
# #     }
# #     headers = {'Content-Type': 'application/json'}
# #     resp = requests.post(url, json=payload, headers=headers, timeout=30)
# #     if resp.status_code != 200:
# #         raise Exception(f'Gemini API error: {resp.status_code} {resp.text}')
# #     data = resp.json()
# #     return data.get('candidates', [{}])[0].get('content') or data.get('output') or str(data)


# def call_gemini(prompt: str, max_tokens: int = 1024, retries: int = 2) -> Optional[str]:
#     """Call Gemini using the official client if available, otherwise REST. Returns model text or None."""
#     last_exc = None
#     for attempt in range(1, retries + 1):
#         try:
#             if _HAS_GOOGLE_CLIENT and API_KEY:
#                 out = _call_google_client(prompt, max_tokens=max_tokens)
#                 if out:
#                     return out
#             # fallback to REST
#             out = _call_rest(prompt, max_tokens=max_tokens)
#             if out:
#                 return out
#         except Exception as e:
#             last_exc = e
#             time.sleep(0.6 * attempt)
#     if last_exc:
#         raise last_exc
#     return None
# def _call_rest(prompt: str, max_tokens: int = 1024) -> Optional[str]:
#     if not API_KEY:
#         return None

#     url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
#     payload = {
#         "contents": [
#             {
#                 "role": "user",
#                 "parts": [{"text": prompt}]
#             }
#         ],
#         "generationConfig": {
#             "maxOutputTokens": max_tokens
#         }
#     }

#     headers = {"Content-Type": "application/json"}

#     resp = requests.post(url, json=payload, headers=headers, timeout=30)

#     if resp.status_code != 200:
#         raise Exception(f"Gemini API error: {resp.status_code} {resp.text}")

#     data = resp.json()
#     return data["candidates"][0]["content"]["parts"][0].get("text", "")



# def generate_materials(transcript: str, topic: str):
#     # If no API key or client, use local fallback
#     if not API_KEY:
#         return generate_materials_fallback(transcript, topic)

#     prompt = _build_prompt(transcript, topic)
#     try:
#         out = call_gemini(prompt)
#     except Exception:
#         return generate_materials_fallback(transcript, topic)

#     if not out:
#         return generate_materials_fallback(transcript, topic)

#     parsed = _parse_model_output(out)

#     # If parsing failed, attempt a short follow-up correction prompt (retry) to ask model to return valid JSON only.
#     def _attempt_correction(prev_text: str, attempts: int = 2):
#         for i in range(attempts):
#             followup = (
#                 "The previous response failed to parse as JSON.\n"
#                 "Here is the previous output:\n\n" + prev_text + "\n\n"
#                 "Please RETURN ONLY a single VALID JSON object (no explanation) that matches the schema:\n"
#                 "{summary: string, flashcards: [{q:string,a:string}], quiz: [{question:string,options:[string],answer:int,explanation:string}], study_plan: object}\n"
#             )
#             try:
#                 corrected = call_gemini(followup, max_tokens=1024, retries=1)
#             except Exception:
#                 corrected = None
#             if not corrected:
#                 continue
#             parsed2 = _parse_model_output(corrected)
#             if isinstance(parsed2, dict):
#                 return parsed2
#             prev_text = corrected
#         return None

#     if isinstance(parsed, dict):
#         # Minimal validation: ensure keys exist
#         parsed.setdefault('summary', parsed.get('summary') or '')
#         parsed.setdefault('flashcards', parsed.get('flashcards') or [])
#         parsed.setdefault('quiz', parsed.get('quiz') or [])
#         parsed.setdefault('study_plan', parsed.get('study_plan') or {})
#         return parsed

#     # try correction flow
#     try:
#         corrected = _attempt_correction(out, attempts=2)
#         if isinstance(corrected, dict):
#             corrected.setdefault('summary', corrected.get('summary') or '')
#             corrected.setdefault('flashcards', corrected.get('flashcards') or [])
#             corrected.setdefault('quiz', corrected.get('quiz') or [])
#             corrected.setdefault('study_plan', corrected.get('study_plan') or {})
#             return corrected
#     except Exception:
#         pass

#     # if all else fails, return the model output as summary
#     return {'summary': out, 'flashcards': [], 'quiz': [], 'study_plan': {}}



import os
import json
import re
import time
from typing import Optional
from collections import Counter

try:
    import google.generativeai as genai
    _HAS_GOOGLE_CLIENT = True
except ImportError:
    _HAS_GOOGLE_CLIENT = False

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("GEN_MODEL", "gemini-2.5-flash")  # use 2.5 flash

if _HAS_GOOGLE_CLIENT and API_KEY:
    genai.configure(api_key=API_KEY)


# ------------------- Local fallback -------------------
def _sentences(text):
    return [x.strip() for x in re.split(r'(?<=[.!?]) +', text) if x.strip()]


def local_generate_summary(text: str, topic: str) -> str:
    sentences = _sentences(text)
    if not sentences:
        return "No transcript available to summarize."
    words = [w.lower() for w in re.findall(r"\w+", text) if len(w) > 3]
    freq = Counter(words)
    def score(sent):
        return sum(freq.get(w.lower(), 0) for w in re.findall(r"\w+", sent))
    s_sorted = sorted(sentences, key=score, reverse=True)
    top = s_sorted[:6]
    return " ".join(top)


def local_generate_flashcards(text: str, topic: str, n=10):
    sentences = _sentences(text)
    cards = []
    for i, s in enumerate(sentences[:n]):
        q = f"What is a key point about '{topic}' from this sentence?"
        a = s
        cards.append({'q': q, 'a': a})
    return cards


def local_generate_quiz(text: str, topic: str, n=10):
    sentences = _sentences(text)
    quiz = []
    for i in range(min(n, len(sentences))):
        correct = sentences[i]
        wrong = sentences[i+1] if i+1 < len(sentences) else sentences[0]
        ques = f"Which statement best summarizes: '{topic}' (pick the best)"
        options = [correct, wrong]
        quiz.append({'question': ques, 'options': options, 'answer': 0, 'explanation': correct})
    return quiz


def generate_materials_fallback(transcript: str, topic: str):
    summary = local_generate_summary(transcript, topic)
    flashcards = local_generate_flashcards(transcript, topic, n=12)
    quiz = local_generate_quiz(transcript, topic, n=10)
    study_plan = {
        'levels': [
            {'level': 'Beginner', 'duration_days': 7, 'focus': 'Key concepts and definitions'},
            {'level': 'Intermediate', 'duration_days': 14, 'focus': 'Practice problems and examples'},
            {'level': 'Mastery', 'duration_days': 30, 'focus': 'Projects and advanced topics'}
        ]
    }
    return {
        'summary': summary,
        'flashcards': flashcards,
        'quiz': quiz,
        'study_plan': study_plan
    }


# ------------------- JSON Parsing -------------------
def _extract_json(text: str) -> Optional[str]:
    if not text:
        return None
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return None


def _parse_model_output(text: str):
    try:
        return json.loads(text)
    except Exception:
        j = _extract_json(text)
        if j:
            try:
                return json.loads(j)
            except Exception:
                return None
    return None


# ------------------- Build Prompt -------------------
def _build_prompt(transcript: str, topic: str) -> str:
    header = (
        "You are a study-pack generator.\n"
        "RETURN ONLY a single VALID JSON object. No text outside the JSON. No markdown.\n"
        "Schema:\n"
        "{'summary': string, 'flashcards': [{'q': string, 'a': string}], 'quiz': [{'question': string, 'options': [string], 'answer': int, 'explanation': string}], 'study_plan': {'levels': [{'level': string, 'duration_days': int, 'focus': string}]}}\n\n"
    )
    prompt = header + f"TRANSCRIPT:\n{transcript}\nTOPIC: {topic}\nRETURN JSON."
    return prompt


# ------------------- Gemini Calls -------------------
def _call_google_client(prompt: str, max_tokens: int = 1024) -> Optional[str]:
    if not _HAS_GOOGLE_CLIENT or not API_KEY:
        return None

    try:
        model = genai.GenerativeModel(MODEL)
        resp = model.generate_content({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {"max_output_tokens": max_tokens}
        })
        return resp.text
    except Exception:
        return None


def _call_rest(prompt: str, max_tokens: int = 1024) -> Optional[str]:
    if not API_KEY:
        return None

    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens}
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Gemini API error: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0].get("text", "")


def call_gemini(prompt: str, max_tokens: int = 1024, retries: int = 2) -> Optional[str]:
    last_exc = None
    for attempt in range(retries):
        try:
            out = None
            if _HAS_GOOGLE_CLIENT and API_KEY:
                out = _call_google_client(prompt, max_tokens)
            if not out:
                out = _call_rest(prompt, max_tokens)
            if out:
                return out
        except Exception as e:
            last_exc = e
            time.sleep(0.5 * (attempt+1))
    if last_exc:
        raise last_exc
    return None


# ------------------- Main Generator -------------------
def generate_materials(transcript: str, topic: str):
    if not API_KEY:
        return generate_materials_fallback(transcript, topic)

    prompt = _build_prompt(transcript, topic)
    try:
        out = call_gemini(prompt, max_tokens=2048)
    except Exception:
        return generate_materials_fallback(transcript, topic)

    if not out:
        return generate_materials_fallback(transcript, topic)

    parsed = _parse_model_output(out)
    if isinstance(parsed, dict):
        parsed.setdefault('summary', parsed.get('summary') or '')
        parsed.setdefault('flashcards', parsed.get('flashcards') or [])
        parsed.setdefault('quiz', parsed.get('quiz') or [])
        parsed.setdefault('study_plan', parsed.get('study_plan') or {})
        return parsed

    # fallback
    return generate_materials_fallback(transcript, topic)
