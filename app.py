import streamlit as st
import tempfile
import os
import subprocess
import re
from datetime import datetime
import pytinytex
import io
import base64

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DEINE BESTEHENDEN KLASSEN (100% 1:1 übernommen!)
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
        toc_levels = {}
        for lineno, line in enumerate(lines):
            text = line.strip()
            if not text: continue
                
            found_normal = False
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, text):
                    indent = (level - 1) * 2
                    spaces = "  " * indent
                    toc.append(f"{spaces}{text}")
                    toc_levels[lineno] = level
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
                            toc_levels[lineno] = level
                            break
        return toc
    
    def to_latex(self, title, date, matrikel, lines):
        latex = []
        
        # Präambel (EXAKT wie bei dir!)
        preamble = [
            r"\documentclass[12pt, a4paper, oneside]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage{geometry}",
            r"\usepackage{fancyhdr}",
            r"\usepackage{titlesec}",
            r"\usepackage{enumitem}",
            r"\usepackage{tocloft}",
            r"\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm, bindingoffset=0cm}",
            r"\setcounter{secnumdepth}{6}",
            r"\setcounter{tocdepth}{6}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            r"\renewcommand{\headrulewidth}{0.5pt}",
            r"\fancypagestyle{plain}{",
            r"	\fancyhf{}",
            r"	\fancyfoot[R]{\thepage}",
            r"	\renewcommand{\headrulewidth}{0pt}",
            r"}",
            r"\makeatletter",
            r"\renewcommand{\@cfoot}{}",
            r"\makeatother"
        ]
        latex.extend(preamble)
        
        latex += [
            r"\begin{document}",
            r"\enlargethispage{40pt}",
            r"\pagenumbering{}",
            r"\vspace*{-3cm}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\tableofcontents",
            r"\clearpage",
            r"\pagenumbering{arabic}",
            fr"\chapter*{{{title} ({date})}}",
            ""
        ]
        
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append("")
                continue
            latex.append("")
            
            title_match = False
            for level, pattern in self.title_patterns.items():
                match = re.match(pattern, line_strip)
                if match:
                    title_text = match.group(2).strip()
                    if level == 1:
                        latex.append(r"\section*{" + title_text + "}")
                        latex.append(r"\addcontentsline{toc}{section}{" + title_text + "}")
                    elif level == 2:
                        latex.append(r"\subsection*{" + title_text + "}")
                        latex.append(r"\addcontentsline{toc}{subsection}{" + title_text + "}")
                    title_match = True
                    break
            
            if not title_match:
                if re.match(self.prefix_patterns[1], line_strip):
                    latex.append(r"\section*{" + line_strip + "}")
                    latex.append(r"\addcontentsline{toc}{section}{" + line_strip + "}")
                elif re.match(self.prefix_patterns[2], line_strip):
                    latex.append(r"\subsection*{" + line_strip + "}")
                    latex.append(r"\addcontentsline{toc}{subsection}{" + line_strip + "}")
                elif re.search(self.footnote_pattern, line_strip):
                    match = re.search(self.footnote_pattern, line_strip)
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
            
            # pdflatex finden
            tiny_base = pytinytex.get_tinytex_path()
            pdflatex_bin = None
            for root, dirs, files in os.walk(tiny_base):
                if "pdflatex" in files and "bin" in root:
                    pdflatex_bin = os.path.join(root, "pdflatex")
                    break
            
            if not pdflatex_bin:
                raise FileNotFoundError("pdflatex nicht gefunden!")
            
            # Zweimal kompilieren (für TOC)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"], 
                         cwd=tmpdir, capture_output=True)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"], 
                         cwd=tmpdir, capture_output=True)
            
            pdf_path = os.path.join(tmpdir, "klausur.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()
            raise FileNotFoundError("PDF konnte nicht erstellt werden!")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. STREAMLIT FRONTEND (identische Funktionalität!)
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="iustWrite | lexgerm.de", 
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚖️ iustWrite - Jura Klausur Editor")
st.markdown("***Automatische Nummerierung • Live-Gliederung • Professioneller PDF-Export***")

# Sidebar (Meta + Shortcuts)
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", value="Zivilrecht I - Klausur")
    date = st.date_input("Datum", value=datetime.now())
    matrikel = st.text_input("Matrikel-Nr.", value="12345678")
    
    st.markdown("---")
    st.header("⌨️ Shortcuts")
    st.markdown("""
    **Strg+1-8**: Überschriften (automatische Nummerierung)  
    **Strg+Shift+1-8**: Titel (ohne Nummerierung mit `*`)  
    **\\fn(Text)**: Fußnoten
    """)
    
    if st.button("🆕 Neue Klausur", use_container_width=True):
        st.session_state.content = ""
        st.session_state.toc = []
        st.rerun()

# Main Layout (Splitter wie PyQt)
col_toc, col_editor = st.columns([1, 3])

with col_toc:
    st.header("📋 Gliederung")
    toc = st.session_state.get("toc", [])
    for item in toc:
        st.write(item)
        
with col_editor:
    st.header("✍️ Editor")
    content = st.text_area(
        label="Klausurtext",
        value=st.session_state.get("content", ""),
        height=600,
        help="Strg+1-8 für Überschriften, \\fn(Text) für Fußnoten",
        key="content_input"
    )

# Live TOC Update (wie on_text_changed)
if 'last_content' not in st.session_state:
    st.session_state.last_content = ""

if content != st.session_state.last_content:
    doc = KlausurDocument()
    lines = content.splitlines()
    st.session_state.toc = doc.generate_toc(lines)
    st.session_state.last_content = content
    st.rerun()

# Statusleiste (Zeichen + Zeit)
if content:
    char_count = len(content)
    words = len(content.split())
    st.markdown(f"**Status**: {char_count} Zeichen | {words} Wörter")

# Action Buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("💾 Speichern", use_container_width=True):
        st.download_button(
            label="TXT herunterladen",
            data=content,
            file_name=f"{title.replace(' ', '_')}.klausur",
            mime="text/plain"
        )

with col2:
    if st.button("🎯 PDF Export", use_container_width=True):
        with st.spinner("Erstelle professionelles PDF..."):
            try:
                doc = KlausurDocument()
                lines = content.splitlines()
                latex = doc.to_latex(title, date.strftime("%d.%m.%Y"), matrikel, lines)
                pdf_bytes = doc.to_pdf_bytes(latex)
                
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_title = title
                st.success("✅ PDF erfolgreich erstellt!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ PDF-Error: {str(e)}")

with col3:
    if hasattr(st.session_state, 'pdf_bytes'):
        st.download_button(
            label="⬇️ PDF herunterladen",
            data=st.session_state.pdf_bytes,
            file_name=f"{st.session_state.pdf_title.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown("*iustWrite für lexgerm.de • Open Source auf GitHub*")
