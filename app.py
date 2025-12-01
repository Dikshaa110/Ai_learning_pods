import os
import json
from flask import Flask, request, jsonify, send_file, send_from_directory
from ai_agent import generate_study_pack
from dotenv import load_dotenv
from flask_cors import CORS
from generate_pdf import OUTPUT_DIR

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json or {}
    topic = data.get('topic')
    youtube_url = data.get('youtube_url')
    transcript_text = data.get('transcript_text')
    export_pdf = data.get('export_pdf', False)
    use_agent = data.get('use_agent', False)

    if not topic:
        return jsonify({'error': 'topic is required'}), 400

    try:
        result = generate_study_pack(topic=topic, youtube_url=youtube_url, transcript_text=transcript_text, export_pdf=export_pdf, use_agent=use_agent)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Expose a downloadable filename (sanitized) when PDF is created
    if isinstance(result, dict) and result.get('pdf_path'):
        try:
            pdf_abs = result.get('pdf_path')
            pdf_fname = os.path.basename(pdf_abs)
            result['pdf_filename'] = pdf_fname
        except Exception:
            pass

    return jsonify(result)


@app.route('/download')
def download():
    """Serve a generated PDF from the backend `output` folder.

    Query param: file (filename only) — sanitized via basename and restricted to OUTPUT_DIR.
    """
    fname = request.args.get('file')
    if not fname:
        return jsonify({'error': 'file parameter required'}), 400
    safe = os.path.basename(fname)
    path = os.path.join(OUTPUT_DIR, safe)
    if not os.path.exists(path):
        return jsonify({'error': 'file not found'}), 404
    return send_file(path, as_attachment=True)

@app.route('/')
def index():
    # serve the static SPA index
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), 'index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Set debug=False for production (Render), True for local development
    debug_mode = os.environ.get('ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
