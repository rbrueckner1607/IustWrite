import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from io import BytesIO
import re
from datetime import datetime

st.set_page_config(page_title="iustWrite | lexgerm.de", layout="wide")

# ============================================================================
# METADATEN + SPEICHER/EXPORT OBEN
# ============================================================================
col_meta1, col_meta2, col_meta3, col_btn1, col_btn2 = st.columns([1, 1, 1, 1, 1])
with col_meta1:
    title = st.text_input("Titel", value="Zivilrecht I - Klausur", label_visibility="collapsed")
with col_meta2:
    date = st.date_input("Datum", value=datetime.now().date(), label_visibility="collapsed")
with col_meta3:
    matrikel = st.text_input("Matrikel", value="12345678", label_visibility="collapsed")
with col_btn1:
    save_content = st.button("💾 Speichern")
with col_btn2:
    export_pdf = st.button("📄 PDF")

# ============================================================================
# GROßER EDITOR RECHTS + optional Gliederung overlay
# ============================================================================
col_left, col_right = st.columns([0.2, 0.8])  # Links optional Gliederung

with col_right:
    default_text = """Teil 1. Zulässigkeit

A. Formelle Voraussetzungen

I. Antragsbegründung

1. Fristgerechtigkeit

a) Einreichungsfrist

II. Begründetheit"""
    content = st.text_area("Editor", value=st.session_state.get('content', default_text), height=850)
    st.session_state.content = content

# ============================================================================
# KOMPAKTE GLIEDERUNG (Overlay)
# ============================================================================
def build_toc(content):
    lines = content.split("\n")
    toc = []
    patterns = [
        r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\.',
        r'^[A-I]\.',
        r'^(I{1,5}|V?|X{0,3})\.',
        r'^\d+\.',
        r'^[a-z]\)',
        r'^[a-z]{2}\)',
        r'^\([a-z]\)',
        r'^\([a-z]{2}\)'
    ]
    levels = {}
    for i, line in enumerate(lines):
        text = line.strip()
        if not text: continue
        for lvl, pattern in enumerate(patterns, 1):
            if re.match(pattern, text):
                toc.append((i, text, lvl))
                levels[i] = lvl
                break
    return toc, levels

toc, toc_levels = build_toc(content)
st.session_state.toc = toc
st.session_state.toc_levels = toc_levels

# ============================================================================
# SAVE / DOWNLOAD
# ============================================================================
if save_content:
    meta_content = f"Titel: {title}\nDatum: {date}\nMatrikelnummer: {matrikel}\n---\n{content}"
    st.download_button("📥 .klausur", meta_content, f"{title.replace(' ', '_')}.klausur", "text/plain")

# ============================================================================
# PDF EXPORT
# ============================================================================
def create_pdf(title, date, matrikel, content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5*cm,
        rightMargin=6*cm,
        topMargin=2.5*cm,
        bottomMargin=3*cm
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Stammdaten
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, spaceAfter=10, alignment=TA_LEFT)
    story.append(Paragraph(f"<b>Matrikel-Nr.:</b> {matrikel} | <b>Datum:</b> {date}", meta_style))
    
    # Titel
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=20, alignment=TA_LEFT)
    story.append(Paragraph(f"<b>{title}</b>", title_style))
    
    # Gliederung
    toc_style = ParagraphStyle('Gliederung', parent=styles['Heading2'], fontSize=14, spaceAfter=5, spaceBefore=5)
    story.append(Paragraph("Gliederung", toc_style))
    for idx, text, lvl in toc:
        indent = "   " * (lvl-1)
        story.append(Paragraph(f"{indent}{text}", styles['Normal']))
    
    story.append(PageBreak())
    
    # Klausurtext
    text_style = ParagraphStyle(
        'Text', parent=styles['Normal'], fontSize=12, leading=14.4, alignment=TA_JUSTIFY, fontName='Helvetica'
    )
    patterns = [p[0] for p in toc]
    for line in content.split("\n"):
        if line.strip() == "":
            story.append(Spacer(1, 5))
            continue
        is_heading = False
        for pattern in [
            r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\.',
            r'^[A-I]\.',
            r'^(I{1,5}|V?|X{0,3})\.',
            r'^\d+\.',
            r'^[a-z]\)',
            r'^[a-z]{2}\)',
            r'^\([a-z]\)',
            r'^\([a-z]{2}\)'
        ]:
            if re.match(pattern, line.strip()):
                heading_style = ParagraphStyle('Heading', parent=text_style, fontName='Helvetica-Bold', spaceAfter=6, alignment=TA_LEFT)
                story.append(Paragraph(line.strip(), heading_style))
                is_heading = True
                break
        if not is_heading:
            story.append(Paragraph(line.strip(), text_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

if export_pdf:
    pdf_bytes = create_pdf(title, date, matrikel, content)
    st.session_state.pdf_bytes = pdf_bytes
    st.session_state.pdf_name = f"{title.replace(' ', '_')}.pdf"

if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF herunterladen", st.session_state.pdf_bytes, st.session_state.pdf_name, "application/pdf")
