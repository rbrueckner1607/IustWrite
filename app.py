import streamlit as st
import tempfile
import os
import subprocess
import re
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DEINE LOGIK-KLASSEN (100% DEIN SYSTEM)
# ═══════════════════════════════════════════════════════════════════════════════

class HeadingCounter:
    def __init__(self, max_level=13):
        self.max_level = max_level
        self.counters = [0] * max_level

    def increment(self, level):
        idx = level - 1
        self.counters[idx] += 1
        for i in range(idx + 1, self.max_level):
            self.counters[i] = 0

    def get_numbering(self, level):
        romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII",
                  "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI",
                  "XVII", "XVIII", "XIX", "XX"]
        def letter(n):
            return chr(96 + n) if 1 <= n <= 26 else str(n)
        parts = []
        for i in range(level):
            n = self.counters[i]
            if n == 0: continue
            if i == 0: parts.append(f"Teil {n}.")
            elif i == 1: parts.append(chr(64 + n) + ".")
            elif i == 2: parts.append(romans[n] + ".") if n < len(romans) else parts.append(str(n)+".") 
            elif i == 3: parts.append(f"{n}.")
            elif i == 4: parts.append(f"{letter(n)})")
            elif i == 5: parts.append(f"{letter(n)*2})")
            elif i == 6: parts.append(f"({letter(n)})")
            elif i == 7: parts.append(f"({letter(n)*2})")
            else: parts.append(str(n))
        return " ".join([x for x in parts if x])

class KlausurDocument:
    def __init__(self):
        # Muster für die automatische Erkennung und die Sternchen-Titel
        self.title_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*\s*(.*)',
            2: r'^\s*([A-H])\*\s*(.*)',                           
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*\s*(.*)',
            4: r'^\s*(\d+)\*\s*(.*)',
            5: r'^\s*([a-z])\*\s*(.*)',
            6: r'^\s*([a-z]{2})\*\s*(.*)',
            7: r'^\s*\(([a-z])\)\*\s*(.*)',
            8: r'^\s*\(([a-z]{2})\)\*\s*(.*)'
        }
        self.footnote_pattern = r'\\fn\(([^)]*)\)'
        
    def generate_toc(self, text):
        toc = []
        current_counter = HeadingCounter()
        lines = text.split('\n')
        for line in lines:
            line_strip = line.strip()
            for level, pattern in sorted(self.title_patterns.items()):
                match = re.match(pattern, line_strip)
                if match:
                    current_counter.increment(level)
                    num = current_counter.get_numbering(level)
                    title_text = match.group(2).strip()
                    indent = "&nbsp;" * (level * 4)
                    toc.append(f"{indent}**{num}** {title_text}")
                    break
        return toc
    
    def to_latex(self, title, date, matrikel, text):
        latex = [
            r"\documentclass[12pt, a4paper, oneside]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm, right=6cm, top=2.5cm, bottom=3cm]{geometry}",
            r"\usepackage{setspace}",
            r"\usepackage{tocloft}",
            r"\onehalfspacing",
            r"\begin{document}",
            # Deckblatt Info
            fr"\noindent \textbf{{Klausur:}} {title} \hfill \textbf{{Datum:}} {date} \\",
            fr"\noindent \textbf{{Matrikel-Nr:}} {matrikel}",
            r"\vspace{1cm}",
            r"\tableofcontents",
            r"\newpage",
            r"\pagenumbering{arabic}"
        ]
        
        current_counter = HeadingCounter()
        lines = text.split('\n')
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append(r"\par\medskip")
                continue
            
            # Fußnoten-Ersetzung
            line_strip = re.sub(self.footnote_pattern, r"\\footnote{\1}", line_strip)
            
            # Überschriften-Logik
            matched = False
            for level, pattern in sorted(self.title_patterns.items()):
                match = re.match(pattern, line_strip)
                if match:
                    current_counter.increment(level)
                    num = current_counter.get_numbering(level)
                    title_text = match.group(2).strip()
                    # Mapping auf LaTeX Ebenen
                    if level == 1: cmd = "section"
                    elif level == 2: cmd = "subsection"
                    elif level == 3: cmd = "subsubsection"
                    else: cmd = "paragraph"
                    
                    latex.append(f"\\{cmd}*{{{num} {title_text}}}")
                    latex.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{{num} {title_text}}}")
                    matched = True
                    break
            
            if not matched:
                latex.append(line_strip)
                    
        latex.append(r"\end{document}")
        return "\n".join(latex)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. STREAMLIT UI (WEB-FRONTEND)
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="LexGerm Editor", layout="wide")

st.title("⚖️ LexGerm | iustWrite Editor")

with st.sidebar:
    st.header("📄 Klausurdaten")
    title = st.text_input("Titel", "Zivilrechtliche Klausur")
    date = st.text_input("Datum", datetime.now().strftime("%d.%m.%Y"))
    matrikel = st.text_input("Matrikel-Nr.")
    st.divider()
    st.header("📋 Gliederung")
    
col_edit, col_space = st.columns([3, 1])

# Editor
with col_edit:
    content = st.text_area("Gutachten (Nutze A* Titel für Überschriften, \\fn(Text) für Fußnoten)", height=600, key="editor_main")

# Sidebar Gliederung befüllen
doc = KlausurDocument()
toc_items = doc.generate_toc(content)
with st.sidebar:
    for item in toc_items:
        st.markdown(item, unsafe_allow_html=True)

# Export Prozess
if st.button("🚀 PDF generieren & herunterladen"):
    if content:
        with st.spinner("LaTeX-Server arbeitet..."):
            latex_code = doc.to_latex(title, date, matrikel, content)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                tex_file = os.path.join(tmpdir, "klausur.tex")
                with open(tex_file, "w", encoding="utf-8") as f:
                    f.write(latex_code)
                
                # Aufruf von pdflatex (Systembefehl in Streamlit Cloud)
                try:
                    subprocess.run(
                        ["pdflatex", "-interaction=nonstopmode", "klausur.tex"],
                        cwd=tmpdir, check=True, capture_output=True
                    )
                    
                    pdf_path = os.path.join(tmpdir, "klausur.pdf")
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ PDF Datei speichern",
                            data=f.read(),
                            file_name=f"Klausur_{title}.pdf",
                            mime="application/pdf"
                        )
                    st.success("Erfolgreich erstellt!")
                except subprocess.CalledProcessError as e:
                    st.error("LaTeX Fehler: Prüfe deine Eingabe auf Sonderzeichen.")
    else:
        st.warning("Bitte erst Text eingeben.")
