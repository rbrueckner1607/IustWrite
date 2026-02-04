import subprocess
import os
import re
import streamlit as st

# --- ERWEITERTE PARSER KLASSE ---
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
        self.star_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*(\s|$)',
            2: r'^\s*[A-H]\*(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*(\s|$)',
            4: r'^\s*\d+\*(\s|$)',
            5: r'^\s*[a-z]\)\*(\s|$)'
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
            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*", 4: "paragraph*", 5: "subparagraph*"}
                    cmd = cmds.get(level, "subparagraph*")
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    break
            if not found_level:
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        cmds = {1: "section", 2: "subsection", 3: "subsubsection", 4: "paragraph", 5: "subparagraph", 6: "subparagraph", 7: "subparagraph", 8: "subparagraph"}
                        cmd = cmds.get(level, "subparagraph")
                        toc_indent = f"{max(0, level - 3)}em" if level > 3 else "0em"
                        latex_output.append(f"\\{cmd}*{{{line_s}}}")
                        toc_cmd = "subsubsection" if level >= 3 else cmd
                        latex_output.append(f"\\addcontentsline{{toc}}{{{toc_cmd}}}{{\\hspace{{{toc_indent}}}{line_s}}}")
                        found_level = True
                        break
            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- UI SETUP ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

# CSS für engere Sidebar-Abstände
st.markdown("""
    <style>
    [data-testid="stSidebar"] button {
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        height: 1.8rem !important;
        min-height: 1.8rem !important;
        line-height: 1 !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    doc_parser = KlausurDocument()
    st.title("⚖️ IustWrite Editor")

    if "klausur_text" not in st.session_state:
        st.session_state.klausur_text = ""

    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Klausur-Titel", "Übungsklausur")
    with c2: kl_datum = st.text_input("Datum", "04.02.2026")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "K-123")

    # --- SIDEBAR ---
    st.sidebar.title("📌 Gliederung")
    
    # Textarea
    # "label_visibility='collapsed'" spart Platz oben
    user_input = st.text_area("Gutachten-Text", value=st.session_state.klausur_text, height=700, key="klausur_text_area")
    # Wir synchronisieren den State
    st.session_state.klausur_text = user_input

    # Gliederung in Sidebar generieren
    if user_input:
        lines = user_input.split('\n')
        for i, line in enumerate(lines):
            line_s = line.strip()
            found = False
            level_found = 0
            
            # Check patterns
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    level_found = level
                    found = True
                    break
            
            if found:
                # Button statt Text für Klickbarkeit
                indent = " " * (level_found * 2)
                if st.sidebar.button(f"{indent}{line_s}", key=f"nav_{i}"):
                    # Kleiner Hack: Wir können in Streamlit nicht den Cursor setzen, 
                    # aber wir können eine Info anzeigen, wo man ist. 
                    # Ein echtes "Scroll-To" in der Textarea erfordert Custom JS Components.
                    st.toast(f"Springe zu: {line_s}")

    # --- BUTTONS ---
    col_pdf, col_save, col_load = st.columns([1, 1, 1])
    # ... (Rest der PDF-Logik bleibt gleich wie im vorherigen Code) ...
    with col_pdf:
        if st.button("🏁 PDF generieren"):
            parsed_content = doc_parser.parse_content(user_input.split('\n'))
            # ... (LaTeX Generierung siehe oben) ...
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
\makeatletter
\renewcommand\paragraph{\@startsection{paragraph}{4}{\z@}%
  {-3.25ex\@plus -1ex \@minus -.2ex}%
  {1.5ex \@plus .2ex}%
  {\normalfont\normalsize\bfseries}}
\renewcommand\subparagraph{\@startsection{subparagraph}{5}{\z@}%
  {-3.25ex\@plus -1ex \@minus -.2ex}%
  {1.5ex \@plus .2ex}%
  {\normalfont\normalsize\bfseries}}
\makeatother
\fancypagestyle{iustwrite}{
\fancyhf{}
\fancyhead[L]{\small """ + kl_kuerzel + r"""}
\fancyhead[R]{\small """ + titel_komplett + r"""}
\fancyfoot[R]{\thepage}
\renewcommand{\headrulewidth}{0.5pt}
\renewcommand{\footrulewidth}{0pt}
}
\begin{document}
\pagenumbering{gobble}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage
\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}
\setstretch{1.2}
{\noindent\Large\bfseries """ + titel_komplett + r""" \par}\bigskip
\noindent
""" + parsed_content + r"""
\end{document}
"""
            with open("klausur.tex", "w", encoding="utf-8") as f:
                f.write(full_latex)
            env = os.environ.copy()
            env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"
            for _ in range(2):
                subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], env=env, capture_output=True)
            if os.path.exists("klausur.pdf"):
                st.success("PDF erfolgreich erstellt!")
                with open("klausur.pdf", "rb") as f:
                    st.download_button("📥 Download", f, f"Klausur_{kl_kuerzel}.pdf")

if __name__ == "__main__":
    main()
