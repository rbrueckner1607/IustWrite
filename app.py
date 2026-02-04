import streamlit as st
import tempfile
import os
import subprocess
import re
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DIE ORIGINALE JURA-LOGIK (HeadingCounter & Document-Parser)
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
        romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", 
                  "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
        def letter(n): return chr(96 + n) if 1 <= n <= 26 else str(n)
        parts = []
        for i in range(level):
            n = self.counters[i]
            if n == 0: continue
            if i == 0: parts.append(f"Teil {n}.")
            elif i == 1: parts.append(chr(64 + n) + ".")
            elif i == 2: parts.append(romans[n] + "." if n < len(romans) else str(n) + ".")
            elif i == 3: parts.append(f"{n}.")
            elif i == 4: parts.append(f"{letter(n)})")
            elif i == 5: parts.append(f"{letter(n)*2})")
            elif i == 6: parts.append(f"({letter(n)})")
            elif i == 7: parts.append(f"({letter(n)*2})")
            else: parts.append(str(n))
        return " ".join([x for x in parts if x])

class KlausurDocument:
    def __init__(self):
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

    def process_text(self, text):
        """Verarbeitet den Text und erkennt die Gliederungspunkte."""
        lines = text.split('\n')
        processed_elements = []
        counter = HeadingCounter()
        
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                processed_elements.append({"type": "text", "content": ""})
                continue
            
            matched = False
            for level, pattern in sorted(self.title_patterns.items()):
                match = re.match(pattern, line_strip)
                if match:
                    counter.increment(level)
                    num = counter.get_numbering(level)
                    title_text = match.group(2).strip()
                    processed_elements.append({
                        "type": "heading", 
                        "level": level, 
                        "number": num, 
                        "title": title_text
                    })
                    matched = True
                    break
            
            if not matched:
                # Fußnoten ersetzen \fn(text) -> \footnote{text}
                clean_line = re.sub(self.footnote_pattern, r"\\footnote{\1}", line_strip)
                processed_elements.append({"type": "text", "content": clean_line})
        
        return processed_elements

# ═══════════════════════════════════════════════════════════════════════════════
# 2. STREAMLIT FRONTEND (INTERFACE)
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="IustWrite | lexgerm.de", layout="wide")

st.title("⚖️ LexGerm | iustWrite Editor")
st.markdown("Nutze `A*`, `I*`, `1*` etc. am Zeilenanfang für die Gliederung.")

# Sidebar für Metadaten
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", "Übungsklausur")
    date = st.text_input("Datum", datetime.now().strftime("%d.%m.%Y"))
    matrikel = st.text_input("Matrikel-Nr.")
    st.divider()
    st.header("📋 Gliederungsvorschau")

# Zwei Spalten Layout
col_edit, col_empty = st.columns([3, 1])

with col_edit:
    content = st.text_area("Klausurtext", height=600, key="editor")

# Logik ausführen
doc = KlausurDocument()
elements = doc.process_text(content)

# Gliederung in Sidebar anzeigen (identisch zur Logik)
with st.sidebar:
    for el in elements:
        if el["type"] == "heading":
            indent = "&nbsp;" * (el["level"] * 4)
            st.markdown(f"{indent}**{el['number']}** {el['title']}", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. PDF EXPORT (LATEX GENERIERUNG)
# ═══════════════════════════════════════════════════════════════════════════════

if st.button("🚀 PDF generieren"):
    if content:
        latex = [
            r"\documentclass[12pt, a4paper]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2.5cm, right=6cm, top=2.5cm, bottom=3cm]{geometry}",
            r"\usepackage{setspace}",
            r"\usepackage{tocloft}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\onehalfspacing",
            r"\begin{document}",
            fr"\noindent \textbf{{{title}}} \hfill {date}\\",
            fr"\noindent Matrikel-Nr.: {matrikel} \vspace{{1cm}} \\",
            r"\tableofcontents \newpage \pagenumbering{arabic}"
        ]

        for el in elements:
            if el["type"] == "heading":
                # LaTeX Befehle zuweisen
                if el["level"] == 1: cmd = "section"
                elif el["level"] == 2: cmd = "subsection"
                elif el["level"] == 3: cmd = "subsubsection"
                else: cmd = "paragraph"
                
                # WICHTIG: Die berechnete Nummer wird als Titel übergeben
                latex.append(f"\\{cmd}*{{{el['number']} {el['title']}}}")
                latex.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{{el['number']} {el['title']}}}")
            else:
                latex.append(el["content"])

        latex.append(r"\end{document}")
        latex_final = "\n".join(latex)

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "klausur.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_final)
            
            try:
                subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdir, check=True)
                with open(os.path.join(tmpdir, "klausur.pdf"), "rb") as f:
                    st.download_button("⬇️ PDF Download", f, file_name=f"{title}.pdf")
            except:
                st.error("LaTeX Fehler. Prüfe die Formatierung!")
