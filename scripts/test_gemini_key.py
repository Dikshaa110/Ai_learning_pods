import os
import sys
from dotenv import load_dotenv

# Ensure backend root is on sys.path when running from scripts/
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)

load_dotenv()
from gemini_client import call_gemini

print('GOOGLE_API_KEY SET:', bool(os.environ.get('GOOGLE_API_KEY')))
try:
    out = call_gemini('Write one short sentence about Python functions.', max_tokens=120)
    print('CALL_SUCCESS_LEN:', len(out) if out else 'EMPTY')
    if out:
        print('OUTPUT:', out[:400])
except Exception as e:
    print('CALL_ERROR:', str(e))
