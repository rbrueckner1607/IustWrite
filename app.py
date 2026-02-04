import streamlit as st
import tempfile
import os
import subprocess
import re
from datetime import datetime

# 1. DER REPARIERTE HEADING-COUNTER
class HeadingCounter:
    def __init__(self, max_level=13):
        self.counters = [0] * max_level

    def increment(self, level):
        idx = level - 1
        self.counters[idx] += 1
        for i in range(idx + 1, len(self.counters)):
            self.counters[i] = 0

    def get_numbering(self, level):
        romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
        def letter(n): return chr(96 + n) if 1 <= n <= 26 else str(n)
        parts = []
        for i in range(level):
            n = self.counters[i]
            if n == 0: continue
            if i == 0: parts.append(f"Teil {n}.")
            elif i == 1: parts.append(chr(64 + n) + ".")
            elif i == 2: parts.append(romans[n] + ".")
            elif i == 3: parts.append(f"{n}.")
            elif i == 4: parts.append(f"{letter(n)})")
        return " ".join(parts)

# 2. DER PARSER (Wird bei jedem Tastendruck neu gestartet -> Kein Hochzählen mehr)
def parse_gliederung(text):
    skizze = []
    local_counter = HeadingCounter() # WICHTIG: Jedes Mal neu!
    for line in text.split('\n'):
        l = line.strip()
        if l.startswith("A."):
            local_counter.increment(2) # Level 2 laut deiner Logik
            skizze.append(f"**{local_counter.get_numbering(2)} {l[2:].strip()}**")
        elif l.startswith("I."):
            local_counter.increment(3)
            skizze.append(f"&nbsp;&nbsp;*{local_counter.get_numbering(3)} {l[2:].strip()}*")
        elif l.startswith("1."):
            local_counter.increment(4)
            skizze.append(f"&nbsp;&nbsp;&nbsp;&nbsp;{local_counter.get_numbering(4)} {l[2:].strip()}")
    return skizze

# 3. DAS INTERFACE (Design-Update)
st.set_page_config(page_title="LexGerm Editor", layout="wide")
st.markdown("""<style> .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 16px !important; } </style>""", unsafe_allow_html=True)

st.title("⚖️ LexGerm Klausuren-Editor")

col_edit, col_nav = st.columns([3, 1])

with col_edit:
    # Textbereich ohne Encoding-Fehler
    content = st.text_area("Dein Gutachten...", height=600, key="editor")

with col_nav:
    st.subheader("Gliederung")
    for s in parse_gliederung(content):
        st.markdown(s, unsafe_allow_html=True)

# 4. PDF EXPORT (6cm Rand + Fix)
if st.button("🚀 PDF generieren"):
    if content:
        with st.spinner("Kompiliere LaTeX..."):
            # LaTeX Template mit 6cm Rand
            latex_template = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[ngerman]{babel}
\usepackage[left=2cm,right=6cm,top=2.5cm,bottom=2.5cm]{geometry}
\usepackage{setspace}
\onehalfspacing
\begin{document}
""" + content.replace("\n", "\n\n") + r"\end{document}"

            with tempfile.TemporaryDirectory() as tmpdir:
                tex_p = os.path.join(tmpdir, "klausur.tex")
                # EXPLIZIT UTF-8 SCHREIBEN
                with open(tex_p, "w", encoding="utf-8") as f:
                    f.write(latex_template)
                
                try:
                    # Aufruf des installierten pdflatex
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   cwd=tmpdir, check=True, capture_output=True)
                    
                    pdf_p = os.path.join(tmpdir, "klausur.pdf")
                    with open(pdf_p, "rb") as f:
                        st.download_button("⬇️ PDF Download", f, "Klausur.pdf", "application/pdf")
                    st.success("Erfolgreich erstellt!")
                except Exception as e:
                    st.error(f"LaTeX Fehler: {e}")
