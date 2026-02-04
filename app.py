import streamlit as st
import tempfile
import os
import subprocess
import shutil
import re
from datetime import datetime

# 1. HEADINGCOUNTER (1:1 aus deiner Vorlage)
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

# 2. KLAUSURDOCUMENT
class KlausurDocument:
    def __init__(self):
        self.heading_counter = HeadingCounter()
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',   
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)(\s|$)',
            6: r'^\s*[a-z]{2}\)(\s|$)',
            7: r'^\s*\([a-z]\)(\s|$)',
            8: r'^\s*\([a-z]{2}\)(\s|$)'
        }
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
        self.footnote_pattern = r'\\fn\((.*?)\)'
        
    def generate_toc(self, lines):
        toc = []
        for line in lines:
            text = line.strip()
            if not text: continue
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, text):
                    indent = "&nbsp;" * (level * 4)
                    toc.append(f"{indent}{text}")
                    break
            for level, pattern in sorted(self.title_patterns.items()):
                match = re.match(pattern, text)
                if match:
                    title_text = match.group(2).strip()
                    indent = "&nbsp;" * (level * 4)
                    toc.append(f"{indent}**{title_text}**")
                    break
        return toc
    
    def to_latex(self, title, date, matrikel, lines):
        latex = [
            r"\documentclass[12pt,a4paper]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm,right=6cm,top=2.5cm,bottom=3cm]{geometry}",
            r"\usepackage{fancyhdr}",
            r"\usepackage{tocloft}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            r"\fancyfoot[R]{\thepage}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\begin{document}",
            r"\enlargethispage{40pt}",
            r"\pagenumbering{gobble}",
            r"\vspace*{-3cm}",
            r"\tableofcontents",
            r"\clearpage",
            r"\pagenumbering{arabic}",
            fr"\section*{{{title} ({date})}}",
            fr"\noindent Matrikel-Nr.: {matrikel} \vspace{{1cm}}"
        ]
        
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append(r"\par\medskip")
                continue
            
            # Fußnoten-Ersetzung
            line_strip = re.sub(self.footnote_pattern, r"\\footnote{\1}", line_strip)
            
            title_match = False
            for level, pattern in self.title_patterns.items():
                match = re.match(pattern, line_strip)
                if match:
                    title_text = match.group(2).strip()
                    cmd = "section" if level == 1 else "subsection" if level == 2 else "subsubsection" if level == 3 else "paragraph"
                    latex.extend([f"\\{cmd}*{{{title_text}}}", f"\\addcontentsline{{toc}}{{{cmd}}}{{{title_text}}}"])
                    title_match = True
                    break
            
            if not title_match:
                # Prüfe auf Standard-Präfixe ohne Sternchen
                found_prefix = False
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_strip):
                        cmd = "section" if level == 1 else "subsection" if level == 2 else "subsubsection" if level == 3 else "paragraph"
                        latex.extend([f"\\{cmd}*{{{line_strip}}}", f"\\addcontentsline{{toc}}{{{cmd}}}{{{line_strip}}}"])
                        found_prefix = True
                        break
                if not found_prefix:
                    latex.append(line_strip)
                    
        latex.append(r"\end{document}")
        return "\n".join(latex)

# 3. STREAMLIT APP UI
st.set_page_config(page_title="iustWrite | lexgerm.de", page_icon="⚖️", layout="wide")

# CSS für Jura-Optik
st.markdown("""<style> .stTextArea textarea { font-family: 'Times New Roman', serif; font-size: 16px; } </style>""", unsafe_allow_html=True)

st.title("⚖️ iustWrite - Jura Klausur Editor")

with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", value="Zivilrechtliche Klausur")
    date = st.text_input("Datum", value=datetime.now().strftime("%d.%m.%Y"))
    matrikel = st.text_input("Matrikel-Nr.")
    st.divider()
    st.header("📋 Live-Gliederung")
    gliederung_area = st.empty()

col_edit, _ = st.columns([4, 1])
with col_edit:
    content = st.text_area("Schreibe hier dein Gutachten...", height=600, key="editor_input")

# Parser für Sidebar
doc = KlausurDocument()
lines = content.split('\n')
toc = doc.generate_toc(lines)
with st.sidebar:
    for item in toc:
        st.markdown(item, unsafe_allow_html=True)

if st.button("🚀 PDF exportieren"):
    if content:
        with st.spinner("PDF wird generiert (2 Durchläufe für Gliederung)..."):
            latex_code = doc.to_latex(title, date, matrikel, lines)
            with tempfile.TemporaryDirectory() as tmpdir:
                tex_path = os.path.join(tmpdir, "klausur.tex")
                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(latex_code)
                
                pdflatex_bin = shutil.which("pdflatex")
                if pdflatex_bin:
                    try:
                        # 2x Kompilieren für Inhaltsverzeichnis
                        subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdir, check=True, capture_output=True)
                        subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdir, check=True, capture_output=True)
                        
                        pdf_path = os.path.join(tmpdir, "klausur.pdf")
                        with open(pdf_path, "rb") as f:
                            st.download_button("⬇️ PDF herunterladen", f, file_name=f"{title}.pdf", mime="application/pdf")
                        st.success("Erfolgreich erstellt!")
                    except Exception as e:
                        st.error(f"Fehler: {e}")
    else:
        st.warning("Bitte erst Text eingeben.")
