import streamlit as st
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import cm
import re

# ----------------------
# Überschriften & Gliederung
# ----------------------
HEADING_PATTERNS = {
    1: r'^(Teil|Tatkomplex|Aufgabe)\s+\d+',
    2: r'^[A-H]\.',
    3: r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.',
    4: r'^\d+\.',
    5: r'^[a-z]\)',
    6: r'^[a-z]{2}\)',
    7: r'^\([a-z]\)',
    8: r'^\([a-z]{2}\)',
}

FOOTNOTE_PATTERN = r'\\fn\(([^)]*)\)'

# ----------------------
# Streamlit UI
# ----------------------
st.title("iustWrite Web-Editor")

with st.form("klausur_form"):
    title = st.text_input("Titel")
    date = st.text_input("Datum")
    matrikel = st.text_input("Matrikelnummer")
    text = st.text_area("Klausurtext", height=400)

    submitted = st.form_submit_button("PDF exportieren")

# ----------------------
# PDF-Erstellung
# ----------------------
def generate_pdf(title, date, matrikel, text):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    story = []

    # Styles
    heading_styles = {
        1: ParagraphStyle('h1', fontSize=18, leading=22, spaceAfter=12, spaceBefore=12, leftIndent=0, alignment=TA_LEFT, fontName='Helvetica-Bold'),
        2: ParagraphStyle('h2', fontSize=16, leading=20, spaceAfter=10, leftIndent=1*cm, fontName='Helvetica-Bold'),
        3: ParagraphStyle('h3', fontSize=14, leading=18, spaceAfter=8, leftIndent=1.5*cm, fontName='Helvetica-Bold'),
        4: ParagraphStyle('h4', fontSize=12, leading=16, spaceAfter=6, leftIndent=2*cm, fontName='Helvetica-Bold'),
        5: ParagraphStyle('h5', fontSize=12, leading=14, spaceAfter=4, leftIndent=2.5*cm, fontName='Helvetica-Bold'),
        6: ParagraphStyle('h6', fontSize=11, leading=14, spaceAfter=4, leftIndent=3*cm, fontName='Helvetica-Bold'),
        7: ParagraphStyle('h7', fontSize=11, leading=12, spaceAfter=3, leftIndent=3.5*cm, fontName='Helvetica-Bold'),
        8: ParagraphStyle('h8', fontSize=10, leading=12, spaceAfter=3, leftIndent=4*cm, fontName='Helvetica-Bold'),
    }
    normal_style = ParagraphStyle('normal', fontSize=11, leading=14, spaceAfter=4, leftIndent=0)

    # Inhaltsverzeichnis vorbereiten
    toc = []
    lines = text.splitlines()
    elements = []

    for idx, line in enumerate(lines):
        line_strip = line.strip()
        if not line_strip:
            elements.append(Spacer(1, 4))
            continue

        # Fußnoten ersetzen
        footnotes = re.findall(FOOTNOTE_PATTERN, line_strip)
        for i, fn in enumerate(footnotes, 1):
            line_strip = re.sub(r'\\fn\([^)]*\)', f'<super>{i}</super>', line_strip, count=1)

        # Überschriften erkennen
        matched = False
        for level, pattern in HEADING_PATTERNS.items():
            if re.match(pattern, line_strip):
                p = Paragraph(line_strip, heading_styles[level])
                elements.append(p)
                toc.append((level, line_strip))
                matched = True
                break

        if not matched:
            elements.append(Paragraph(line_strip, normal_style))

    # Deckblatt
    story.append(Paragraph(f"{title} ({date})", heading_styles[1]))
    story.append(Paragraph(f"Matrikelnummer: {matrikel}", normal_style))
    story.append(Spacer(1, 12))
    story.append(PageBreak())

    # Inhaltsverzeichnis
    story.append(Paragraph("Inhaltsverzeichnis", heading_styles[1]))
    for level, text_entry in toc:
        indent = (level-1) * 0.5 * cm
        p = Paragraph(f'{text_entry}', ParagraphStyle('toc', leftIndent=indent, fontSize=11, leading=14))
        story.append(p)
    story.append(PageBreak())

    story.extend(elements)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ----------------------
# PDF Download
# ----------------------
if submitted:
    if not title or not date or not matrikel or not text:
        st.warning("Bitte alle Felder ausfüllen!")
    else:
        pdf_bytes = generate_pdf(title, date, matrikel, text)
        st.success("PDF erfolgreich erstellt!")
        st.download_button("PDF herunterladen", pdf_bytes, file_name=f"{title}.pdf", mime="application/pdf")
