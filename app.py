import streamlit as st
import tempfile
import os
import subprocess
import shutil
import re
from datetime import datetime

# -----------------------------
# HeadingCounter für Nummerierung
# -----------------------------
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
            if n == 0:
                continue
            if i == 0:
                parts.append(f"Teil {n}.")
            elif i == 1:
                parts.append(chr(64 + n) + ".")
            elif i == 2:
                parts.append(romans[n] + ".") if n < len(romans) else parts.append(str(n)+".")
            elif i == 3:
                parts.append(f"{n}.")
            elif i == 4:
                parts.append(f"{letter(n)})")
            elif i == 5:
                parts.append(f"{letter(n)*2})")
            elif i == 6:
                parts.append(f"({letter(n)})")
            elif i == 7:
                parts.append(f"({letter(n)*2})")
            else:
                parts.append(str(n))
        return " ".join([x for x in parts if x])

# -----------------------------
# KlausurDocument für Export
# -----------------------------
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
        self.footnote_pattern = r'\\fn\(([^)]*)\)'

    # TOC-Generator
    def generate_toc(self, lines):
        toc = []
        for lineno, line in enumerate(lines):
            text = line.strip()
            if not text:
                continue
            level = None
            title_text = None
            for l, pattern in self.prefix_patterns.items():
                if re.match(pattern, text):
                    level = l
                    title_text = text
                    break
            if not level:
                for l, pattern in self.title_patterns.items():
                    match = re.match(pattern, text)
                    if match:
                        level = l
                        title_text = match.group(2).strip()
                        break
            if level and title_text:
                indent = (level - 1) * 2
                toc.append("  " * indent + title_text)
        return toc

    # LaTeX-Header für jede Ebene
    def latex_header(self, level, text):
        if level == 1:
            return r"\section*{" + text + "}", r"\addcontentsline{toc}{section}{" + text + "}"
        elif level == 2:
            return r"\subsection*{" + text + "}", r"\addcontentsline{toc}{subsection}{" + text + "}"
        elif level == 3:
            return r"\subsubsection*{" + text + "}", r"\addcontentsline{toc}{subsubsection}{" + text + "}"
        elif level == 4:
            return r"\paragraph*{" + text + "}", r"\addcontentsline{toc}{paragraph}{" + text + "}"
        elif level == 5:
            return r"\subparagraph*{" + text + "}", r"\addcontentsline{toc}{subparagraph}{" + text + "}"
        else:
            return r"\subparagraph*{\textit{" + text + "}}", r"\addcontentsline{toc}{subparagraph}{" + text + "}"

    # Export nach LaTeX
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
            r"\fancyhead[L]{" + title + "}",
            r"\fancyfoot[R]{\thepage}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\begin{document}",
            r"\tableofcontents",
            r"\clearpage",
            fr"\section*{{{title} ({date})}}",
        ]
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append("")
                continue
            level = None
            title_text = None
            for l, pattern in self.prefix_patterns.items():
                if re.match(pattern, line_strip):
                    level = l
                    title_text = line_strip
                    break
            if not level:
                for l, pattern in self.title_patterns.items():
                    match = re.match(pattern, line_strip)
                    if match:
                        level = l
                        title_text = match.group(2).strip()
                        break
            if level and title_text:
                # Fußnoten prüfen
                fn_match = re.search(self.footnote_pattern, title_text)
                if fn_match:
                    fn_text = fn_match.group(1)
                    title_text = re.sub(self.footnote_pattern, '', title_text).strip()
                    if title_text:
                        title_text += f"\\footnote{{{fn_text}}}"
                    else:
                        title_text = f"\\footnote{{{fn_text}}}"
                cmd, toc = self.latex_header(level, title_text)
                latex.append(cmd)
                latex.append(toc)
            else:
                latex.append(line_strip)
        latex.append(r"\end{document}")
        return "\n".join(latex)

    # PDF Bytes erzeugen
    def to_pdf_bytes(self, latex_content):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "klausur.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)
            pdflatex_bin = shutil.which("pdflatex")
            if not pdflatex_bin:
                raise FileNotFoundError("pdflatex nicht im PATH")
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)
            pdf_path = os.path.join(tmpdir, "klausur.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()
            raise FileNotFoundError("PDF nicht erstellt")

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="iustWrite | lexgerm.de", layout="wide")

st.title("⚖️ iustWrite - Jura Klausur Editor")
st.markdown("***Automatische Nummerierung • Live-Gliederung • PDF-Export***")

# Sidebar
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", value="Zivilrecht I - Klausur")
    date = st.date_input("Datum", value=datetime.now())
    matrikel = st.text_input("Matrikel-Nr.", value="12345678")
    st.markdown("---")

# Layout: Split-Screen
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
    content = st.text_area("", value=st.session_state.get("content", default_content),
                           height=650, key="editor")

# TOC live aktualisieren
doc = KlausurDocument()
if content != st.session_state.get("last_content", ""):
    st.session_state.toc = doc.generate_toc(content.splitlines())
    st.session_state.last_content = content
    st.session_state.content = content
    st.experimental_rerun()

# Status
if content.strip():
    st.markdown(f"**Status**: {len(content):,} Zeichen")

# Buttons
col1b, col2b, col3b = st.columns(3)
with col1b:
    if st.button("🎯 PDF Export"):
        with st.spinner("Erstelle PDF..."):
            try:
                latex = doc.to_latex(title, date.strftime("%d.%m.%Y"), matrikel, content.splitlines())
                pdf_bytes = doc.to_pdf_bytes(latex)
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_name = f"{title.replace(' ', '_')}.pdf"
                st.success("✅ PDF bereit!")
            except Exception as e:
                st.error(f"❌ {str(e)}")
with col2b:
    if st.button("💾 Speichern"):
        with open(f"{title.replace(' ','_')}.txt", "w", encoding="utf-8") as f:
            f.write(content)
        st.success("✅ Datei gespeichert")
with col3b:
    uploaded_file = st.file_uploader("📂 Laden", type=["txt"])
    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        st.session_state.content = content
        st.experimental_rerun()

# PDF Download
if 'pdf_bytes' in st.session_state:
    st.download_button("⬇️ PDF Download", st.session_state.pdf_bytes, 
                       st.session_state.pdf_name, "application/pdf")
