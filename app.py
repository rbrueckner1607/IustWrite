import streamlit as st
import os
import re
import shutil
import tempfile
import subprocess
from datetime import datetime

# ------------------------
# Hilfsfunktionen
# ------------------------
def get_asset_path(filename):
    """Finde Assets im jura_assets Ordner"""
    return os.path.join(os.getcwd(), "jura_assets", filename)

def run_pdflatex(tex_path, workdir):
    """pdflatex mit TEXINPUTS, damit jurabook.cls gefunden wird"""
    env = os.environ.copy()
    env["TEXINPUTS"] = f".:{os.path.join(workdir, 'jura_assets')}:"
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", tex_path],
        cwd=workdir,
        env=env,
        capture_output=True,
        check=True
    )
    
# ------------------------
# Heading Counter
# ------------------------
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
        def letter(n): return chr(96+n) if 1<=n<=26 else str(n)
        parts = []
        for i in range(level):
            n = self.counters[i]
            if n == 0: continue
            if i==0: parts.append(f"Teil {n}.")
            elif i==1: parts.append(chr(64+n)+".")
            elif i==2: parts.append(romans[n]+"." if n<len(romans) else str(n)+".")
            elif i==3: parts.append(f"{n}.")
            elif i==4: parts.append(f"{letter(n)})")
            elif i==5: parts.append(f"{letter(n)*2})")
            elif i==6: parts.append(f"({letter(n)})")
            elif i==7: parts.append(f"({letter(n)*2})")
            else: parts.append(str(n))
        return " ".join(parts)

# ------------------------
# KlausurDocument
# ------------------------
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

    def generate_toc(self, lines):
        toc = []
        for lineno, line in enumerate(lines):
            text = line.strip()
            if not text: continue
            found = False
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, text):
                    indent = (level-1)*2
                    toc.append((lineno, "  "*indent + text))
                    found = True
                    break
            if not found:
                for level, pattern in sorted(self.title_patterns.items()):
                    match = re.match(pattern, text)
                    if match:
                        title_text = match.group(2).strip()
                        indent = (level-1)*2
                        toc.append((lineno, "  "*indent + title_text))
                        break
        return toc

    def to_latex(self, title, date, matrikel, lines):
        latex = [
            r"\documentclass[12pt,a4paper]{jurabook}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm,right=6cm,top=2.5cm,bottom=3cm]{geometry}",
            r"\usepackage{fancyhdr}",
            r"\usepackage{tocloft}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            fr"\fancyhead[L]{{{title}}}",
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
            matched = False
            for level, pattern in self.title_patterns.items():
                m = re.match(pattern, line_strip)
                if m:
                    txt = m.group(2).strip()
                    if level==1: latex.append(r"\section*{" + txt + "}\n\addcontentsline{toc}{section}{" + txt + "}")
                    elif level==2: latex.append(r"\subsection*{" + txt + "}\n\addcontentsline{toc}{subsection}{" + txt + "}")
                    elif level==3: latex.append(r"\subsubsection*{" + txt + "}\n\addcontentsline{toc}{subsubsection}{" + txt + "}")
                    else: latex.append(r"\paragraph*{" + txt + "}\n\addcontentsline{toc}{subsubsection}{" + txt + "}")
                    matched = True
                    break
            if not matched:
                latex.append(line_strip)

        latex.append(r"\end{document}")
        return "\n".join(latex)

    def to_pdf_bytes(self, latex_content):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "klausur.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # Kopiere jura_assets
            assets_dir = os.path.join(tmpdir, "jura_assets")
            shutil.copytree("jura_assets", assets_dir)

            # pdflatex mit TEXINPUTS
            run_pdflatex("klausur.tex", tmpdir)
            run_pdflatex("klausur.tex", tmpdir)

            pdf_path = os.path.join(tmpdir, "klausur.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()
            raise FileNotFoundError("PDF nicht erstellt!")

# ------------------------
# Streamlit App
# ------------------------
st.set_page_config(page_title="iustWrite", layout="wide")
st.title("⚖️ iustWrite - Jura Klausur Editor")

# Sidebar
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", "Zivilrecht I - Klausur")
    date = st.date_input("Datum", datetime.now())
    matrikel = st.text_input("Matrikel-Nr.", "12345678")

    uploaded_file = st.file_uploader("📂 Klausur laden (.txt)")
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8")
        st.session_state.content = content

# Layout Split
col1, col2 = st.columns([1,3])
with col1:
    st.header("📋 Gliederung")
    if "toc" in st.session_state:
        for lineno, item in st.session_state.toc:
            if st.button(item, key=f"toc_{lineno}"):
                st.session_state.jump_line = lineno

with col2:
    st.header("✍️ Editor")
    content = st.text_area("Editor", value=st.session_state.get("content",""), height=650, key="editor")
    st.session_state.content = content

# TOC Update
doc = KlausurDocument()
lines = content.splitlines()
st.session_state.toc = doc.generate_toc(lines)

# PDF Export
if st.button("🎯 PDF Export"):
    latex = doc.to_latex(title, date.strftime("%d.%m.%Y"), matrikel, lines)
    pdf_bytes = doc.to_pdf_bytes(latex)
    st.download_button("⬇️ PDF Download", pdf_bytes, f"{title.replace(' ','_')}.pdf", "application/pdf")

# TXT Export
if st.button("💾 TXT speichern"):
    st.download_button("⬇️ TXT Download", content.encode("utf-8"), f"{title.replace(' ','_')}.txt", "text/plain")
