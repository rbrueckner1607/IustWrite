import streamlit as st
import subprocess
import os
import re

# --- KLAUSUR-PARSER ---
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
                    # Wir erzwingen die Einrückung im Inhaltsverzeichnis händisch!
                    # level 1-8 werden auf die jurabook-befehle gemappt
                    cmds = {1: "section", 2: "subsection", 3: "subsubsection", 
                            4: "paragraph", 5: "subparagraph", 6: "subparagraph", 
                            7: "subparagraph", 8: "subparagraph"}
                    cmd = cmds.get(level, "subparagraph")
                    
                    # Hier wird der TOC-Eintrag mit manuellem Abstand (hspace) gebaut
                    # Das verhindert, dass alles auf einer Linie steht
                    abstand = (level - 1) * 0.5 # Steigerung pro Ebene in cm
                    latex_output.append(f"\\{cmd}*{{{line_s}}}")
                    latex_output.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{\\hspace{{{abstand}cm}}{line_s}}}")
                    found_level = True
                    break
            
            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
            
        return "\n".join(latex_output)

# --- UI ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

def main():
    doc_parser = KlausurDocument()
    st.title("⚖️ IustWrite Editor")
    
    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Klausur-Titel", "Übungsklausur")
    with c2: kl_datum = st.text_input("Datum", "04.02.2026")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "K-123")

    user_input = st.text_area("Gutachten-Text", height=500, key="editor")

    if st.button("🏁 PDF generieren"):
        if user_input:
            with st.spinner("Präzisions-Kompilierung..."):
                parsed_content = doc_parser.parse_content(user_input.split('\n'))
                
                # --- DIE ULTIMATIVE PRÄAMBEL ---
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage{setspace}
\usepackage[T1]{fontenc}
\usepackage{palatino}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{tocloft}

\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}

% Zähler für tiefe Gliederung
\setcounter{secnumdepth}{8}
\setcounter{tocdepth}{8}

% --- SEITENZAHLEN & KOPFZEILE RADIKAL FIXEN ---
\pagestyle{fancy}
\fancyhf{} 
\fancyhead[L]{\small """ + kl_kuerzel + r"""}
\fancyhead[R]{\small """ + kl_titel + r"""}
\fancyfoot[R]{\thepage}
\renewcommand{\headrulewidth}{0.5pt}

% Diese Befehle löschen die jurabook-internen Kolumnentitel (keine "Gliederung" mehr im Kopf)
\renewcommand{\sectionmark}[1]{}
\renewcommand{\subsectionmark}[1]{}

\makeatletter
\renewcommand{\@cfoot}{} % Killt die mittige Seitenzahl
\fancypagestyle{plain}{
  \fancyhf{}
  \fancyfoot[R]{\thepage}
  \renewcommand{\headrulewidth}{0pt}
}
\makeatother

\begin{document}
	\enlargethispage{40pt}
	\pagenumbering{gobble} % Gliederung absolut ohne Zahlen
	\vspace*{-3cm}
	\renewcommand{\contentsname}{Gliederung}
	\tableofcontents
	\clearpage

	\pagenumbering{arabic}
    \setcounter{page}{1}
	\setstretch{1.2}

    % Titel auf der ersten Seite
    {\noindent\Large\bfseries """ + kl_titel + " (" + kl_datum + r") \par}\bigskip
""" + parsed_content + r"\end{document}"

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                env = os.environ.copy()
                env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   env=env, capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    st.success("PDF erfolgreich erstellt!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Download", f, f"Klausur_{kl_kuerzel}.pdf")
                else:
                    st.error("Fehler - Log prüfen.")
                    if os.path.exists("klausur.log"):
                        with open("klausur.log", "r", encoding="utf-8", errors="replace") as log:
                            st.code(log.read()[-2000:])

if __name__ == "__main__":
    main()
