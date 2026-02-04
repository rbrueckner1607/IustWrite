# iustwrite_streamlit.py
import streamlit as st
import re
import os
import subprocess
import tempfile
from io import BytesIO

st.set_page_config(page_title="iustWrite Web Editor", layout="wide")

# -----------------------------
# Hilfsfunktionen
# -----------------------------

def extract_headings(text):
    """Scannt Text und findet Überschriften für die Sidebar"""
    headings = []
    lines = text.splitlines()
    prefix_patterns = {
        1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
        2: r'^\s*[A-H]\.(\s|$)',
        3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\.(\s|$)',
        4: r'^\s*\d+\.(\s|$)',
        5: r'^\s*[a-z]\)(\s|$)',
        6: r'^\s*[a-z]{2}\)(\s|$)',
        7: r'^\s*\([a-z]\)(\s|$)',
        8: r'^\s*\([a-z]{2}\)(\s|$)',
    }
    for lineno, line in enumerate(lines):
        line_strip = line.strip()
        if not line_strip:
            continue
        for level, pattern in prefix_patterns.items():
            if re.match(pattern, line_strip):
                headings.append({"level": level, "text": line_strip, "lineno": lineno})
                break
    return headings

def generate_latex(title, date, matrikel, text):
    """Erzeugt LaTeX-Dokument als String"""
    latex = [
        r"\documentclass[12pt,a4paper,oneside]{article}",
        r"\usepackage[ngerman]{babel}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{lmodern}",
        r"\usepackage{geometry}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{titlesec}",
        r"\usepackage{tocloft}",
        r"\geometry{left=2cm,right=2cm,top=2.5cm,bottom=3cm}",
        r"\setcounter{secnumdepth}{6}",
        r"\setcounter{tocdepth}{6}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\renewcommand{\headrulewidth}{0.5pt}",
        r"\begin{document}",
        fr"\chapter*{{{title} ({date})}}",
        r"\tableofcontents",
        r"\clearpage"
    ]
    lines = text.splitlines()
    prefix_patterns = {
        1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
        2: r'^\s*[A-H]\.(\s|$)',
        3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\.(\s|$)',
        4: r'^\s*\d+\.(\s|$)',
        5: r'^\s*[a-z]\)(\s|$)',
        6: r'^\s*[a-z]{2}\)(\s|$)',
        7: r'^\s*\([a-z]\)(\s|$)',
        8: r'^\s*\([a-z]{2}\)(\s|$)',
    }
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            latex.append("")
            continue
        matched = False
        for level, pattern in prefix_patterns.items():
            if re.match(pattern, line_strip):
                if level == 1:
                    latex.append(r"\section*{" + line_strip + "}")
                    latex.append(r"\addcontentsline{toc}{section}{" + line_strip + "}")
                elif level == 2:
                    latex.append(r"\subsection*{" + line_strip + "}")
                    latex.append(r"\addcontentsline{toc}{subsection}{" + line_strip + "}")
                elif level == 3:
                    latex.append(r"\subsubsection*{" + line_strip + "}")
                    latex.append(r"\addcontentsline{toc}{subsubsection}{" + line_strip + "}")
                else:
                    latex.append(r"\paragraph*{" + line_strip + "}")
                    latex.append(r"\addcontentsline{toc}{subsection}{" + line_strip + "}")
                matched = True
                break
        if not matched:
            latex.append(line_strip)
    latex.append(r"\end{document}")
    return "\n".join(latex)

def build_pdf(latex_string):
    """Erzeugt PDF Bytes via Tectonic"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "doc.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_string)
        # Tectonic aufrufen
        result = subprocess.run(["tectonic", tex_path, "--outdir", tmpdir],
                                capture_output=True)
        pdf_path = os.path.join(tmpdir, "doc.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            return pdf_bytes
        else:
            st.error("PDF-Erstellung fehlgeschlagen!")
            st.text(result.stderr.decode())
            return None

# -----------------------------
# Streamlit UI
# -----------------------------

st.title("iustWrite Web Editor")

with st.sidebar:
    st.header("Metadaten")
    title = st.text_input("Titel", "Meine Klausur")
    date = st.text_input("Datum", "01.01.2026")
    matrikel = st.text_input("Matrikelnummer", "123456")
    st.markdown("---")
    st.header("Gliederung")
    toc_placeholder = st.empty()

text = st.text_area("Klausurinhalt", height=500)

# Sidebar TOC aktualisieren
headings = extract_headings(text)
toc_text = ""
for h in headings:
    indent = (h["level"] - 1) * 10
    toc_text += f"{' ' * indent}- {h['text']}\n"
toc_placeholder.text(toc_text)

if st.button("PDF exportieren"):
    latex_str = generate_latex(title, date, matrikel, text)
    pdf_bytes = build_pdf(latex_str)
    if pdf_bytes:
        st.download_button("Download PDF", data=pdf_bytes, file_name=f"{title}.pdf", mime="application/pdf")
