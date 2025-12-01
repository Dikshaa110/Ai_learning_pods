import os, sys, inspect
from dotenv import load_dotenv
load_dotenv()
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)

import google.generativeai as genai
print('Using module:', genai)
print('GenerativeModel class:', genai.GenerativeModel)

model_name = os.environ.get('GEN_MODEL', 'gemini-2.5-flash')
print('Model name to try:', model_name)

try:
    gm = genai.GenerativeModel(model_name)
    print('Instance created:', gm)
    attrs = dir(gm)
    print('\nInstance methods/properties:')
    for a in attrs:
        if not a.startswith('_'):
            print(' -', a)

    # Find possible generate-like methods
    candidates = [a for a in attrs if 'generate' in a.lower() or 'create' in a.lower() or 'respond' in a.lower() or 'run' in a.lower()]
    print('\nCandidate methods:', candidates[:40])

    # Attempt to call a likely method with a simple prompt
    tried = False
    for meth in ['generate', 'generate_text', 'create', 'generate_content', 'respond', 'respond_text', 'run', 'produce']:
        if hasattr(gm, meth):
            fn = getattr(gm, meth)
            print(f'Attempting method: {meth} ->', fn)
            try:
                # Try calling with a simple prompt parameter if signature allows a 'prompt' or 'messages'
                sig = None
                try:
                    sig = inspect.signature(fn)
                    print('signature:', sig)
                except Exception:
                    pass
                # Try common call shapes
                try:
                    out = fn('Write one sentence about Python functions.')
                    print('CALL_OK (string arg):', str(out)[:400])
                    tried = True
                    break
                except Exception as e1:
                    try:
                        out = fn(prompt='Write one sentence about Python functions.', max_output_tokens=120)
                        print('CALL_OK (prompt kw):', str(out)[:400])
                        tried = True
                        break
                    except Exception as e2:
                        print('Call failed for', meth, 'errors:', e1, e2)
            except Exception as e:
                print('Error while trying method', meth, e)
    if not tried:
        print('No candidate method produced a simple text response; show repr of object for further inspection')
except Exception as e:
    print('Error creating/using GenerativeModel:', e)

print('\nDone')
