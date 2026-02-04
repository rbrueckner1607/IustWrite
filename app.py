import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, TableOfContents
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

# Hauptlayout - MAXIMALER Schreibplatz rechts
col_left, col_right = st.columns([0.18, 0.82])  # 18% links, 82% rechts!

# ============================================================================
# LINKS: KLEINE, EINFACHE GLIEDERUNG (nur Überschriften)
# ============================================================================
with col_left:
    st.markdown("### 📋 Gliederung")
    
    # KOMPAKTE Liste - nur Überschriften
    if 'toc_compact' in st.session_state:
        for idx, item in enumerate(st.session_state.toc_compact):
            level = st.session_state.toc_levels.get(idx, 1)
            marker = ["▸", "├", "└"][min(level-1, 2)]
            short_item = item[:35] + "..." if len(item) > 35 else item
            if st.button(f"{marker} {short_item}", key=f"tocbtn_{idx}", use_container_width=True):
                st.session_state.selected_line = idx
                st.rerun()

# ============================================================================
# RECHTS: GIGANTISCHER EDITOR (82% Platz!)
# ============================================================================
with col_right:
    st.markdown("### ✍️ Klausur Editor")
    
    default_text = """Teil 1. Zulässigkeit

A. Formelle Voraussetzungen

I. Antragsbegründung

1. Fristgerechtigkeit

a) Einreichungsfrist

II. Begründetheit"""
    
    content = st.text_area(
        "",
        value=st.session_state.get('content', default_text),
        height=850,  # MAXIMAL!
        label_visibility="collapsed"
    )

# ============================================================================
# LIVE GLIEDERUNG + TIMER (unsichtbar)
# ============================================================================
if content != st.session_state.get('last_content', ''):
    st.session_state.last_content = content
    
    # Timer starten
    if 'start_time' not in st.session_state:
        st.session_state.start_time = datetime.now()
    elapsed = int((datetime.now() - st.session_state.start_time).total_seconds())
    st.session_state.elapsed_time = elapsed
    
    # KOMPAKTE Gliederung generieren
    lines = content.split('\n')
    toc_compact = []
    toc_levels = {}
    
    # DEINE Patterns (vereinfacht)
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
                toc_compact.append(text)
                toc_levels[i] = level
                break
    
    st.session_state.toc_compact = toc_compact
    st.session_state.toc_levels = toc_levels
    st.rerun()

# ============================================================================
# MINI STATUS (unten rechts)
# ============================================================================
st.markdown("---")
st.markdown(f"""
<div style='text-align: right; color: #666; font-size: 0.9em;'>
    {len(content):,} Zeichen | ⏱️ {st.session_state.get('elapsed_time', 0)//60:02d}:{st.session_state.get('elapsed_time', 0)%60:02d}
</div>
""", unsafe_allow_html=True)

# ============================================================================
# BUTTONS (kompakt)
# ============================================================================
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    if st.button("💾 Speichern", use_container_width=True):
        meta_content = f"Titel: {title}\nDatum: {date}\nMatrikelnummer: {matrikel}\n---\n{content}"
        st.download_button("📥 .klausur", meta_content, f"{title.replace(' ', '_')}.klausur", "text/plain")

with col_btn2:
    uploaded = st.file_uploader("📤 Laden", type=['klausur', 'txt'], label_visibility="collapsed")
    if uploaded:
        st.session_state.content = uploaded.read().decode()
        st.success("✅ Geladen!")
        st.rerun()

with col_btn3:
    if st.button("🎯 PDF", use_container_width=True):
        with st.spinner("PDF wird erstellt..."):
            pdf_bytes = create_perfect_pdf(title, date, matrikel, content)
            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.pdf_name = f"{title.replace(' ', '_')}.pdf"
            st.success("✅ PDF bereit!")
            st.rerun()

if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF", st.session_state.pdf_bytes, st.session_state.pdf_name, "application/pdf")

# ============================================================================
# PERFEKTE PDF GENERIERUNG (GENAU deine Spezifikationen)
# ============================================================================
def create_perfect_pdf(title, date, matrikel, content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=6*cm,      # 6cm Korrekturrand rechts!
        leftMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=3*cm
    )
    story = []
    styles = getSampleStyleSheet()
    
    # 1. STAMMDATEN (ganz oben)
    meta_style = ParagraphStyle(
        'Meta', parent=styles['Normal'], fontSize=10, spaceAfter=20,
        leftIndent=0, alignment=TA_LEFT
    )
    story.append(Paragraph(f"<b>Matrikel-Nr.:</b> {matrikel} | <b>Datum:</b> {date}", meta_style))
    
    # 2. TITEL
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=16, spaceAfter=30,
        leftIndent=0, alignment=TA_LEFT
    )
    story.append(Paragraph(f"<b>{title}</b>", title_style))
    story.append(Spacer(1, 20))
    
    # 3. GLIEDERUNG (keine Seitenzahlen!)
    gliederung_style = ParagraphStyle(
        'Gliederung', parent=styles['Heading2'], 
        fontSize=14, spaceAfter=10, spaceBefore=20
    )
    story.append(Paragraph("**Gliederung**", gliederung_style))
    
    # Einfache Gliederung (kein TOC - einfacher!)
    lines = content.split('\n')
    gliederung_items = []
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
    
    for line in lines:
        text = line.strip()
        if not text: continue
        
        for level, pattern in enumerate(patterns, 1):
            if re.match(pattern, text):
                indent = "   " * (level - 1)
                gliederung_items.append(f"{indent}{text}")
                break
    
    # Gliederung als einfache Liste
    for item in gliederung_items[:15]:  # Max 15 Einträge
        story.append(Paragraph(item, styles['Normal']))
        story.append(Spacer(1, 3))
    
    story.append(PageBreak())
    
    # 4. KLAUSURTEXT (BlockSatz 1.2 Zeilenabstand)
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
    
    # Überschriften inline fett (keine Einrückung!)
    for line in lines:
        text = line.strip()
        if not text:
            story.append(Spacer(1, 8))
            continue
            
        # Überschrift? → FETT
        is_heading = False
        for pattern in patterns:
            if re.match(pattern, text):
                heading_style = ParagraphStyle(
                    'InlineHeading',
                    parent=text_style,
                    fontName='Helvetica-Bold',
                    fontSize=12,
                    spaceAfter=8,
                    alignment=TA_LEFT,
                    leftIndent=0
                )
                story.append(Paragraph(text, heading_style))
                is_heading = True
                break
        
        if not is_heading:
            # Normaltext Blocksatz
            story.append(Paragraph(text, text_style))
    
    doc.build(story, onFirstPage=first_page_no_number, onLaterPages=later_pages)
    buffer.seek(0)
    return buffer.getvalue()

# ============================================================================
# SEITENNUMMERIERUNG (erst ab Klausurtext!)
# ============================================================================
def first_page_no_number(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 10)
    canvas.drawRightString(A4[0] - 2*cm, 2*cm, f"Matrikel: {matrikel}")
    canvas.restoreState()

def later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 10)
    canvas.drawRightString(A4[0] - 2*cm, 2*cm, str(doc.page))
    canvas.restoreState()

# Footer
st.markdown("---")
st.markdown("*iustWrite für lexgerm.de • Studentisches Projekt*")
