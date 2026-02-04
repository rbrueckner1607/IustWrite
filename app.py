import streamlit as st
import re
import os
import subprocess
import tempfile
from datetime import datetime

# 1. Die Jura-Zähl-Logik (Robust nachgebaut)
class JuraCounter:
    def __init__(self):
        self.counts = [0] * 10
    def increment(self, level):
        self.counts[level-1] += 1
        for i in range(level, 10): self.counts[i] = 0
    def get_label(self, level):
        romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
        n = self.counts[level-1]
        if level == 1: return f"Teil {n}."
        if level == 2: return f"{chr(64 + n)}." # A.
        if level == 3: return f"{romans[n]}." if n < len(romans) else f"{n}." # I.
        if level == 4: return f"{n}."
        if level == 5: return f"{chr(96 + n)}." # a)
        if level == 6: return f"{chr(96 + n)}{chr(96 + n)}." # aa)
        return str(n)

# 2. Die Erkennungs-Muster (Deine Sternchen-Logik)
PATTERNS = {
    1: r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\*',
    2: r'^[A-H]\*',
    3: r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)\*',
    4: r'^\d+\*',
    5: r'^[a-z]\*'
}

# 3. Web-Interface Setup
st.set_page_config(page_title="LexGerm Editor", layout="wide")
st.title("⚖️ LexGerm | iustWrite Editor")

with st.sidebar:
    st.header("📄 Klausurdaten")
    titel = st.text_input("Titel", "Übungsklausur")
    st.header("📋 Gliederung")
    gliederung_area = st.empty()

col1, col2 = st.columns([3, 1]) # Editor bekommt mehr Platz

with col1:
    content = st.text_area("Schreibe dein Gutachten (Nutze A*, I*, 1* für Überschriften):", height=600)

# 4. Logik-Verarbeitung
counter = JuraCounter()
sidebar_content = ""
latex_body = []

for line in content.split('\n'):
    line_strip = line.strip()
    if not line_strip:
        latex_body.append(r"\par\medskip")
        continue
    
    found = False
    for level, pattern in PATTERNS.items():
        if re.match(pattern, line_strip):
            counter.increment(level)
            label = counter.get_label(level)
            text = line_strip.split('*', 1)[1].strip()
            
            # Sidebar Anzeige
            indent = "&nbsp;" * (level * 4)
            sidebar_content += f"{indent}**{label} {text}**  \n"
            
            # LaTeX PDF Logik (mit Gliederungsebenen)
            cmd = "section" if level == 1 else "subsection" if level == 2 else "subsubsection" if level == 3 else "paragraph"
            latex_body.append(f"\\{cmd}*{{{label} {text}}}")
            latex_body.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{{label} {text}}}")
            found = True
            break
    
    if not found:
        # Normaler Text und Fußnoten \fn(text)
        txt = re.sub(r'\\fn\(([^)]*)\)', r'\\footnote{\1}', line_strip)
        latex_body.append(txt)

# Sidebar füllen
gliederung_area.markdown(sidebar_content, unsafe_allow_html=True)

# 5. PDF Export
if st.button("🚀 PDF generieren (6cm Rand)"):
    latex_full = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[left=2cm,right=6cm,top=2cm,bottom=2cm]{geometry}
\usepackage{setspace}
\onehalfspacing
\renewcommand{\contentsname}{Gliederung}
\begin{document}
""" + f"\\section*{{{titel}}} \\tableofcontents \\newpage" + "\n".join(latex_body) + r"\end{document}"

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "klausur.tex"), "w", encoding="utf-8") as f:
            f.write(latex_full)
        try:
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdir, check=True)
            with open(os.path.join(tmpdir, "klausur.pdf"), "rb") as f:
                st.download_button("⬇️ PDF Download", f, file_name=f"{titel}.pdf")
        except:
            st.error("LaTeX-Fehler: Bitte prüfe Sonderzeichen im Text.")
