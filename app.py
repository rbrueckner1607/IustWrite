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
                        cmds = {
                            1: "section", 2: "subsection", 3: "subsubsection",
                            4: "paragraph", 5: "subparagraph", 6: "subparagraph",
                            7: "subparagraph", 8: "subparagraph"
                        }
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

# --- UI SETTINGS ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

if "klausur_text" not in st.session_state:
    st.session_state.klausur_text = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content
        st.session_state.klausur_text = content

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        [data-testid="stSidebar"] .stMarkdown { margin-bottom: -18px; }
        [data-testid="stSidebar"] p { font-size: 0.82rem !important; line-height: 1.1 !important; }
        [data-testid="stSidebar"] h2 { font-size: 1.1rem; padding-bottom: 5px; }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR EINSTELLUNGEN ---
    st.sidebar.title("⚙️ Layout")
    
    # 1. Korrekturrand
    rand_input = st.sidebar.text_input("Korrekturrand rechts (in cm)", value="6")
    rand_wert = rand_input.strip()
    if not any(unit in rand_wert for unit in ['cm', 'mm']):
        rand_wert += "cm"
    
    # 2. Zeilenabstand
    abstand_options = ["1.0", "1.2", "1.5", "2.0"]
    zeilenabstand = st.sidebar.selectbox("Zeilenabstand", options=abstand_options, index=1)

    # 3. Schriftart (NEU)
    font_options = {"lmodern (Standard)": "lmodern", "Palatino": "newpxtext,newpxmath", "Helvetica": "helvet"}
    font_choice = st.sidebar.selectbox("Schriftart", options=list(font_options.keys()), index=0)
    selected_font_package = font_options[font_choice]

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Titel", "Gutachten")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area(
        "Gutachten", 
        value=st.session_state.klausur_text, 
        height=700, 
        key="main_editor_key"
    )

    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            found = False
            for level, pattern in doc_parser.star_patterns.items():
                if re.match(pattern, line_s):
                    weight = "**" if level <= 2 else ""
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 2)}{weight}{line_s}{weight}")
                    found = True
                    break
            if not found:
                for level, pattern in doc_parser.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        weight = "**" if level <= 2 else ""
                        st.sidebar.markdown(f"{'&nbsp;' * (level * 2)}{weight}{line_s}{weight}")
                        break

    col_pdf, col_save, col_load = st.columns([1, 1, 1])

    with col_pdf:
        if st.button("🏁 PDF generieren"):
            if not current_text.strip():
                st.warning("Das Editorfenster ist leer!")
            else:
                with st.spinner("Kompiliere..."):
                    parsed_content = doc_parser.parse_content(current_text.split('\n'))
                    titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel

                    # Font LaTeX Logic
                    font_latex = f"\\usepackage{{{selected_font_package}}}"
                    if "helvet" in selected_font_package:
                        font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                    full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
""" + font_latex + r"""
\usepackage{setspace}
\usepackage{geometry}
\usepackage{fancyhdr}

% Gliederungs-Layout
\geometry{left=2cm, right=3cm, top=2.5cm, bottom=3cm}

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
    \fancyhead[R]{\small """ + titel_komp + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
}

\begin{document}
\sloppy
\pagenumbering{gobble}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage

% Text-Layout mit Variablen aus der Sidebar
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\fancyhfoffset[R]{0pt} 

\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}
\setstretch{""" + zeilenabstand + r"""}

{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
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
                        # Umbenennen für den Download
                        if os.path.exists("Gutachten.pdf"): os.remove("Gutachten.pdf")
                        os.rename("klausur.pdf", "Gutachten.pdf")
                        st.success(f"PDF erstellt ({font_choice}, Rand: {rand_wert}, Zeilenabstand: {zeilenabstand})")
                        with open("Gutachten.pdf", "rb") as f:
                            st.download_button("📥 Download PDF", f, f"Gutachten.pdf")

    with col_save:
        st.download_button("💾 Als TXT speichern", data=current_text, file_name=f"Gutachten.txt")

    with col_load:
        st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

if __name__ == "__main__":
    main()
