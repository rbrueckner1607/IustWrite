import streamlit as st
import subprocess
import os
import re

# --- PARSER KLASSE ---
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
        self.footnote_pattern = r'\\fn\((.*?)\)'

    def parse_content(self, lines):
        latex_output = []
        for line in lines:
            line_s = line.strip()
            if not line_s:
                latex_output.append("\\medskip")
                continue

            found_level = False
            for level, pattern in self.prefix_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {
                        1: "section",
                        2: "subsection",
                        3: "subsubsection",
                        4: "paragraph",
                        5: "subparagraph",
                        6: "subparagraph",
                        7: "subparagraph",
                        8: "subparagraph"
                    }
                    cmd = cmds[level]

                    # ⭐ WICHTIG: KEIN hspace im TOC!
                    latex_output.append(f"\\{cmd}*{{{line_s}}}")
                    latex_output.append(
                        f"\\addcontentsline{{toc}}{{{cmd}}}{{{line_s}}}"
                    )

                    found_level = True
                    break

            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = (
                    line_s.replace('§', '\\S~')
                          .replace('&', '\\&')
                          .replace('%', '\\%')
                )
                latex_output.append(line_s)

        return "\n".join(latex_output)


# --- UI ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

def main():
    doc_parser = KlausurDocument()
    st.title("⚖️ IustWrite Editor")

    c1, c2, c3 = st.columns(3)
    with c1:
        kl_titel = st.text_input("Klausur-Titel", "Übungsklausur")
    with c2:
        kl_datum = st.text_input("Datum", "04.02.2026")
    with c3:
        kl_kuerzel = st.text_input("Kürzel / Matrikel", "K-123")

    st.sidebar.title("📌 Gliederung")
    user_input = st.text_area("Gutachten-Text", height=500)

    if st.button("🏁 PDF generieren") and user_input:
        with st.spinner("Präzisions-Kompilierung läuft..."):
            parsed_content = doc_parser.parse_content(user_input.splitlines())
            titel_komplett = f"{kl_titel} ({kl_datum})"

            full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{palatino}
\usepackage{geometry}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{tocloft}

\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}

\setcounter{secnumdepth}{6}
\setcounter{tocdepth}{6}

% --- TOC: FLACH & PLATZSPAREND ---
\setlength{\cftsectionindent}{0em}
\setlength{\cftsubsectionindent}{0.8em}
\setlength{\cftsubsubsectionindent}{1.6em}
\setlength{\cftparaindent}{2.4em}
\setlength{\cftsubparaindent}{3.2em}

\begin{document}

\pagenumbering{gobble}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage

\pagenumbering{arabic}
\setcounter{page}{1}
\setstretch{1.2}

\noindent{\Large\bfseries """ + titel_komplett + r"""\par}
\bigskip

""" + parsed_content + r"""
\end{document}
"""

            with open("klausur.tex", "w", encoding="utf-8") as f:
                f.write(full_latex)

            # ⭐ ENTSCHEIDEND: jurabook + jurabase finden
            env = os.environ.copy()
            env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

            for _ in range(2):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "klausur.tex"],
                    env=env,
                    capture_output=True
                )

            if os.path.exists("klausur.pdf"):
                st.success("PDF erfolgreich erstellt!")
                with open("klausur.pdf", "rb") as f:
                    st.download_button("📥 Download", f, "klausur.pdf")
            else:
                st.error("PDF nicht erzeugt – bitte Log prüfen.")

if __name__ == "__main__":
    main()
