import streamlit as st
import tempfile
import os
import subprocess
import shutil
import re
from datetime import datetime

# ============================================================
# PARSER / DOKUMENT
# ============================================================

class KlausurDocument:
    def __init__(self):
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

    # --------------------------------------------------------

    def parse_structure(self, lines):
        entries = []
        for idx, line in enumerate(lines):
            text = line.rstrip()
            if not text:
                continue

            for level, pat in self.title_patterns.items():
                m = re.match(pat, text)
                if m:
                    entries.append({
                        "level": level,
                        "title": m.group(2).strip(),
                        "line": idx
                    })
                    break
            else:
                for level, pat in self.prefix_patterns.items():
                    if re.match(pat, text):
                        entries.append({
                            "level": level,
                            "title": text.strip(),
                            "line": idx
                        })
                        break
        return entries

    # --------------------------------------------------------

    def to_latex(self, title, date, matrikel, lines):
        latex = [
            r"\documentclass[12pt,a4paper]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm,right=6cm,top=2.5cm,bottom=3cm]{geometry}",
            r"\usepackage{fancyhdr}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            fr"\fancyhead[L]{{{title}}}",
            r"\fancyfoot[R]{\thepage}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\begin{document}",
            r"\pagenumbering{gobble}",
            r"\tableofcontents",
            r"\clearpage",
            r"\pagenumbering{arabic}",
        ]

        for line in lines:
            ls = line.strip()
            if not ls:
                latex.append("")
                continue

            handled = False
            for level, pat in self.title_patterns.items():
                m = re.match(pat, ls)
                if m:
                    t = m.group(2)
                    cmd = "section" if level == 1 else "subsection"
                    latex.append(fr"\{cmd}*{{{t}}}")
                    latex.append(fr"\addcontentsline{{toc}}{{{cmd}}}{{{t}}}")
                    handled = True
                    break

            if handled:
                continue

            if re.search(self.footnote_pattern, ls):
                fn = re.search(self.footnote_pattern, ls)
                text = re.sub(self.footnote_pattern, "", ls)
                latex.append(f"{text}\\footnote{{{fn.group(1)}}}")
            else:
                latex.append(ls)

        latex.append(r"\end{document}")
        return "\n".join(latex)

    # --------------------------------------------------------

    def to_pdf_bytes(self, latex):
        with tempfile.TemporaryDirectory() as tmp:
            tex = os.path.join(tmp, "doc.tex")
            with open(tex, "w", encoding="utf-8") as f:
                f.write(latex)

            pdflatex = shutil.which("pdflatex")
            if not pdflatex:
                raise RuntimeError("pdflatex nicht gefunden")

            subprocess.run([pdflatex, "doc.tex"], cwd=tmp, capture_output=True)
            subprocess.run([pdflatex, "doc.tex"], cwd=tmp, capture_output=True)

            with open(os.path.join(tmp, "doc.pdf"), "rb") as f:
                return f.read()

# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(layout="wide", page_title="iustWrite")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", "Zivilrecht I – Klausur")
    date = st.date_input("Datum", datetime.now())
    matrikel = st.text_input("Matrikel", "12345678")

    st.divider()

    uploaded = st.file_uploader("📤 TXT laden", type=["txt"])
    if uploaded:
        st.session_state.content = uploaded.read().decode("utf-8")

    if st.button("🆕 Neue Klausur"):
        st.session_state.clear()
        st.rerun()

# ---------------- Layout ----------------
col_toc, col_edit = st.columns([1, 3])

doc = KlausurDocument()

content = st.session_state.get(
    "content",
    "Teil 1* Zulässigkeit\n\nA* Formelle Voraussetzungen\n\nI* Antrag"
)

lines = content.splitlines()
structure = doc.parse_structure(lines)

# ---------------- TOC ----------------
with col_toc:
    st.subheader("📋 Gliederung")
    for e in structure:
        indent = " " * (e["level"] - 1)
        if st.button(f"{indent}{e['title']}", key=f"toc_{e['line']}"):
            st.session_state.jump = e["line"]

# ---------------- Editor ----------------
with col_edit:
    st.subheader("✍️ Editor")

    if "jump" in st.session_state:
        marker = f"\n>>> SPRUNG ZU ZEILE {st.session_state.jump+1} <<<\n"
        lines.insert(st.session_state.jump, marker)
        content = "\n".join(lines)
        del st.session_state.jump

    content = st.text_area(
        "",
        value=content,
        height=650
    )
    st.session_state.content = content

# ---------------- Export ----------------
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.download_button(
        "💾 TXT speichern",
        content,
        file_name="klausur.txt"
    )

with c2:
    if st.button("🎯 PDF erzeugen"):
        pdf = doc.to_pdf_bytes(
            doc.to_latex(title, date.strftime("%d.%m.%Y"), matrikel, content.splitlines())
        )
        st.download_button("⬇️ PDF herunterladen", pdf, "klausur.pdf", "application/pdf")
