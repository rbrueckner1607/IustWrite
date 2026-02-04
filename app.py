import streamlit as st
import subprocess
import os
import re

# --- PARSER KLASSE (DEINE LOGIK FÜR JURA-GLIEDERUNG) ---
class KlausurDocument:
    def __init__(self):
        # Muster für die Erkennung der Gliederungsebenen
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
        self.footnote_pattern = r'\\fn\((.*?)\)'

    def get_latex_level_command(self, level, title_text):
        """
        Ordnet die Ebenen den LaTeX-Befehlen zu und erzwingt 
        den manuellen Eintrag ins Inhaltsverzeichnis (TOC).
        """
        commands = {
            1: "section",       # Teil
            2: "subsection",    # A.
            3: "subsubsection", # I.
            4: "paragraph",     # 1.
            5: "subparagraph",  # a)
            6: "subparagraph",  # aa)
            7: "subparagraph",  # (a)
            8: "subparagraph"   # (aa)
        }
        cmd = commands.get(level, "subparagraph")
        # WICHTIG: Manueller TOC-Eintrag für deine Präambel-Makros
        return f"\\{cmd}*{{{title_text}}}\n\\addcontentsline{{toc}}{{{cmd}}}{{{title_text}}}"

    def parse_content(self, lines):
        latex_output = []
        for line in lines:
            line_s = line.strip()
            if not line_s:
                latex_output.append("\\medskip")
                continue
            
            # Gliederungs-Check
            found_level = False
            for level, pattern in self.prefix_patterns.items():
                if re.match(pattern, line_s):
                    latex_output.append(self.get_latex_level_command(level, line_s))
                    found_level = True
                    break
            if found_level: continue

            # Sonderzeichen & Fußnoten
            line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
            line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
            latex_output.append(line_s)
            
        return "\n".join(latex_output)

# --- UI SETTINGS ---
st.set_page_config(page_title="Jura Klausur-Editor", layout="wide")

def main():
    doc_parser = KlausurDocument()
    st.sidebar.title("📌 Gliederung")
    st.title("Jura Klausur-Editor")

    user_input = st.text_area("Dein Gutachten...", height=500, key="editor")

    # Live-Vorschau in der Sidebar
    if user_input:
        for line in user_input.split('\n'):
            line_s = line.strip()
            for level, pattern in doc_parser.prefix_patterns.items():
                if re.match(pattern, line_s):
                    indent = "&nbsp;" * (level * 4)
                    st.sidebar.markdown(f"{indent}{line_s}")
                    break

    if st.button("🏁 PDF generieren"):
        if user_input:
            with st.spinner("PDF wird erstellt (2 Durchläufe)..."):
                parsed_latex = doc_parser.parse_content(user_input.split('\n'))
                
                # DEINE PRÄAMBEL MIT ALLEN MAKROS
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{tocloft}
\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}
\setcounter{secnumdepth}{6}
\setcounter{tocdepth}{6}

% Makros für das Inhaltsverzeichnis (TOC)
\setlength{\cftsecnumwidth}{2em}
\setlength{\cftsubsecnumwidth}{2.5em}
\setlength{\cftsubsubsecnumwidth}{3em}
\setlength{\cftparanumwidth}{3.5em}
\setlength{\cftsubparanumwidth}{4em}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot[R]{\thepage}

\begin{document}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage
\setstretch{1.2}
""" + parsed_latex + r"\end{document}"

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                # Pfad zu jurabook.cls
                env = os.environ.copy()
                env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

                # 2 Durchläufe für das Inhaltsverzeichnis
                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   env=env, capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    st.success("Erfolg! Dein PDF ist fertig.")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Jetzt PDF herunterladen", f, "Jura_Klausur.pdf")
                else:
                    st.error("Fehler: PDF konnte nicht generiert werden.")
                    if os.path.exists("klausur.log"):
                        with open("klausur.log", "r", encoding="utf-8", errors="replace") as log:
                            st.code(log.read()[-2000:])

if __name__ == "__main__":
    main()
