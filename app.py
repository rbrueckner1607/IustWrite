import streamlit as st
from streamlit_ace import st_ace
import tempfile
import os
import subprocess
import shutil
import re
from datetime import datetime

# 1. JURA LOGIK & PARSER (Optimiert für 8 Ebenen)
class KlausurDocument:
    def __init__(self):
        self.patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\*|\.)',
            2: r'^\s*[A-H](\*|\.)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)(\*|\.)',
            4: r'^\s*\d+(\*|\.)',
            5: r'^\s*[a-z]\)',
            6: r'^\s*[a-z]{2}\)',
            7: r'^\s*\([a-z]\)',
            8: r'^\s*\([a-z]{2}\)'
        }

    def get_toc_with_lines(self, text):
        toc = []
        lines = text.split('\n')
        for idx, line in enumerate(lines):
            clean = line.strip()
            for level, pattern in self.patterns.items():
                if re.match(pattern, clean):
                    toc.append({"level": level, "text": clean, "line": idx + 1})
                    break
        return toc

# 2. WEB-APP SETUP
st.set_page_config(page_title="iustWrite PRO", layout="wide")

# CSS für Word-Feeling und Sidebar-Fixierung
st.markdown("""
<style>
    .sidebar-content { position: fixed; top: 50px; width: 18%; overflow-y: auto; height: 85vh; }
    .editor-container { margin-left: 20%; }
</style>
""", unsafe_allow_html=True)

doc = KlausurDocument()

# --- SIDEBAR (GLIEDERUNG & METADATEN) ---
with st.sidebar:
    st.title("⚖️ iustWrite")
    titel = st.text_input("Klausurtitel", value="Zivilrechtliche Klausur")
    matrikel = st.text_input("Matrikel-Nr.")
    
    st.divider()
    st.subheader("📋 Gliederung (Klick springt)")
    
    # Text aus Session State holen
    current_text = st.session_state.get("content", "")
    toc_data = doc.get_toc_with_lines(current_text)
    
    # Navigations-Buttons in der Sidebar
    for item in toc_data:
        indent = "&nbsp;" * (item["level"] * 3)
        if st.button(f"{indent}{item['text']}", key=f"nav_{item['line']}"):
            st.session_state.jump_to = item["line"]

# --- HAUPTBEREICH (EDITOR) ---
col1, col2 = st.columns([1, 4]) # Abstandshalter

with col2:
    # Speichern / Laden Funktionen
    c1, c2, c3 = st.columns(3)
    with c1:
        uploaded_file = st.file_uploader("Datei laden (.txt)", type="txt")
        if uploaded_file:
            st.session_state.content = uploaded_file.read().decode("utf-8")
    
    with c2:
        st.download_button("💾 Text lokal speichern", current_text, file_name="klausur_entwurf.txt")

    # DER EDITOR (Ace Editor für Zeilenspringen)
    content = st_ace(
        value=st.session_state.get("content", ""),
        height=700,
        language="text",
        theme="chrome",
        font_size=16,
        wrap=True,
        auto_update=True,
        key="ace_editor"
    )
    st.session_state.content = content

# --- PDF EXPORT LOGIK ---
if st.button("🚀 PDF EXPORT (6cm Rand + Gliederung)"):
    with st.spinner("Erzeuge Gliederung und PDF..."):
        # LaTeX Template (Professionell)
        latex_header = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern, geometry, setspace, tocloft, fancyhdr}
\geometry{left=2cm,right=6cm,top=2.5cm,bottom=3cm}
\onehalfspacing
\renewcommand{\contentsname}{Gliederung}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{""" + titel + r"""}
\fancyhead[R]{Seite \thepage}
\begin{document}
\tableofcontents\newpage
"""
        # (Hier käme deine Parser-Logik für die Umwandlung von Text in \section etc.)
        latex_body = content.replace("\n", "\n\n") # Minimalbeispiel
        latex_final = latex_header + latex_body + r"\end{document}"

        # PDF Erzeugung (2x für TOC)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "klausur.tex")
            with open(path, "w", encoding="utf-8") as f: f.write(latex_final)
            pdflatex = shutil.which("pdflatex")
            for _ in range(2):
                subprocess.run([pdflatex, "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdir)
            
            with open(os.path.join(tmpdir, "klausur.pdf"), "rb") as f:
                st.download_button("⬇️ PDF JETZT HERUNTERLADEN", f, file_name="klausur.pdf")
