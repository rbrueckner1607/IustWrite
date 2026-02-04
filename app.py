import streamlit as st
import subprocess
import os
import re

# ---------------- PARSER ----------------
class KlausurDocument:
    def __init__(self):
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)\s.*',
            6: r'^\s*[a-z]{2}\)\s.*',
            7: r'^\s*\([a-z]\)\s.*',
            8: r'^\s*\([a-z]{2}\)\s.*'
        }

        # FIXE, PLATZSPARENDE TOC-EINRÜCKUNG
        self.indent_boxes = {
            1: "0em",
            2: "0em",
            3: "0.8em",
            4: "1.2em",
            5: "1.6em",
            6: "2.0em",
            7: "2.0em",
            8: "2.0em",
        }

    def parse_content(self, lines):
        latex = []

        for line in lines:
            s = line.strip()

            if not s:
                latex.append("\\medskip")
                continue

            matched = False
            for level, pattern in self.prefix_patterns.items():
                if re.match(pattern, s):
                    cmd_map = {
                        1: "section",
                        2: "section",
                        3: "subsection",
                        4: "subsubsection",
                        5: "paragraph",
                        6: "subparagraph",
                        7: "subparagraph",
                        8: "subparagraph",
                    }
                    cmd = cmd_map[level]
                    box = self.indent_boxes[level]

                    latex.append(f"\\{cmd}*{{{s}}}")
                    latex.append(
                        f"\\addcontentsline{{toc}}{{{cmd}}}"
                        f"{{\\protect\\makebox[{box}][l]{{}}{s}}}"
                    )
                    matched = True
                    break

            if not matched:
                latex.append(
                    s.replace('&', '\\&')
                     .replace('%', '\\%')
                     .replace('§', '\\S~')
                )

        return "\n".join(latex)


# ---------------- UI ----------------
st.set_page_config(page_title="IustWrite Editor", layout="wide")
st.title("⚖️ IustWrite Editor")

parser = KlausurDocument()

c1, c2, c3 = st.columns(3)
with c1:
    titel = st.text_input("Klausur-Titel", "Übungsklausur")
with c2:
    datum = st.text_input("Datum", "04.02.2026")
with c3:
    kuerzel = st.text_input("Kürzel / Matrikel", "K-123")

st.sidebar.title("📌 Gliederung")

text = st.text_area("Gutachten-Text", height=600)

# ---------- LIVE-GLIEDERUNG LINKS ----------
if text:
    for line in text.split("\n"):
        s = line.strip()
        for lvl, pat in parser.prefix_patterns.items():
            if re.match(pat, s):
                st.sidebar.markdown("&nbsp;" * (lvl * 4) + s)
                break

# ---------- PDF ----------
if st.button("🏁 PDF generieren"):
    if not text.strip():
        st.warning("Kein Text vorhanden.")
    else:
        with st.spinner("Kompiliere jurabook-PDF …"):
            body = parser.parse_content(text.split("\n"))
            titel_full = f"{titel} ({datum})"

            latex = rf"""
\documentclass[12pt,a4paper,oneside]{{jurabook}}
\usepackage[ngerman]{{babel}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{setspace}}
\usepackage{{palatino}}
\usepackage{{geometry}}
\usepackage{{fancyhdr}}

\geometry{{left=2cm,right=6cm,top=2.5cm,bottom=3cm}}

\fancypagestyle{{iustwrite}}{{
  \fancyhf{{}}
  \fancyhead[L]{{\small {kuerzel}}}
  \fancyhead[R]{{\small {titel_full}}}
  \fancyfoot[R]{{\thepage}}
  \renewcommand{{\headrulewidth}}{{0.5pt}}
}}

\begin{{document}}
\pagenumbering{{gobble}}
\renewcommand{{\contentsname}}{{Gliederung}}
\tableofcontents
\clearpage

\pagestyle{{iustwrite}}
\pagenumbering{{arabic}}
\setstretch{{1.2}}

\noindent\Large\bfseries {titel_full}\par\bigskip

{body}

\end{{document}}
"""

            with open("klausur.tex", "w", encoding="utf-8") as f:
                f.write(latex)

            env = os.environ.copy()
            env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "klausur.tex"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            if os.path.exists("klausur.pdf"):
                with open("klausur.pdf", "rb") as f:
                    st.download_button(
                        "📥 PDF herunterladen",
                        f,
                        file_name=f"Klausur_{kuerzel}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("PDF konnte nicht erzeugt werden.")
