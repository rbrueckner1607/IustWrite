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
        [cite_start]} [cite: 1, 2]

        self.star_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*(\s|$)',
            2: r'^\s*[A-H]\*(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*(\s|$)',
            4: r'^\s*\d+\*(\s|$)',
            5: r'^\s*[a-z]\)\*(\s|$)'
        [cite_start]} [cite: 2, 3]

        [cite_start]self.footnote_pattern = r'\\fn\((.*?)\)' [cite: 3]

    def parse_content(self, lines):
        latex_output = []

        for line in lines:
            line_s = line.strip()

            if not line_s:
                latex_output.append("\\medskip")
                [cite_start]continue [cite: 3, 4]

            found_level = False

            # Sterne-Überschriften
            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*", 4: "paragraph*", 5: "subparagraph*"}
                    cmd = cmds.get(level, "subparagraph*")
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    [cite_start]break [cite: 4, 5, 6, 7]

            # Normale Überschriften
            if not found_level:
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        cmds = {
                            1: "section", 2: "subsection", 3: "subsubsection",
                            4: "paragraph", 5: "subparagraph", 6: "subparagraph",
                            7: "subparagraph", 8: "subparagraph"
                        [cite_start]} [cite: 7, 8, 9, 10, 11]
                        cmd = cmds.get(level, "subparagraph")
                        indent = max(0, (level - 2) * 0.15) if level > 1 else 0

                        latex_output.append(f"\\{cmd}*{{{line_s}}}")
                        latex_output.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{\\hspace{{{indent}cm}}{line_s}}}")
                        found_level = True
                        [cite_start]break [cite: 11, 12, 13]

            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                [cite_start]latex_output.append(line_s) [cite: 13, 14]

        return "\n".join(latex_output)


# --- UI ---
[cite_start]st.set_page_config(page_title="IustWrite Editor", layout="wide") [cite: 14]

def load_klausur():
    uploaded_file = st.session_state.uploader_key
    if uploaded_file is not None:
        loaded_text = uploaded_file.read().decode("utf-8")
        st.session_state.klausur_text = st.session_state.klausur_text + "\n\n--- NEU GELADETE KLASUR ---\n\n" + loaded_text
        [cite_start]st.session_state.show_success = True [cite: 15]

def main():
    doc_parser = KlausurDocument()
    [cite_start]st.title("⚖️ IustWrite Editor") [cite: 16]

    if "klausur_text" not in st.session_state:
        st.session_state.klausur_text = ""
    if "show_success" not in st.session_state:
        [cite_start]st.session_state.show_success = False [cite: 16]

    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Klausur-Titel", "Übungsklausur")
    with c2: kl_datum = st.text_input("Datum", "04.02.2026")
    [cite_start]with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "K-123") [cite: 16, 17]

    st.sidebar.title("📌 Gliederung")

    [cite_start]user_input = st.text_area("Gutachten-Text", value=st.session_state.klausur_text, height=700, key="klausur_text") [cite: 17]

    if user_input:
        char_count = len(user_input)
        col1, col2 = st.columns([4, 1])
        [cite_start]with col2: st.metric("Zeichen", f"{char_count:,}") [cite: 17, 18]

        for line in user_input.split('\n'):
            line_s = line.strip()
            found = False
            for level, pattern in doc_parser.star_patterns.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 4)}**{line_s}**")
                    found = True
                    break
            if not found:
                for level, pattern in doc_parser.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        st.sidebar.markdown("&nbsp;" * (level * 4) + line_s)
                        [cite_start]break [cite: 18, 19, 20, 21]

    col_pdf, col_save, col_load = st.columns([1, 1, 1])

    with col_pdf:
        if st.button("🏁 PDF generieren"):
            with st.spinner("Präzisions-Kompilierung läuft..."):
                parsed_content = doc_parser.parse_content(user_input.split('\n'))
                titel_komplett = f"{kl_titel} ({kl_datum})"

                # --- FIX: Neudefinition von paragraph/subparagraph für Zeilenumbruch ---
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
""" + parsed_content + r"""
\end{document}
[cite_start]""" [cite: 22]

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                env = os.environ.copy()
                [cite_start]env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:" [cite: 22, 23]

                for _ in range(2):
                    [cite_start]subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], env=env, capture_output=True) [cite: 23, 24]

                if os.path.exists("klausur.pdf"):
                    st.success("PDF erfolgreich erstellt!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Download", f, f"Klausur_{kl_kuerzel}.pdf")
                else:
                    [cite_start]st.error("Fehler beim Erzeugen.") [cite: 24, 25]

    with col_save:
        if st.button("💾 Als TXT speichern", type="secondary"):
            [cite_start]st.download_button(label="📥 Download TXT", data=user_input, file_name=f"Klausur_{kl_kuerzel}_{kl_titel.replace(' ', '_')}.txt", mime="text/plain") [cite: 25, 26]

    with col_load:
        [cite_start]st.file_uploader("📂 Klausur laden", type=['txt'], key="uploader_key", on_change=load_klausur) [cite: 26, 27]

    if st.session_state.get("show_success", False):
        st.success("✅ Klausur geladen!")
        st.session_state.show_success = False

if __name__ == "__main__":
    main()
