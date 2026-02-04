import streamlit as st
import tempfile
import os
import subprocess
import re
from datetime import datetime

# 1. HEADINGCOUNTER (1:1 aus PyQt)
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

# 2. KLAUSURDOCUMENT (GUI-unabhängige Logik)
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
        self.footnote_pattern = r'\\fn\([^)]*\)'
        
    def clean_text(self, text):
        for pattern in self.prefix_patterns.values():
            text = re.sub(pattern, '', text, count=1).strip()
        for pattern in self.title_patterns.values():
            text = re.sub(pattern, '', text, count=1).strip()
        return text
    
    def generate_toc(self, lines):
        toc = []
        for lineno, line in enumerate(lines):
            text = line.strip()
            if not text: continue
                
            found_normal = False
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, text):
                    indent = (level - 1) * 2
                    spaces = "  " * indent
                    toc.append(f"{spaces}{text}")
                    found_normal = True
                    break
            
            if not found_normal:
                for level, pattern in sorted(self.title_patterns.items()):
                    match = re.match(pattern, text)
                    if match:
                        title_text = match.group(2).strip()
                        if title_text:
                            indent = (level - 1) * 2
                            spaces = "  " * indent
                            toc.append(f"{spaces}{title_text}")
                            break
        return toc
    
    def to_latex(self, title, date, matrikel, lines):
        latex = []
        
        # Präambel (Streamlit-kompatibel)
        preamble = [
            r"\documentclass[12pt,a4paper]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm,right=6cm,top=2.5cm,bottom=3cm]{geometry}",
            r"\usepackage{fancyhdr}",
            r"\usepackage{titlesec}",
            r"\usepackage{tocloft}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            r"\fancyfoot[R]{\thepage}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\setcounter{tocdepth}{4}",
            r"\setlength{\cftbeforesecskip}{2pt}",
            r"\setlength{\cftbeforesubsecskip}{2pt}"
        ]
        latex.extend(preamble)
        latex.append(r"\begin{document}")
        
        latex.extend([
            r"\enlargethispage{40pt}",
            r"\pagenumbering{gobble}",
            r"\vspace*{-3cm}",
            r"\tableofcontents",
            r"\clearpage",
            r"\pagenumbering{arabic}",
            fr"\section*{{{title} ({date})}}",
            ""
        ])
        
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append("")
                continue
            latex.append("")
            
            # Title-Patterns
            title_match = False
            for level, pattern in self.title_patterns.items():
                match = re.match(pattern, line_strip)
                if match:
                    title_text = match.group(2).strip()
                    if level == 1:
                        latex.extend([r"\section*{" + title_text + "}",
                                    r"\addcontentsline{toc}{section}{" + title_text + "}"])
                    elif level == 2:
                        latex.extend([r"\subsection*{" + title_text + "}",
                                    r"\addcontentsline{toc}{subsection}{" + title_text + "}"])
                    title_match = True
                    break
            
            if not title_match:
                # Normale Patterns
                if re.match(self.prefix_patterns[1], line_strip):
                    latex.extend([r"\section*{" + line_strip + "}",
                                r"\addcontentsline{toc}{section}{" + line_strip + "}"])
                elif re.match(self.prefix_patterns[2], line_strip):
                    latex.extend([r"\subsection*{" + line_strip + "}",
                                r"\addcontentsline{toc}{subsection}{" + line_strip + "}"])
                elif re.match(self.prefix_patterns[3], line_strip):
                    latex.extend([r"\subsubsection*{" + line_strip + "}",
                                r"\addcontentsline{toc}{subsubsection}{" + line_strip + "}"])
                elif re.search(self.footnote_pattern, line_strip):
                    match = re.search(self.footnote_pattern, line_strip)
                    if match:
                        footnote_text = match.group(1).strip()
                        clean_line = re.sub(self.footnote_pattern, '', line_strip).strip()
                        if clean_line:
                            latex.append(clean_line + f"\\footnote{{{footnote_text}}}")
                        else:
                            latex.append(f"\\footnote{{{footnote_text}}}")
                else:
                    latex.append(line_strip)
                    
        latex.append(r"\end{document}")
        return "\n".join(latex)
    
    def to_pdf_bytes(self, latex_content):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "klausur.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)
            
            # pdflatex direkt finden (Streamlit Cloud hat es!)
            pdflatex_bin = shutil.which("pdflatex")
            if not pdflatex_bin:
                # Fallback: PATH durchsuchen
                for path in os.environ["PATH"].split(os.pathsep):
                    pdflatex_candidate = os.path.join(path, "pdflatex")
                    if os.path.isfile(pdflatex_candidate):
                        pdflatex_bin = pdflatex_candidate
                        break
            
            if not pdflatex_bin:
                raise FileNotFoundError("pdflatex nicht gefunden!")
            
            # Zweimal kompilieren (für TOC)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"], 
                         cwd=tmpdir, capture_output=True, check=True)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"], 
                         cwd=tmpdir, capture_output=True, check=True)
            
            pdf_path = os.path.join(tmpdir, "klausur.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()
            raise FileNotFoundError("PDF Generation failed!")

# Streamlit App (identisch wie vorher)
st.set_page_config(page_title="iustWrite | lexgerm.de", page_icon="⚖️", layout="wide")

st.title("⚖️ iustWrite - Jura Klausur Editor")
st.markdown("***Automatische Nummerierung • Live-Gliederung • PDF-Export***")

# Sidebar
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", value="Zivilrecht I - Klausur")
    date = st.date_input("Datum", value=datetime.now())
    matrikel = st.text_input("Matrikel-Nr.", value="12345678")
    
    if st.button("🆕 Neue Klausur"):
        st.session_state.clear()
        st.rerun()

col1, col2 = st.columns([1, 3])

with col1:
    st.header("📋 Gliederung")
    toc = st.session_state.get("toc", [])
    for item in toc:
        st.write(item)

with col2:
    st.header("✍️ Editor")
    default_content = """Teil 1. Zulässigkeit

A. Formelle Voraussetzungen

I. Antragsbegründung"""
    content = st.text_area("", value=st.session_state.get('content', default_content), height=650, key="editor")

# Live TOC
if content != st.session_state.get('last_content', ''):
    doc = KlausurDocument()
    st.session_state.toc = doc.generate_toc(content.splitlines())
    st.session_state.last_content = content
    st.rerun()

# Buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("🎯 PDF Export"):
        with st.spinner("Erstelle PDF..."):
            try:
                doc = KlausurDocument()
                lines = content.splitlines()
                latex = doc.to_latex(title, date.strftime("%d.%m.%Y"), matrikel, lines)
                pdf_bytes = doc.to_pdf_bytes(latex)
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_name = f"{title}.pdf"
                st.success("✅ PDF bereit!")
                st.rerun()
            except Exception as e:
                st.error(f"PDF Fehler: {str(e)}")

if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF Download", st.session_state.pdf_bytes, st.session_state.pdf_name, "application/pdf")
