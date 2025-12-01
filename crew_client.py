import os
import requests
from typing import Any, Dict

CREW_API_KEY = os.environ.get('CREW_API_KEY')
CREW_API_URL = os.environ.get('CREW_API_URL', 'https://api.crew.ai/v1/tasks')


class CrewClientError(Exception):
    pass


def send_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a task to crew.ai (placeholder). Requires `CREW_API_KEY`.

    This is a minimal client wrapper. The exact crew.ai API may differ; replace
    endpoint and payload fields as required by your crew.ai account.
    """
    if not CREW_API_KEY:
        raise CrewClientError('CREW_API_KEY not set')

    headers = {
        'Authorization': f'Bearer {CREW_API_KEY}',
        'Content-Type': 'application/json'
    }

    resp = requests.post(CREW_API_URL, json=payload, headers=headers, timeout=30)
    if resp.status_code >= 400:
        raise CrewClientError(f'Crew API error: {resp.status_code} {resp.text}')

    return resp.json()


def create_and_run_workflow(topic: str, transcript: str, youtube_url: str = None) -> Dict[str, Any]:
    """High-level helper: create a workflow payload suitable for crew.ai and run it.

    This function sends a single synchronous task to crew.ai. For more advanced
    usage you may want to create multi-step workflows via the crew.ai UI or SDK.
    """
    payload = {
        'type': 'generate_study_pack',
        'input': {
            'topic': topic,
            'transcript': transcript,
            'youtube_url': youtube_url
        }
    }
    return send_task(payload)
