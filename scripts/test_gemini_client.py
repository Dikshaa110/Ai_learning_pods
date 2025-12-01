import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.environ.get('GOOGLE_API_KEY')
print('GOOGLE_API_KEY SET:', bool(api_key))

try:
    import google.generativeai as genai
except Exception as e:
    print('GENAI_INSTALLED: False -', str(e))
    raise SystemExit(1)

try:
    genai.configure(api_key=api_key)
    # try the common helper names used by different library versions
    try:
        resp = genai.generate_text(model=os.environ.get('GEN_MODEL','gemini-2.5-flash'), prompt='Write one short sentence about Python functions.', max_output_tokens=120)
        print('GENAI_METHOD: generate_text')
        if isinstance(resp, dict):
            print('RESPONSE_KEYS:', list(resp.keys()))
            print('OUTPUT_SNIPPET:', resp.get('candidates',[{}])[0].get('content') or resp.get('output'))
        else:
            print('OUTPUT:', str(resp)[:400])
    except Exception as e1:
        try:
            resp = genai.text.generate(model=os.environ.get('GEN_MODEL','gemini-2.5-flash'), prompt='Write one short sentence about Python functions.', max_output_tokens=120)
            print('GENAI_METHOD: genai.text.generate')
            if isinstance(resp, dict):
                print('RESPONSE_KEYS:', list(resp.keys()))
                print('OUTPUT_SNIPPET:', resp.get('candidates',[{}])[0].get('content') or resp.get('output'))
            else:
                # some versions have response.text
                print('OUTPUT:', getattr(resp, 'text', str(resp))[:400])
        except Exception as e2:
            print('GENAI_ERROR:', str(e1)[:200], ' / ', str(e2)[:200])
            raise
except Exception as e:
    print('ERROR_CONFIGURING_OR_CALLING_GENAI:', str(e))
    raise
