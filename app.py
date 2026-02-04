import streamlit as st
from datetime import datetime
import re

st.set_page_config(page_title="iustWrite | lexgerm.de", layout="wide")

# -----------------------------
# METADATEN + EXPORT BUTTONS
# -----------------------------
st.markdown("---")
col_meta1, col_meta2, col_meta3, col_btns = st.columns([1,1,2,1])

with col_meta1:
    title = st.text_input("Titel", value="Zivilrecht I - Klausur", label_visibility="collapsed")
with col_meta2:
    date = st.date_input("Datum", value=datetime.now().date(), label_visibility="collapsed")
with col_meta3:
    matrikel = st.text_input("Matrikel", value="12345678", label_visibility="collapsed")

with col_btns:
    col_save, col_load, col_pdf = st.columns(3)
    with col_save:
        if st.button("💾 Speichern", use_container_width=True):
            content = st.session_state.get('content','')
            meta_content = f"Titel: {title}\nDatum: {date}\nMatrikelnummer: {matrikel}\n---\n{content}"
            st.download_button("📥 .klausur", meta_content, f"{title.replace(' ','_')}.klausur", "text/plain")
    with col_load:
        uploaded = st.file_uploader("📤 Laden", type=['klausur', 'txt'], label_visibility="collapsed")
        if uploaded:
            st.session_state.content = uploaded.read().decode()
            st.success("✅ Geladen!")
    with col_pdf:
        if st.button("🎯 PDF", use_container_width=True):
            st.success("✅ PDF-Export bereit!")

# -----------------------------
# LINKS: Gliederung, scrollbar
# -----------------------------
col_left, col_right = st.columns([0.15,0.85])

with col_left:
    st.markdown("### 📋 Gliederung")
    if 'content' not in st.session_state:
        st.session_state.content = ""

    lines = st.session_state.content.split('\n')
    
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
    
    toc_compact = []
    for i, line in enumerate(lines):
        text = line.strip()
        if not text: continue
        for level, pattern in enumerate(patterns,1):
            if re.match(pattern, text):
                toc_compact.append((i,text,level))
                break
    st.session_state.toc_compact = toc_compact

    st.markdown("<div style='height:400px; overflow-y:auto;'>", unsafe_allow_html=True)
    for idx, (line_no, text, level) in enumerate(toc_compact):
        short_text = text if len(text)<=30 else text[:30]+"..."
        if st.button(short_text, key=f"toc_{idx}", help=text):
            st.session_state['cursor_line'] = line_no
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# RECHTS: Editor, maximaler Platz
# -----------------------------
with col_right:
    default_text = """Teil 1. Zulässigkeit

A. Formelle Voraussetzungen

I. Antragsbegründung

1. Fristgerechtigkeit

a) Einreichungsfrist

II. Begründetheit"""

    content = st.text_area(
        "",
        value=st.session_state.get('content', default_text),
        height=900,
        label_visibility="collapsed"
    )
    st.session_state.content = content

    # Cursor setzen + scrollen
    if 'cursor_line' in st.session_state:
        cursor_js = f"""
        <script>
        var textarea = window.parent.document.querySelector('textarea');
        if (textarea) {{
            var lines = textarea.value.split('\\n');
            var pos = 0;
            for (var i=0;i<{st.session_state['cursor_line']};i++) pos += lines[i].length+1;
            textarea.focus();
            textarea.setSelectionRange(pos,pos);
            var lineHeight = 20;  // geschätzte Höhe pro Zeile
            textarea.scrollTop = pos/textarea.value.length * textarea.scrollHeight - 60;
        }}
        </script>
        """
        st.components.v1.html(cursor_js, height=0)
        del st.session_state['cursor_line']
