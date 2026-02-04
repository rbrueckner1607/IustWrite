import streamlit as st
import tempfile
import os
import subprocess
import shutil
import re
from datetime import datetime

# -----------------------------
# Hilfsklassen
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
        def letter(n): return chr(96 + n) if 1 <= n <= 26 else str(n)
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
                    toc.append((spaces + text, lineno))
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
                            toc.append((spaces + title_text, lineno))
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
        ]
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append("")
                continue
            title_match = False
            for level, pattern in self.title_patterns.items():
                match = re.match(pattern, line_strip)
                if match:
                    title_text = match.group(2).strip()
                    latex.extend([r"\section*{" + title_text + "}",
                                  r"\addcontentsline{toc}{section}{" + title_text + "}"])
                    title_match = True
                    break
            if not title_match:
                if re.search(self.footnote_pattern, line_strip):
                    match = re.search(self.footnote_pattern, line_strip)
                    footnote_text = match.group(1).strip()
                    clean_line = re.sub(self.footnote_pattern, '', line_strip).strip()
                    latex.append(clean_line + f"\\footnote{{{footnote_text}}}" if clean_line else f"\\footnote{{{footnote_text}}}")
                else:
                    latex.append(line_strip)
        latex.append(r"\end{document}")
        return "\n".join(latex)

    def to_pdf_bytes(self, latex_content):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "klausur.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)
            pdflatex_bin = shutil.which("pdflatex")
            if not pdflatex_bin: raise FileNotFoundError("pdflatex nicht im PATH!")
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)
            pdf_path = os.path.join(tmpdir, "klausur.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()
            raise FileNotFoundError("PDF nicht erstellt!")

# -----------------------------
# STREAMLIT APP
# -----------------------------
st.set_page_config(page_title="iustWrite | lexgerm.de", layout="wide")
st.title("⚖️ iustWrite - Jura Klausur Editor")

# Metadaten & Datei-Upload
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", "Zivilrecht I - Klausur")
    date = st.date_input("Datum")
    matrikel = st.text_input("Matrikel-Nr.", "12345678")
    uploaded_file = st.file_uploader("📂 .txt Datei laden", type=["txt", "klausur"])
    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        st.session_state["content"] = content
    elif "content" not in st.session_state:
        st.session_state["content"] = "Teil 1. Beispieltext\nA. Unterpunkt\nI. Subunterpunkt"

# Layout: Sidebar TOC + Editor
col1, col2 = st.columns([1,3])
doc = KlausurDocument()
lines = st.session_state["content"].splitlines()
toc = doc.generate_toc(lines)

with col1:
    st.header("📋 Gliederung")
    for item, lineno in toc:
        st.text(item)

with col2:
    st.header("✍️ Editor")
    content = st.text_area("Hier Text eingeben", value=st.session_state["content"], height=600, key="editor")
    st.session_state["content"] = content

# PDF Export
if st.button("🎯 PDF Export"):
    with st.spinner("Erstelle PDF..."):
        try:
            latex = doc.to_latex(title, date.strftime("%d.%m.%Y"), matrikel, st.session_state["content"].splitlines())
            pdf_bytes = doc.to_pdf_bytes(latex)
            st.download_button("⬇️ PDF Download", pdf_bytes, f"{title.replace(' ','_')}.pdf")
            st.success("✅ PDF erstellt!")
        except Exception as e:
            st.error(f"❌ LaTeX Fehler: {e}")

# TXT speichern
if st.button("💾 Speichern .txt"):
    with open(f"{title.replace(' ','_')}.txt", "w", encoding="utf-8") as f:
        f.write(st.session_state["content"])
    st.success("✅ Datei gespeichert!")
