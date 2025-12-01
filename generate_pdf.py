from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_study_pdf(topic: str, materials: dict) -> str:
    # Create a simple PDF compiled from generated materials
    filename = f"{topic.replace(' ', '_')}_study_pack.pdf"
    safe_path = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(safe_path, pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont('Helvetica-Bold', 16)
    c.drawString(50, y, f"Study Pack: {topic}")
    y -= 30

    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, y, 'Summary:')
    y -= 20
    c.setFont('Helvetica', 10)
    text = materials.get('summary') or materials.get('materials', {}).get('summary', '')
    for line in str(text).split('\n'):
        c.drawString(60, y, line[:100])
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 50

    # Flashcards
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, y, 'Flashcards:')
    y -= 20
    c.setFont('Helvetica', 10)
    for card in materials.get('flashcards', [])[:50]:
        q = card.get('q')
        a = card.get('a')
        c.drawString(60, y, f"Q: {q[:120]}")
        y -= 12
        c.drawString(70, y, f"A: {a[:120]}")
        y -= 18
        if y < 80:
            c.showPage(); y = height - 50

    # Quiz
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, y, 'Quiz:')
    y -= 20
    c.setFont('Helvetica', 10)
    for i, q in enumerate(materials.get('quiz', [])[:30], start=1):
        c.drawString(60, y, f"{i}. {q.get('question')[:120]}")
        y -= 12
        for opt in q.get('options', [])[:4]:
            c.drawString(70, y, f"- {opt[:120]}")
            y -= 12
        y -= 6
        if y < 80:
            c.showPage(); y = height - 50

    c.save()
    return safe_path
