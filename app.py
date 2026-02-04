import streamlit as st
import tempfile
import os
import subprocess
import pytinytex
from datetime import datetime

# Deine bestehenden Klassen (1:1 übernommen!)
class HeadingCounter:
    # ... (exakt wie in deinem Code)
    
class KlausurDocument:
    def __init__(self):
        self.heading_counter = HeadingCounter()
        self.prefix_patterns = { ... }  # Deine Patterns
        self.title_patterns = { ... }
        
    def from_text(self, text, title, date, matrikel):
        self.meta = {"title": title, "date": date, "matrikel": matrikel}
        self.lines = text.splitlines()
        
    def to_latex(self):
        # EXAKT dein export_latex() ohne GUI-Teile
        latex = []
        # ... deine LaTeX-Generierung
        return "\n".join(latex)
    
    def to_pdf(self, latex_content):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "klausur.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)
            
            # Deine pdflatex-Logik hier
            tiny_base = pytinytex.get_tinytex_path()
            pdflatex_bin = ...  # Suche wie bisher
            subprocess.run([pdflatex_bin, tex_path], cwd=tmpdir, check=True)
            return os.path.join(tmpdir, "klausur.pdf")

# Streamlit Frontend
st.set_page_config(page_title="iustWrite | lexgerm.de", layout="wide")

st.title("👨‍⚖️ iustWrite - Jura Klausur Editor")
st.markdown("**Für lexgerm.de** - Automatische Nummerierung • Live-Gliederung • PDF-Export")

# Sidebar Meta
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", value="Zivilrecht I - Klausur")
    date = st.date_input("Datum", value=datetime.now())
    matrikel = st.text_input("Matrikel-Nr.")
    
    if st.button("🆕 Neue Klausur"):
        st.session_state.content = ""

# Main Editor (2 Spalten)
col1, col2 = st.columns([1, 3])

with col1:
    st.header("📋 Gliederung")
    toc = st.session_state.get("toc", [])
    for item in toc:
        st.write(item)

with col2:
    st.header("✍️ Editor")
    content = st.text_area(
        "Klausurtext (Strg+1-8 für Überschriften)",
        value=st.session_state.get("content", ""),
        height=600,
        key="content_input"
    )

# Live TOC Update
if content != st.session_state.get("last_content"):
    doc = KlausurDocument()
    doc.from_text(content, title, str(date), matrikel)
    st.session_state.toc = doc.generate_toc()  # Neue Methode
    st.session_state.last_content = content

# Buttons
col_pdf, col_download = st.columns(2)
with col_pdf:
    if st.button("🎯 PDF exportieren"):
        with st.spinner("Erstelle PDF..."):
            doc = KlausurDocument()
            doc.from_text(content, title, str(date), matrikel)
            latex = doc.to_latex()
            pdf_bytes = doc.to_pdf(latex)
            
            st.session_state.pdf_bytes = pdf_bytes
            st.success("✅ PDF bereit!")

if hasattr(st.session_state, "pdf_bytes"):
    with col_download:
        st.download_button(
            "⬇️ PDF herunterladen",
            data=st.session_state.pdf_bytes,
            file_name=f"{title.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
