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
                    cmds = {1: "section", 2: "subsection", 3: "subsubsection", 
                            4: "paragraph", 5: "subparagraph", 6: "subparagraph", 
                            7: "subparagraph", 8: "subparagraph"}
                    cmd = cmds.get(level, "subparagraph")
                    
                    # MIKRO-EINRÜCKUNGEN (Jetzt extrem dezent gestaffelt)
                    # A. (0) -> I. (0.15) -> 1. (0.3) -> a) (0.4) -> aa) (0.5) ...
                    if level == 1: indent = 0.0
                    elif level == 2: indent = 0.0
                    elif level == 3: indent = 0.15
                    elif level == 4: indent = 0.3
                    elif level == 5: indent = 0.4
                    elif level == 6: indent = 0.5
                    elif level == 7: indent = 0.6
                    else: indent = 0.7
                        
                    latex_output.append(f"\\{cmd}*{{{line_s}}}")
                    latex_output.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{\\hspace{{{indent}cm}}{line_s}}}")
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
                parsed_content = doc_parser.parse_content(user_input.split('\n'))
                titel_komplett = f"{kl_titel} ({kl_datum})"
                
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage{setspace}
\usepackage[T1]{fontenc}
\usepackage{palatino}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{tocloft}
\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}

% --- KOPFZEILE & SEITENZAHL FIX ---
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small """ + kl_kuerzel + r"""}
\fancyhead[R]{\small """ + titel_komplett + r"""}
\fancyfoot[R]{\thepage}
\renewcommand{\headrulewidth}{0.5pt}

% Diese Befehle verhindern das Überschreiben der Kopfzeile durch jurabook
\renewcommand{\sectionmark}[1]{}
\renewcommand{\subsectionmark}[1]{}

\makeatletter
\renewcommand{\@cfoot}{} 
\makeatother

\begin{document}
\pagenumbering{gobble}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage

% --- START TEXTTEIL ---
\pagenumbering{arabic}
\setcounter{page}{1}
% Explizites Setzen der Marks, um "Gliederung" aus dem Speicher zu werfen
\markboth{}{} 
\setstretch{1.2}

{\noindent\Large\bfseries """ + titel_komplett + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                env = os.environ.copy()
                env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

                # 2 Durchläufe für TOC
                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   env=env, capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    st.success("PDF erfolgreich erstellt!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Download", f, f"Klausur_{kl_kuerzel}.pdf")
                else:
                    st.error("Fehler - Prüfe Log.")

if __name__ == "__main__":
    main()
