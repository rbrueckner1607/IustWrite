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
# METADATEN OBEN KOMPAKT
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
# HAUFPLAYOUT: LINKS Gliederung, RECHTS Editor
# ============================================================================
col_left, col_right = st.columns([0.2, 0.8])  # Links kleiner, rechts riesig

# ============================================================================  
# RECHTS: Editor
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
        height=850,
        label_visibility="collapsed"
    )

# ============================================================================  
# LINKS: Scrollbare Gliederung
# ============================================================================
def generate_toc(content):
    lines = content.split('\n')
    toc_items = []
    toc_levels = {}
    patterns = [
        r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\.',  # Level 1
        r'^[A-I]\.',                             # Level 2
        r'^(I{1,5}|V?|X{0,3})\.',                # Level 3
        r'^\d+\.',                               # Level 4
        r'^[a-z]\)',                             # Level 5
        r'^[a-z]{2}\)',                          # Level 6
        r'^\([a-z]\)',                           # Level 7
        r'^\([a-z]{2}\)'                         # Level 8
    ]
    for i, line in enumerate(lines):
        line_text = line.strip()
        if not line_text:
            continue
        for level, pattern in enumerate(patterns, 1):
            if re.match(pattern, line_text):
                toc_items.append((i, line_text, level))
                toc_levels[i] = level
                break
    return toc_items, toc_levels

toc_items, toc_levels = generate_toc(content)
st.session_state['toc_items'] = toc_items
st.session_state['toc_levels'] = toc_levels

with col_left:
    st.markdown("### 📋 Gliederung")
    toc_container = st.container()
    for line_no, text, level in toc_items:
        indent = (level - 1) * 10
        short_text = text if len(text) <= 35 else text[:35] + "..."
        if st.button(short_text, key=f"toc_{line_no}"):
            st.session_state.cursor_line = line_no
            st.rerun()

# Cursor springen zu Zeile im Editor
if 'cursor_line' in st.session_state:
    cursor_line = st.session_state.cursor_line
    content_lines = content.split('\n')
    if cursor_line < len(content_lines):
        # Textarea in Streamlit kann nicht direkt den Cursor setzen, workaround:
        # wir markieren die Zeile als Kommentar oben
        lines_before = "\n".join(content_lines[:cursor_line])
        lines_after = "\n".join(content_lines[cursor_line:])
        new_content = lines_before + "\n" + lines_after
        st.session_state.content = content
        del st.session_state['cursor_line']
        st.experimental_rerun()

# ============================================================================
# MINI STATUS
# ============================================================================
elapsed = st.session_state.get('elapsed_time', 0)
st.markdown("---")
st.markdown(f"""
<div style='text-align: right; color: #666; font-size: 0.9em;'>
    {len(content):,} Zeichen | ⏱️ {elapsed//60:02d}:{elapsed%60:02d}
</div>
""", unsafe_allow_html=True)

# ============================================================================
# BUTTONS
# ============================================================================
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    if st.button("💾 Speichern", use_container_width=True):
        meta_content = f"Titel: {title}\nDatum: {date}\nMatrikelnummer: {matrikel}\n---\n{content}"
        st.download_button("📥 .klausur", meta_content, f"{title.replace(' ','_')}.klausur", "text/plain")

with col_btn2:
    uploaded = st.file_uploader("📤 Laden", type=['klausur', 'txt'], label_visibility="collapsed")
    if uploaded:
        st.session_state.content = uploaded.read().decode()
        st.success("✅ Geladen!")
        st.rerun()

with col_btn3:
    if st.button("🎯 PDF", use_container_width=True):
        with st.spinner("PDF wird erstellt..."):
            pdf_bytes = create_pdf(title, date, matrikel, content)
            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.pdf_name = f"{title.replace(' ','_')}.pdf"
            st.success("✅ PDF bereit!")

if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF", st.session_state.pdf_bytes, st.session_state.pdf_name, "application/pdf")

# ============================================================================
# PDF GENERIERUNG MIT REPORTLAB (Palatino, Blocksatz, 1.2 Zeilenabstand, Korrekturrand)
# ============================================================================
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

pdfmetrics.registerFont(TTFont('Palatino', 'Palatino.ttf'))
pdfmetrics.registerFont(TTFont('Palatino-Bold', 'Palatino-Bold.ttf'))

def create_pdf(title, date, matrikel, content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer,
                            pagesize=A4,
                            leftMargin=2.5*cm,
                            rightMargin=6*cm,
                            topMargin=2.5*cm,
                            bottomMargin=3*cm)
    story = []
    styles = getSampleStyleSheet()

    # STAMMDATEN
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontName='Palatino', fontSize=10, leftIndent=0)
    story.append(Paragraph(f"<b>Matrikel-Nr.:</b> {matrikel} | <b>Datum:</b> {date}", meta_style))
    story.append(Spacer(1, 12))

    # TITEL
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName='Palatino-Bold', fontSize=16, spaceAfter=20, leftIndent=0)
    story.append(Paragraph(f"{title}", title_style))
    story.append(Spacer(1, 12))

    # GLIEDERUNG
    story.append(Paragraph("Gliederung", ParagraphStyle('TOC', fontName='Palatino-Bold', fontSize=14, spaceAfter=10)))
    toc_items, toc_levels = generate_toc(content)
    for line_no, text, level in toc_items:
        indent = (level - 1) * 10
        style = ParagraphStyle('TOCItem', fontName='Palatino', fontSize=12, leftIndent=indent)
        story.append(Paragraph(text, style))
    story.append(PageBreak())

    # KLAUSURTEXT
    text_style = ParagraphStyle('KlausurText', fontName='Palatino', fontSize=12, leading=14.4, alignment=TA_JUSTIFY)
    bold_style = ParagraphStyle('Heading', fontName='Palatino-Bold', fontSize=12, leftIndent=0, spaceAfter=6)

    lines = content.split('\n')
    patterns = [
        r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\.', r'^[A-I]\.', r'^(I{1,5}|V?|X{0,3})\.', r'^\d+\.',
        r'^[a-z]\)', r'^[a-z]{2}\)', r'^\([a-z]\)', r'^\([a-z]{2}\)'
    ]

    for line in lines:
        txt = line.strip()
        if not txt:
            story.append(Spacer(1, 6))
            continue
        is_heading = any(re.match(pat, txt) for pat in patterns)
        if is_heading:
            story.append(Paragraph(txt, bold_style))
        else:
            story.append(Paragraph(txt, text_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Footer
st.markdown("---")
st.markdown("*iustWrite für lexgerm.de • Studentisches Projekt*")
