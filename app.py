import streamlit as st
import subprocess
import os
import re

# --- PARSER KLASSE (DEIN ORIGINAL-CODE) ---
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
        self.footnote_pattern = r'\\fn\((.*?)\)'

    def get_latex_level_command(self, level, title_text):
        # Zuordnung der Ebenen für jurabook (angepasst für saubere TOC-Struktur)
        commands = {1: "section", 2: "subsection", 3: "subsubsection", 
                    4: "paragraph", 5: "subparagraph", 6: "subparagraph", 
                    7: "subparagraph", 8: "subparagraph"}
        cmd = commands.get(level, "subparagraph")
        return f"\\{cmd}*{{{title_text}}}\n\\addcontentsline{{toc}}{{{cmd}}}{{{title_text}}}"

    def parse_content(self, lines):
        latex_output = []
        for line in lines:
            line_s = line.strip()
            if not line_s:
                latex_output.append("\\medskip")
                continue
            
            # Gliederungs-Erkennung
            found = False
            for level, pattern in self.prefix_patterns.items():
                if re.match(pattern, line_s):
                    latex_output.append(self.get_latex_level_command(level, line_s))
                    found = True
                    break
            if found: continue

            # Text & Fußnoten
            line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
            line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
            latex_output.append(line_s)
            
        return "\n".join(latex_output)

# --- UI ---
st.set_page_config(page_title="Jura Klausur-Editor", layout="wide")

def main():
    doc_parser = KlausurDocument()
    st.sidebar.title("📌 Gliederung")
    st.title("Jura Klausur-Editor")

    user_input = st.text_area("Gutachten...", height=500, key="editor")

    # Live-Sidebar
    if user_input:
        for line in user_input.split('\n'):
            for level, pattern in doc_parser.prefix_patterns.items():
                if re.match(pattern, line.strip()):
                    st.sidebar.markdown("&nbsp;" * (level*4) + line.strip())
                    break

    if st.button("🏁 PDF generieren"):
        if user_input:
            with st.spinner("Kompiliere 12-seitiges PDF..."):
                parsed_latex = doc_parser.parse_content(user_input.split('\n'))
                
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{setspace}
\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}
\setcounter{secnumdepth}{6}
\setcounter{tocdepth}{6}
\begin{document}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage
\setstretch{1.2}
""" + parsed_latex + r"\end{document}"

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                env = os.environ.copy()
                env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

                # PDFlatex Aufruf
                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   env=env, capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    st.success("PDF bereit!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Jetzt PDF herunterladen", f, "Klausur.pdf")
                else:
                    st.error("Fehler beim Erzeugen des PDF.")

if __name__ == "__main__":
    main()
