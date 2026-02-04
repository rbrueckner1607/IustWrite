import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from io import BytesIO
import re
from datetime import datetime

st.set_page_config(page_title="iustWrite | lexgerm.de", layout="wide")

# ============================================================================
# ===================== PDF FUNKTIONEN ============================
# ============================================================================

def first_page_no_number(c, doc, matrikel):
    """Erste Seite (Gliederung + Stammdaten) ohne Seitennummer"""
    c.saveState()
    c.setFont('Helvetica', 10)
    c.drawRightString(A4[0] - 2*cm, 2*cm, f"Matrikel: {matrikel}")
    c.restoreState()

def later_pages(c, doc):
    """Seitenzahlen ab Klausurtext"""
    c.saveState()
    c.setFont('Helvetica', 10)
    c.drawRightString(A4[0] - 2*cm, 2*cm, str(doc.page))
    c.restoreState()

def create_perfect_pdf(title, date, matrikel, content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=6*cm,   # Korrekturrand rechts
        leftMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=3*cm
    )

    styles = getSampleStyleSheet()

    story = []

    # ---------------- Stammdaten ----------------
    meta_style = ParagraphStyle(
        'Meta', parent=styles['Normal'], fontSize=10, spaceAfter=6, leftIndent=0, alignment=TA_LEFT
    )
    story.append(Paragraph(f"<b>Matrikel-Nr.:</b> {matrikel} | <b>Datum:</b> {date}", meta_style))

    # ---------------- Titel ----------------
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=16, spaceAfter=12, leftIndent=0, alignment=TA_LEFT
    )
    story.append(Paragraph(f"<b>{title}</b>", title_style))
    story.append(Spacer(1, 12))

    # ---------------- Gliederung ----------------
    gliederung_style = ParagraphStyle(
        'Gliederung', parent=styles['Normal'], fontSize=11, leading=12, spaceAfter=3, leftIndent=0
    )
    story.append(Paragraph("<b>Gliederung</b>", gliederung_style))
    
    # Muster für Überschriften
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

    lines = content.split('\n')
    toc_items = []
    for i, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        for level, pattern in enumerate(patterns, 1):
            if re.match(pattern, text):
                indent = "   " * (level - 1)
                toc_items.append(f"{indent}{text}")
                break

    for item in toc_items:
        story.append(Paragraph(item, gliederung_style))
    story.append(PageBreak())

    # ---------------- Klausurtext ----------------
    text_style = ParagraphStyle(
        'KlausurText',
        parent=styles['Normal'],
        fontSize=12,
        leading=14.4,  # 1.2 Zeilenabstand
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        leftIndent=0, rightIndent=0,
        fontName='Helvetica'
    )

    for line in lines:
        text = line.strip()
        if not text:
            story.append(Spacer(1, 6))
            continue
        is_heading = False
        for pattern in patterns:
            if re.match(pattern, text):
                heading_style = ParagraphStyle(
                    'Heading', parent=text_style, fontName='Helvetica-Bold', fontSize=12,
                    leftIndent=0, alignment=TA_LEFT, spaceAfter=6
                )
                story.append(Paragraph(text, heading_style))
                is_heading = True
                break
        if not is_heading:
            story.append(Paragraph(text, text_style))

    doc.build(story, onFirstPage=lambda c,d: first_page_no_number(c,d,matrikel),
                    onLaterPages=later_pages)

    buffer.seek(0)
    return buffer.getvalue()

# ============================================================================
# ===================== METADATEN + BUTTONS OBEN ============================
# ============================================================================
st.markdown("---")
meta_cols = st.columns([1,1,1,2,1,1])  # Titel, Datum, Matrikel, Spacer, Speichern, PDF
title = meta_cols[0].text_input("Titel", value="Zivilrecht I - Klausur", label_visibility="collapsed")
date = meta_cols[1].date_input("Datum", value=datetime.now().date(), label_visibility="collapsed")
matrikel = meta_cols[2].text_input("Matrikel", value="12345678", label_visibility="collapsed")

# Speicher-Button
if meta_cols[4].button("💾 Speichern"):
    meta_content = f"Titel: {title}\nDatum: {date}\nMatrikelnummer: {matrikel}\n---\n{st.session_state.get('content','')}"
    st.download_button("Download .klausur", meta_content, f"{title.replace(' ','_')}.klausur", "text/plain")

# PDF-Button
if meta_cols[5].button("📄 PDF"):
    with st.spinner("PDF wird erstellt..."):
        pdf_bytes = create_perfect_pdf(title, date, matrikel, st.session_state.get('content',''))
        st.session_state['pdf_bytes'] = pdf_bytes
        st.session_state['pdf_name'] = f"{title.replace(' ','_')}.pdf"
        st.success("PDF erstellt!")

if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF herunterladen", st.session_state['pdf_bytes'], st.session_state['pdf_name'], "application/pdf")

# ============================================================================
# ===================== HAUPT-BEREICH ============================
# ============================================================================
col_left, col_right = st.columns([0.2, 0.8])  # links Gliederung, rechts Editor

# -------------------- GLIEDERUNG --------------------
with col_left:
    st.markdown("### 📋 Gliederung")
    lines = st.session_state.get('content','').split('\n')
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
    for i, line in enumerate(lines):
        text = line.strip()
        if not text: continue
        for level, pattern in enumerate(patterns, 1):
            if re.match(pattern, text):
                # Button springt zum Cursor
                if st.button(text, key=f"toc_{i}"):
                    st.session_state['cursor_pos'] = i
                break

# -------------------- EDITOR --------------------
with col_right:
    content = st.text_area("Klausur Editor", value=st.session_state.get('content',''), height=850, label_visibility="collapsed")
    st.session_state['content'] = content

# -------------------- AUTOMATISCH SCROLL / CURSOR SPRUNG --------------------
if 'cursor_pos' in st.session_state:
    pos = st.session_state['cursor_pos']
    content_lines = st.session_state.get('content','').split('\n')
    cursor_text = "\n".join(content_lines[max(0,pos-3):pos+3])  # 3 Zeilen darüber/3 darunter
    st.text_area(" ", value=cursor_text, height=200, label_visibility="collapsed")

# ============================================================================
# ===================== STATUS --------------------
# ============================================================================
st.markdown("---")
elapsed = int((datetime.now() - st.session_state.get('start_time', datetime.now())).total_seconds())
st.markdown(f"<div style='text-align:right;color:#666;font-size:0.9em;'>{len(content):,} Zeichen | ⏱ {elapsed//60:02d}:{elapsed%60:02d}</div>", unsafe_allow_html=True)
