import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.rl_config import defaultPageSize
from io import BytesIO
import re

st.set_page_config(page_title="iustWrite | lexgerm.de", layout="wide")

# Sidebar (ausklappbar)
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("**Titel**", value="Zivilrecht I - Klausur")
    date = st.date_input("**Datum**", value=datetime.now().date())
    matrikel = st.text_input("**Matrikel-Nr.**", value="12345678")
    
    st.markdown("---")
    st.caption("**Shortcuts:** Strg+1-8 = Überschriften")
    if st.button("🆕 Neue Klausur", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Hauptlayout
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("⚖️ iustWrite - Jura Klausur Editor")
with header_col2:
    if 'elapsed_time' in st.session_state:
        st.metric("⏱️ Zeit", f"{st.session_state.elapsed_time//60:02d}:{st.session_state.elapsed_time%60:02d}")

col1, col2 = st.columns([0.25, 0.75])

# ════════════════════════════════════════════════════════════════════════════════
# LINKS: NAVIGIERBARE GLIEDERUNG (Klick springt zur Zeile!)
# ════════════════════════════════════════════════════════════════════════════════
with col1:
    st.markdown("### 📋 **Gliederung**")
    
    # Toggle für ein/ausblenden
    if st.toggle("Gliederung ausblenden", key="toc_toggle"):
        st.empty()
    else:
        if 'toc_items' in st.session_state:
            for idx, toc_item in enumerate(st.session_state.toc_items):
                level = st.session_state.toc_levels.get(idx, 1)
                indent = "  " * (level - 1)
                display_text = f"{indent}▸ {toc_item}"
                
                if st.button(display_text, key=f"toc_{idx}", use_container_width=True):
                    st.session_state.selected_line = idx
                    st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# RECHTS: EDITOR mit FETTEN ÜBERSCHRIFTEN
# ════════════════════════════════════════════════════════════════════════════════
with col2:
    st.markdown("### ✍️ **Klausur Editor**")
    
    # Beispielttext
    default_text = """Teil 1. Zulässigkeit

A. Formelle Voraussetzungen

I. Antragsbegründung

1. Fristgerechtigkeit

a) Einreichungsfrist

II. Begründetheit

B. Sachliche Voraussetzungen"""
    
    content = st.text_area(
        "",
        value=st.session_state.get('content', default_text),
        height=700,
        key="editor_content"
    )

# ════════════════════════════════════════════════════════════════════════════════
# LIVE VERARBEITUNG (wie PyQt on_text_changed)
# ════════════════════════════════════════════════════════════════════════════════
if content != st.session_state.get('last_content', ''):
    st.session_state.last_content = content
    
    # 1. TIMER (wie PyQt)
    if 'start_time' not in st.session_state:
        st.session_state.start_time = time.time()
    st.session_state.elapsed_time = int(time.time() - st.session_state.start_time)
    
    # 2. GLIEDERUNG generieren (deine Patterns)
    lines = content.split('\n')
    toc_items = []
    toc_levels = {}
    
    patterns = {
        1: r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\.',
        2: r'^[A-I]\.',
        3: r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)',
        4: r'^\d+\.',
        5: r'^[a-z]\)',
        6: r'^[a-z]{2}\)',
        7: r'^\([a-z]\)',
        8: r'^\([a-z]{2}\)'
    }
    
    for i, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
            
        for level, pattern in patterns.items():
            if re.match(pattern, text):
                toc_items.append(text[:50] + ('...' if len(text) > 50 else ''))
                toc_levels[i] = level
                break
    
    st.session_state.toc_items = toc_items
    st.session_state.toc_levels = toc_levels
    
    st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# STATUSLEISTE (wie PyQt)
# ════════════════════════════════════════════════════════════════════════════════
if content.strip():
    chars = len(content)
    words = len(re.findall(r'\w+', content))
    st.markdown(f"**Status**: {chars:,} Zeichen | {words:,} Wörter | ⏱️ {st.session_state.elapsed_time//60:02d}:{st.session_state.elapsed_time%60:02d}")

# ════════════════════════════════════════════════════════════════════════════════
# BUTTONS
# ════════════════════════════════════════════════════════════════════════════════
col1, col2, col3 = st.columns(3)

with col1:
    # SAVE
    if st.button("💾 **Als .klausur speichern**", use_container_width=True):
        content_with_meta = f"""Titel: {title}
Datum: {date}
Matrikelnummer: {matrikel}
---
{content}"""
        st.download_button(
            "📥 Download .klausur",
            data=content_with_meta,
            file_name=f"{title.replace(' ', '_')}.klausur",
            mime="text/plain"
        )

with col2:
    # UPLOAD
    uploaded_file = st.file_uploader("📤 .klausur laden", type=['klausur', 'txt'])
    if uploaded_file:
        content = uploaded_file.read().decode('utf-8')
        st.session_state.content = content
        st.success("✅ Datei geladen!")
        st.rerun()

with col3:
    # PDF EXPORT (EINFACH mit reportlab!)
    if st.button("🎯 **PDF erstellen**", use_container_width=True):
        with st.spinner("Erstelle PDF mit Gliederung..."):
            try:
                pdf_bytes = create_pdf(title, date, matrikel, content.split('\n'))
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_name = f"{title.replace(' ', '_')}_{date.strftime('%d%m%Y')}.pdf"
                st.success("✅ PDF fertig!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ PDF Fehler: {str(e)}")

# PDF Download
if 'pdf_bytes' in st.session_state:
    st.download_button(
        "⬇️ **PDF herunterladen**",
        st.session_state.pdf_bytes,
        st.session_state.pdf_name,
        "application/pdf",
        use_container_width=True
    )

# ════════════════════════════════════════════════════════════════════════════════
# PDF GENERIERUNG (EINFACH - KEIN LaTeX!)
# ════════════════════════════════════════════════════════════════════════════════
def create_pdf(title, date, matrikel, lines):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=6*cm)
    story = []
    styles = getSampleStyleSheet()
    
    # Titel
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_LEFT
    )
    story.append(Paragraph(f"<b>{title}</b> ({date})", title_style))
    story.append(Spacer(1, 12))
    
    # Gliederung
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(fontName='Helvetica-Bold', fontSize=12),
        ParagraphStyle(fontName='Helvetica-Bold', fontSize=11),
        ParagraphStyle(fontName='Helvetica', fontSize=10),
    ]
    story.append(Paragraph("Gliederung", styles['Heading2']))
    story.append(toc)
    story.append(PageBreak())
    
    # Inhalt mit korrekter Nummerierung
    patterns = {
        1: r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\.',
        2: r'^[A-I]\.',
        3: r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)',
        4: r'^\d+\.',
        5: r'^[a-z]\)',
        6: r'^[a-z]{2}\)',
        7: r'^\([a-z]\)',
        8: r'^\([a-z]{2}\)'
    }
    
    for line in lines:
        text = line.strip()
        if not text:
            story.append(Spacer(1, 6))
            continue
            
        # Überschrift erkennen → fett
        is_heading = False
        for level, pattern in patterns.items():
            if re.match(pattern, text):
                style = ParagraphStyle(
                    f'Heading{level}',
                    parent=styles['Heading2'],
                    fontSize=12-level,
                    spaceAfter=6,
                    fontName='Helvetica-Bold',
                    leftIndent=(level-1)*0.5*cm,
                    alignment=TA_LEFT
                )
                story.append(Paragraph(text, style))
                toc.addEntry(level, text, len(story)-1, 0)
                is_heading = True
                break
        
        if not is_heading:
            # Normaltext
            style = ParagraphStyle(
                'NormalText',
                parent=styles['Normal'],
                alignment=TA_JUSTIFY,
                spaceAfter=4,
                leftIndent=1*cm
            )
            story.append(Paragraph(re.sub(r'\\\\fn\((.*?)\)', r'<super>\1</super>', text), style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
