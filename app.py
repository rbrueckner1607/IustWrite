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
# ======================== METADATEN + BUTTONS OBEN =========================
# ============================================================================
top_col1, top_col2, top_col3, top_col4, top_col5 = st.columns([1, 1, 1, 1, 1.5])

with top_col1:
    title = st.text_input("Titel", value="Zivilrecht I - Klausur", label_visibility="collapsed")
with top_col2:
    date = st.date_input("Datum", value=datetime.now().date(), label_visibility="collapsed")
with top_col3:
    matrikel = st.text_input("Matrikel", value="12345678", label_visibility="collapsed")
with top_col4:
    if st.button("💾 Speichern"):
        meta_content = f"Titel: {title}\nDatum: {date}\nMatrikelnummer: {matrikel}\n---\n{st.session_state.get('content','')}"
        st.download_button("📥 .klausur", meta_content, f"{title.replace(' ','_')}.klausur", "text/plain")
with top_col5:
    if st.button("🎯 PDF"):
        with st.spinner("PDF wird erstellt..."):
            pdf_bytes = create_perfect_pdf(title, date, matrikel, st.session_state.get('content',''))
            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.pdf_name = f"{title.replace(' ','_')}.pdf"

if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF", st.session_state.pdf_bytes, st.session_state.pdf_name, "application/pdf")

# ============================================================================
# ========================= LAYOUT LINKS/RECHTS =============================
# ============================================================================
col_left, col_right = st.columns([0.18, 0.82])

# ==================== RECHTS: EDITOR ====================
with col_right:
    default_text = """Teil 1. Zulässigkeit

A. Formelle Voraussetzungen

I. Antragsbegründung

1. Fristgerechtigkeit

a) Einreichungsfrist

II. Begründetheit"""
    content = st.text_area(
        "✍️ Klausur Editor",
        value=st.session_state.get('content', default_text),
        height=700,
        label_visibility="collapsed"
    )
    st.session_state.content = content

# ==================== LINKS: GLIEDERUNG ====================
with col_left:
    st.markdown("### 📋 Gliederung")
    lines = content.split('\n')
    toc = []
    toc_levels = {}
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
        for level, pattern in enumerate(patterns,1):
            if re.match(pattern,text):
                toc.append((i, text))
                toc_levels[i] = level
                break

    # Zeilenabstand 1, platzsparend, anklickbar
    for idx, (lineno, heading) in enumerate(toc):
        short_text = heading if len(heading)<=30 else heading[:27]+"..."
        if st.button(short_text, key=f"toc_{idx}", use_container_width=True):
            # Cursor springt zur entsprechenden Zeile im Editor
            st.session_state.scroll_line = lineno
            st.experimental_rerun()

# ==================== AUTOMATISCH SCROLLEN ====================
if 'scroll_line' in st.session_state:
    scroll_idx = st.session_state.pop('scroll_line')
    # Streamlit unterstützt nicht direkt scrollen, aber Textarea neu setzen kann Fokus simulieren
    # Keine native Lösung → Alternative: Hinweis im Editor
    st.warning(f"⬆ Gehe zu Zeile {scroll_idx+1} im Textfenster")

# ============================================================================
# ======================= PDF GENERIERUNG ==============================
# ============================================================================
def create_perfect_pdf(title, date, matrikel, content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=6*cm,
        leftMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=3*cm
    )
    story = []
    styles = getSampleStyleSheet()

    # --- Stammdaten ---
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, spaceAfter=12, alignment=TA_LEFT)
    story.append(Paragraph(f"<b>Matrikel:</b> {matrikel} | <b>Datum:</b> {date}", meta_style))

    # --- Titel ---
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=20, alignment=TA_LEFT)
    story.append(Paragraph(f"<b>{title}</b>", title_style))

    # --- Gliederung ---
    story.append(Paragraph("<b>Gliederung</b>", ParagraphStyle('TOC', fontSize=12, spaceAfter=6, spaceBefore=6)))
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
    for line in content.split('\n'):
        text = line.strip()
        if not text: continue
        for level, pattern in enumerate(patterns,1):
            if re.match(pattern,text):
                indent = "&nbsp;"*(level-1)*4
                story.append(Paragraph(f"{indent}{text}", ParagraphStyle('TOCItem', fontSize=10, spaceAfter=2)))
                break
    story.append(PageBreak())

    # --- Klausurtext ---
    text_style = ParagraphStyle('KlausurText', fontSize=12, leading=14.4, alignment=TA_JUSTIFY, spaceAfter=6, fontName='Helvetica')
    for line in content.split('\n'):
        text = line.strip()
        if not text:
            story.append(Spacer(1,6))
            continue
        is_heading = any(re.match(p, text) for p in patterns)
        if is_heading:
            heading_style = ParagraphStyle('Heading', fontName='Helvetica-Bold', fontSize=12, leading=14.4, spaceAfter=6)
            story.append(Paragraph(text, heading_style))
        else:
            story.append(Paragraph(text, text_style))

    doc.build(story, onFirstPage=first_page_no_number, onLaterPages=later_pages)
    buffer.seek(0)
    return buffer.getvalue()

# ==================== SEITENNUMMERIERUNG ====================
def first_page_no_number(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica',10)
    # Keine Seitenzahl auf Gliederung
    canvas.restoreState()

def later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica',10)
    canvas.drawRightString(A4[0]-2*cm, 2*cm, str(doc.page))
    canvas.restoreState()
