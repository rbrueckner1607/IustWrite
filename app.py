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

    def get_latex_level_command(self, level, title_text):
        # Mapping auf LaTeX-Standardebenen
        commands = {1: "section", 2: "subsection", 3: "subsubsection", 
                    4: "paragraph", 5: "subparagraph", 6: "subparagraph", 
                    7: "subparagraph", 8: "subparagraph"}
        cmd = commands.get(level, "subparagraph")
        # Jede Ebene erhält einen eigenen addcontentsline-Eintrag
        return f"\\{cmd}*{{{title_text}}}\n\\addcontentsline{{toc}}{{{cmd}}}{{{title_text}}}"

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
                    latex_output.append(self.get_latex_level_command(level, line_s))
                    found_level = True
                    break
            if found_level: continue

            line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
            line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
            latex_output.append(line_s)
            
        return "\n".join(latex_output)

# --- UI SETTINGS ---
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
    user_input = st.text_area("Gutachten-Text", height=500, key="editor")

    if user_input:
        for line in user_input.split('\n'):
            line_s = line.strip()
            for level, pattern in doc_parser.prefix_patterns.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown("&nbsp;" * (level * 4) + line_s)
                    break

    if st.button("🏁 PDF generieren"):
        if user_input:
            with st.spinner("Präzisions-Kompilierung läuft..."):
                parsed_latex = doc_parser.parse_content(user_input.split('\n'))
                
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{tocloft}

\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}

% --- TOC EINRÜCKUNGEN (Treppen-Logik erzwingen) ---
\setcounter{tocdepth}{8}
\setcounter{secnumdepth}{8}
\setlength{\cftsecindent}{0em}
\setlength{\cftsubsecindent}{1.5em}
\setlength{\cftsubsubsecindent}{3em}
\setlength{\cftparaindent}{4.5em}
\setlength{\cftsubparaindent}{6em}

% --- DOPPELTE SEITENZAHLEN & KOPFZEILE FIX ---
\pagestyle{fancy}
\fancyhf{} % Löscht ALLES (Kopf- und Fußzeile)
\fancyhead[L]{\small """ + kl_kuerzel + r"""}
\fancyhead[R]{\small """ + kl_titel + r"""}
\fancyfoot[R]{\thepage} % Seitenzahl NUR rechts unten
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0pt}

% Jurabook spezifische Deaktivierung der Standard-Kopfzeilen (wichtig!)
\makeatletter
\renewcommand{\@evenhead}{}
\renewcommand{\@oddhead}{\fancyplain{}{\fancyhead[L]{\small """ + kl_kuerzel + r"""}\fancyhead[R]{\small """ + kl_titel + r"""}}}
\renewcommand{\@evenfoot}{}
\renewcommand{\@oddfoot}{\fancyplain{}{\fancyfoot[R]{\thepage}}}
\makeatother

\begin{document}
% 1. Gliederung ohne Zahlen
\pagenumbering{gobble}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage

% 2. Textteil
\pagenumbering{arabic}
\setcounter{page}{1}
\setstretch{1.2}

\section*{""" + kl_titel + " (" + kl_datum + r""")}

""" + parsed_latex + r"\end{document}"

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                env = os.environ.copy()
                env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

                # 2 Durchläufe für TOC
                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   env=env, capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    st.success("PDF erstellt!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 PDF herunterladen", f, f"Klausur_{kl_kuerzel}.pdf")
                else:
                    st.error("Fehler beim Erzeugen des PDF.")

if __name__ == "__main__":
    main()
