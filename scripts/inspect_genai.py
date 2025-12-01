import os, sys, inspect
from dotenv import load_dotenv
load_dotenv()
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)

print('PYTHON:', sys.executable)
try:
    import google.generativeai as genai
except Exception as e:
    print('IMPORT_ERROR:', e)
    raise SystemExit(1)

print('GENAI MODULE:', genai)
attrs = dir(genai)
print('\nAttributes:')
for a in attrs:
    print(' -', a)

# Show callables at top-level and their signatures
print('\nTop-level callables and types:')
for a in attrs:
    try:
        obj = getattr(genai, a)
    except Exception:
        continue
    if callable(obj):
        try:
            sig = inspect.signature(obj)
        except Exception:
            sig = '()'
        print(f' * {a} {sig}')

# Try to find classes named GenerativeModel, Client, or similar
candidates = ['GenerativeModel','Client','GenAI','GenAIClient','TextGenerationModel','TextClient']
found = []
for c in candidates:
    if hasattr(genai, c):
        found.append(c)
print('\nFound candidate classes:', found)

# If there's a `model` or `generative` attribute, show its dir
for name in ['model','generative','text','util','api']:
    if hasattr(genai, name):
        print(f"\ngenai.{name} -> {type(getattr(genai,name))}")
        try:
            print('dir:', dir(getattr(genai,name))[:60])
        except Exception:
            pass

# Attempt to call some likely helpers safely
print('\nAttempting safe calls (no heavy payloads):')
try:
    if hasattr(genai, 'configure'):
        print('Has configure, calling with current key...')
        genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
        print('configure OK')
except Exception as e:
    print('configure failed:', e)

# Try to find a function that can be used to generate, print repr of first candidate
for a in attrs:
    try:
        obj = getattr(genai, a)
        if callable(obj) and a.lower().startswith('generate'):
            print('FOUND GENERATE FUNCTION:', a, '->', obj)
            try:
                print('signature:', inspect.signature(obj))
            except Exception:
                pass
    except Exception:
        pass

print('\nDone')
