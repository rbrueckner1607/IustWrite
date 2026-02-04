import streamlit as st
import tempfile
import os
import subprocess
import re
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DAS GEHIRN (DEINE JURA-LOGIK)
# ═══════════════════════════════════════════════════════════════════════════════

class HeadingCounter:
    def __init__(self):
        self.counters = [0] * 15

    def increment(self, level):
        idx = level - 1
        self.counters[idx] += 1
        for i in range(idx + 1, 15):
            self.counters[i] = 0

    def get_numbering(self, level):
        romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
        def letter(n): return chr(96 + n) if 1 <= n <= 26 else str(n)
        parts = []
        for i in range(level):
            n = self.counters[i]
            if n == 0: continue
            if i == 0: parts.append(f"Teil {n}.")
            elif i == 1: parts.append(chr(64 + n) + ".") # A.
            elif i == 2: parts.append(romans[n] + ".") if n < len(romans) else parts.append(str(n)+".")
            elif i == 3: parts.append(f"{n}.")
            elif i == 4: parts.append(f"{letter(n)})")
            elif i == 5: parts.append(f"{letter(n)*2})")
            elif i == 6: parts.append(f"({letter(n)})")
            elif i == 7: parts.append(f"({letter(n)*2})")
        return " ".join(parts)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. DAS DESIGN (DEIN COCKPIT)
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="LexGerm Editor", layout="wide")

# CSS für echte Jura-Optik (Serifenschrift im Editor)
st.markdown("""
<style>
    .stTextArea textarea {
        font-family: "Times New Roman", Times, serif;
        font-size: 18px !important;
        line-height: 1.5 !important;
    }
    .gliederung-item {
        font-family: sans-serif;
        font-size: 14px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ LexGerm | iustWrite Editor")

# Sidebar für Meta & Gliederung
with st.sidebar:
    st.header("📄 Metadaten")
    k_title = st.text_input("Titel", "Übungsklausur")
    k_date = st.text_input("Datum", datetime.now().strftime("%d.%m.%Y"))
    k_matrikel = st.text_input("Matrikel-Nr.")
    st.divider()
    st.header("📋 Live-Gliederung")
    gliederung_placeholder = st.empty()

# Editor
user_input = st.text_area("Schreibe hier dein Gutachten...", height=650, key="editor_input")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. VERARBEITUNG (PARSER)
# ═══════════════════════════════════════════════════════════════════════════════

patterns = {
    1: r'^(Teil|Tatkomplex|Aufgabe)\s+\d+\*',
    2: r'^[A-H]\*',
    3: r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)\*',
    4: r'^\d+\*',
    5: r'^[a-z]\*',
    6: r'^[a-z]{2}\*',
    7: r'^\([a-z]\)\*',
    8: r'^\([a-z]{2}\)\*'
}

h_counter = HeadingCounter()
lines = user_input.split('\n')
sidebar_html = ""
latex_body = []

for line in lines:
    clean_line = line.strip()
    if not clean_line:
        latex_body.append(r"\par\medskip")
        continue

    matched = False
    for level, pattern in patterns.items():
        if re.match(pattern, clean_line):
            h_counter.increment(level)
            num = h_counter.get_numbering(level)
            # Text nach dem Sternchen holen
            title_text = clean_line.split('*', 1)[1].strip()
            
            # 1. Für Sidebar (HTML)
            indent = (level - 1) * 15
            sidebar_html += f'<div class="gliederung-item" style="margin-left:{indent}px;"><b>{num} {title_text}</b></div>'
            
            # 2. Für LaTeX
            cmd = "section" if level == 1 else "subsection" if level == 2 else "subsubsection" if level == 3 else "paragraph"
            latex_body.append(f"\\{cmd}*{{{num} {title_text}}}")
            latex_body.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{{num} {title_text}}}")
            matched = True
            break
    
    if not matched:
        # Normaler Text & Fußnoten \fn(text)
        text_with_fn = re.sub(r'\\fn\(([^)]*)\)', r'\\footnote{\1}', clean_line)
        latex_body.append(text_with_fn)

# Gliederung in Sidebar ausgeben
gliederung_placeholder.markdown(sidebar_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

if st.button("🚀 PDF generieren"):
    if user_input:
        with st.spinner("LaTeX wird kompiliert..."):
            latex_code = r"""
\documentclass[12pt, a4paper]{article}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[left=2.5cm, right=6cm, top=2.5cm, bottom=3cm]{geometry}
\usepackage{setspace}
\usepackage{tocloft}
\renewcommand{\contentsname}{Gliederung}
\onehalfspacing
\begin{document}
""" + f"\\noindent \\textbf{{{k_title}}} \\hfill {k_date} \\\\ Matrikel-Nr.: {k_matrikel} \\vspace{{1cm}} \\\\ \\tableofcontents \\newpage \\pagenumbering{{arabic}}" + "\n".join(latex_body) + r"\end{document}"

            with tempfile.TemporaryDirectory() as tmpdir:
                tex_file = os.path.join(tmpdir, "klausur.tex")
                with open(tex_file, "w", encoding="utf-8") as f:
                    f.write(latex_code)
                try:
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdir, check=True)
                    with open(os.path.join(tmpdir, "klausur.pdf"), "rb") as f:
                        st.download_button("⬇️ PDF Herunterladen", f, file_name=f"{k_title}.pdf")
                    st.success("Fertig!")
                except:
                    st.error("Fehler im LaTeX. Bitte prüfen.")
