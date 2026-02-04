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
# KOMPAKTE METADATEN - GANZ OBEN
# ============================================================================
st.markdown("---")
meta_col1, meta_col2, meta_col3 = st.columns([1, 1, 2])
with meta_col1:
    title = st.text_input("**Titel**", value="Zivilrecht I - Klausur", label_visibility="collapsed")
with meta_col2:
    date = st.date_input("**Datum**", value=datetime.now().date(), label_visibility="collapsed")
with meta_col3:
    matrikel = st.text_input("**Matrikel**", value="12345678", label_visibility="collapsed")

# ============================================================================
# Hauptlayout: Links Gliederung, rechts Editor
# ============================================================================
col_left, col_right = st.columns([0.2, 0.8])  # 20% links für Gliederung

# ============================================================================
# RECHTS: KLAUSUR-EDITOR
# ============================================================================
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
        height=800,  # großer Editor
        label_visibility="collapsed"
    )
    st.session_state.content = content

# ============================================================================
# LINKS: Scrollbare Gliederung (nur Überschriften)
# ============================================================================
with col_left:
    st.markdown("### 📋 Gliederung")
    toc_container = st.container()
    
    lines = content.split('\n')
    toc_compact = []
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
        for level, pattern in enumerate(patterns, 1):
            if re.match(pattern, text):
                toc_compact.append((i, text, level))
                toc_levels[i] = level
                break
    
    st.session_state.toc_levels = toc_levels
    
    # Scrollbare Buttons
    for idx, (line_no, text, level) in enumerate(toc_compact):
        indent = (level-1) * 10
        short_text = text if len(text) <= 30 else text[:30]+"..."
        if st.button(short_text, key=f"toc_{idx}", help=text):
            st.session_state.cursor_line = line_no
            st.experimental_rerun()

# ============================================================================
# Mini Status unten
# ============================================================================
st.markdown("---")
elapsed = st.session_state.get('elapsed_time', 0)
st.markdown(f"""
<div style='text-align: right; color: #666; font-size: 0.9em;'>
    {len(content):,} Zeichen | ⏱️ {elapsed//60:02d}:{elapsed%60:02d}
</div>
""", unsafe_allow_html=True)

# ============================================================================
# Buttons: Speichern, Laden, PDF
# ============================================================================
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    if st.button("💾 Speichern"):
        meta_content = f"Titel: {title}\nDatum: {date}\nMatrikelnummer: {matrikel}\n---\n{content}"
        st.download_button("📥 .klausur", meta_content, f"{title.replace(' ', '_')}.klausur", "text/plain")

with col_btn2:
    uploaded = st.file_uploader("📤 Laden", type=['klausur', 'txt'])
    if uploaded:
        st.session_state.content = uploaded.read().decode()
        st.experimental_rerun()

with col_btn3:
    if st.button("🎯 PDF"):
        with st.spinner("PDF wird erstellt..."):
            pdf_bytes = create_perfect_pdf(title, date, matrikel, content)
            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.pdf_name = f"{title.replace(' ', '_')}.pdf"
            st.success("✅ PDF bereit!")
            st.experimental_rerun()

if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF", st.session_state.pdf_bytes, st.session_state.pdf_name, "application/pdf")

# ============================================================================
# PDF GENERIERUNG
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
    
    # Meta-Daten
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, spaceAfter=10, leftIndent=0, alignment=TA_LEFT)
    story.append(Paragraph(f"<b>Matrikel:</b> {matrikel} | <b>Datum:</b> {date}", meta_style))
    
    # Titel
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=20, leftIndent=0, alignment=TA_LEFT)
    story.append(Paragraph(f"<b>{title}</b>", title_style))
    story.append(Spacer(1, 10))
    
    # Gliederung
    story.append(Paragraph("<b>Gliederung</b>", ParagraphStyle('TOC', parent=styles['Heading2'], fontSize=14, spaceAfter=10)))
    for idx, (line_no, text, level) in enumerate(toc_compact):
        indent = (level-1)*10
        story.append(Paragraph(" " * indent + text, styles['Normal']))
    story.append(PageBreak())
    
    # Klausurtext
    text_style = ParagraphStyle(
        'Text',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=14.4,  # 1.2 Zeilenabstand
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=text_style,
        fontName='Helvetica-Bold',
        fontSize=12,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 8))
            continue
        is_heading = any(re.match(p, stripped) for p in patterns)
        if is_heading:
            story.append(Paragraph(stripped, heading_style))
        else:
            story.append(Paragraph(stripped, text_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
