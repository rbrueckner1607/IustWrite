import subprocess
import os
import re
import streamlit as st

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

def load_klausur():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state.klausur_editor = content

# --- MAIN ---
def main():
    st.set_page_config(page_title="IustWrite Editor", layout="wide")
    doc_parser = KlausurDocument()
    
    st.title("⚖️ IustWrite Editor")

    if "klausur_editor" not in st.session_state:
        st.session_state.klausur_editor = ""

    # --- SIDEBAR ---
    with st.sidebar:
        st.subheader("⚙️ Einstellungen")
        kl_titel = st.text_input("Titel", "Klausur")
        kl_datum = st.text_input("Datum (optional)", "")
        kl_kuerzel = st.text_input("Kürzel / Matrikel", "")
        # Der Rand-Input
        kl_rand_val = st.number_input("Rand (rechts) in cm", min_value=0.0, max_value=15.0, value=6.0, step=0.5)
        
        st.divider()
        st.subheader("📌 Gliederung")
        if st.session_state.klausur_editor:
            for line in st.session_state.klausur_editor.split('\n'):
                line_s = line.strip()
                for level, pattern in {**doc_parser.prefix_patterns, **doc_parser.star_patterns}.items():
                    if re.match(pattern, line_s):
                        st.write(f"{'·' * (level * 2)} {line_s}")
                        break

    # --- EDITOR ---
    user_input = st.text_area("Gutachten", height=600, key="klausur_editor")

    col_pdf, col_save, col_load = st.columns([1, 1, 1])

    with col_pdf:
        if st.button("🏁 PDF generieren", use_container_width=True):
            if not user_input.strip():
                st.error("Kein Text vorhanden.")
            else:
                with st.spinner("Erzeuge PDF..."):
                    # DATUM LOGIK: String-Zusammenbau in Python, bevor LaTeX es sieht
                    clean_datum = kl_datum.strip()
                    if clean_datum:
                        titel_anzeige = f"{kl_titel} ({clean_datum})"
                    else:
                        titel_anzeige = kl_titel

                    parsed_body = doc_parser.parse_content(user_input.split('\n'))
                    
                    # LaTeX DOCUMENT
                    # Hier wird der Rand direkt als Zahl mit 'cm' eingefügt
                    full_latex = r"""
\documentclass[12pt, a4paper]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{setspace}

\geometry{left=2cm, right=""" + str(kl_rand_val) + r"""cm, top=2.5cm, bottom=3cm}

\fancypagestyle{iustwrite}{
  \fancyhf{}
  \fancyhead[L]{\small """ + kl_kuerzel + r"""}
  \fancyhead[R]{\small """ + titel_anzeige + r"""}
  \fancyfoot[R]{\thepage}
  \renewcommand{\headrulewidth}{0.5pt}
}

\begin{document}
\pagenumbering{gobble}
\tableofcontents
\clearpage
\pagenumbering{arabic}
\pagestyle{iustwrite}
\setstretch{1.2}
{\noindent\Large\bfseries """ + titel_anzeige + r""" \par}\bigskip
""" + parsed_body + r"""
\end{document}
"""
                    with open("output.tex", "w", encoding="utf-8") as f:
                        f.write(full_latex)

                    # PDF Erzeugung
                    for _ in range(2):
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "output.tex"], capture_output=True)

                    if os.path.exists("output.pdf"):
                        st.success("PDF erfolgreich generiert.")
                        with open("output.pdf", "rb") as f:
                            st.download_button("📥 Jetzt PDF herunterladen", f, file_name="Klausur.pdf", use_container_width=True)
                    else:
                        st.error("LaTeX Fehler. Prüfe den Text auf Sonderzeichen.")

    with col_save:
        st.download_button("💾 Als TXT speichern", data=user_input, file_name="Gutachten.txt", use_container_width=True)

    with col_load:
        st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=load_klausur, label_visibility="collapsed")

if __name__ == "__main__":
    main()
