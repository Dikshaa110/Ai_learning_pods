
# import re

# def extract_video_id(url_or_id: str) -> str:
#     # support full url or direct id
#     if 'youtube' in url_or_id or 'youtu.be' in url_or_id:
#         # naive extraction
#         m = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})', url_or_id)
#         if m:
#             return m.group(1)
#     return url_or_id


# def get_transcript_for_youtube(url_or_id: str) -> str:
#     """Fetch transcript from YouTube video using video ID or URL."""
#     video_id = extract_video_id(url_or_id)
#     try:
#         # Create API instance and fetch the transcript
#         api = YouTubeTranscriptApi()
#         transcript = api.fetch(video_id, languages=['en'])
#         text = ' '.join([item['text'] for item in transcript])
#         return text
#     except TranscriptsDisabled:
#         raise Exception('Transcripts are disabled for this video')
#     except Exception as e:
#         raise Exception(f'Failed to fetch transcript: {str(e)}')
