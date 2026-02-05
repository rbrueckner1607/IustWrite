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

# --- UI HILFSFUNKTIONEN ---
def load_klausur():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state.klausur_editor = content
        st.session_state.show_success = True

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="IustWrite Editor", layout="wide")
    doc_parser = KlausurDocument()
    
    st.title("⚖️ IustWrite Editor")

    if "klausur_editor" not in st.session_state:
        st.session_state.klausur_editor = ""
    if "show_success" not in st.session_state:
        st.session_state.show_success = False

    # --- SIDEBAR EINSTELLUNGEN ---
    with st.sidebar:
        st.markdown("### ⚙️ Einstellungen")
        kl_titel = st.text_input("Titel", "Klausur")
        kl_datum = st.text_input("Datum (optional)", "")
        kl_kuerzel = st.text_input("Kürzel / Matrikel", "")
        # Korrekte Beschriftung und Variable
        kl_rand = st.number_input("Rand (rechts) in cm", min_value=0.0, max_value=15.0, value=6.0, step=0.5)
        
        st.divider()
        st.markdown("### 📌 Gliederung")
        
        if st.session_state.klausur_editor:
            for line in st.session_state.klausur_editor.split('\n'):
                line_s = line.strip()
                found = False
                for level, pattern in doc_parser.star_patterns.items():
                    if re.match(pattern, line_s):
                        st.markdown(f"{'&nbsp;' * (level * 2)}**{line_s}**")
                        found = True
                        break
                if not found:
                    for level, pattern in doc_parser.prefix_patterns.items():
                        if re.match(pattern, line_s):
                            st.markdown("&nbsp;" * (level * 2) + line_s)
                            break

    # --- EDITOR ---
    user_input = st.text_area("Gutachten", height=650, key="klausur_editor")

    # --- AKTIONEN ---
    col_pdf, col_save, col_load = st.columns([1, 1, 1])

    with col_pdf:
        if st.button("🏁 PDF generieren", use_container_width=True):
            if not user_input.strip():
                st.error("Text fehlt.")
            else:
                with st.spinner("Kompilierung läuft..."):
                    parsed_content = doc_parser.parse_content(user_input.split('\n'))
                    
                    # LOGIK: Klammern nur, wenn Datum vorhanden
                    if kl_datum.strip():
                        titel_anzeige = f"{kl_titel} ({kl_datum})"
                    else:
                        titel_anzeige = kl_titel

                    # LaTeX Code mit kl_rand und titel_anzeige
                    full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage{setspace}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{tocloft}
\geometry{left=2cm, right=""" + str(kl_rand) + r"""cm, top=2.5cm, bottom=3cm}

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
\fancyhead[R]{\small """ + titel_anzeige + r"""}
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

{\noindent\Large\bfseries """ + titel_anzeige + r""" \par}\bigskip
\noindent
""" + parsed_content + r"""
\end{document}
"""
                    with open("klausur.tex", "w", encoding="utf-8") as f:
                        f.write(full_latex)

                    env = os.environ.copy()
                    for _ in range(2):
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], env=env, capture_output=True)

                    if os.path.exists("klausur.pdf"):
                        st.success("PDF fertig!")
                        with open("klausur.pdf", "rb") as f:
                            st.download_button("📥 Download", f, f"Klausur.pdf", use_container_width=True)
                    else:
                        st.error("Fehler bei PDF-Erstellung.")

    with col_save:
        st.download_button("💾 Als TXT speichern", data=user_input, file_name="Klausur.txt", use_container_width=True)

    with col_load:
        st.file_uploader("📂 Laden", type=['txt'], key="uploader_key", on_change=load_klausur, label_visibility="collapsed")

if __name__ == "__main__":
    main()
