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
                latex_output.append("\\par\\medskip")
                continue

            found_level = False
            # Check for Star-Patterns
            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*", 4: "paragraph*", 5: "subparagraph*"}
                    cmd = cmds.get(level, "subparagraph*")
                    # Nur bei tiefen Ebenen (4+) den Umbruch erzwingen
                    suffix = "\\mbox{}\\par" if level >= 4 else ""
                    latex_output.append(f"\\{cmd}{{{line_s}}}{suffix}")
                    found_level = True
                    break

            # Check for Prefix-Patterns
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
                        # Nur bei tiefen Ebenen (4+) den Umbruch erzwingen
                        suffix = "\\mbox{}\\par" if level >= 4 else ""
                        
                        latex_output.append(f"\\{cmd}*{{{line_s}}}{suffix}")
                        toc_cmd = "subsubsection" if level >= 3 else cmd
                        latex_output.append(f"\\addcontentsline{{toc}}{{{toc_cmd}}}{{\\hspace{{{toc_indent}}}{line_s}}}")
                        found_level = True
                        break

            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(f"{line_s}") 
                
        return "\n".join(latex_output)

# --- UI SETTINGS ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

if "klausur_text" not in st.session_state:
    st.session_state.klausur_text = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state.klausur_text = content

def main():
    doc_parser = KlausurDocument()
    
    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR ---
    st.sidebar.title("⚙️ Layout")
    rand_input = st.sidebar.text_input("Korrekturrand rechts", value="6cm")
    
    # NEU: Zeilenabstand Slider
    z_abstand = st.sidebar.slider("Zeilenabstand", 1.0, 2.0, 1.3, 0.1)
    
    font_options = {
        "Latin Modern (Standard)": "\\usepackage{lmodern}",
        "Palatino": "\\usepackage{mathpazo}",
        "Helvetica (Sans-Serif)": "\\usepackage[scaled]{helvet}\n\\renewcommand{\\familydefault}{\\sfdefault}"
    }
    selected_font_label = st.sidebar.selectbox("Schriftart wählen", list(font_options.keys()))
    font_code = font_options[selected_font_label]

    rand_wert = rand_input.strip()
    if not any(unit in rand_wert for unit in ['cm', 'mm', 'in', 'pt']):
        rand_wert += "cm"
    
    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- EDITOR ---
    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Titel", "Gutachten")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area("Gutachten Text", value=st.session_state.klausur_text, height=600, key="main_editor_key")

    # Gliederungsvorschau
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 2)} {line_s}")
                    break

    # --- PDF GENERIERUNG ---
    if st.button("🏁 PDF generieren"):
        if not current_text.strip():
            st.warning("Editor leer!")
        else:
            with st.spinner("PDF wird erstellt..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel

                full_latex = r"""\documentclass[12pt, a4paper]{article}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
""" + font_code + r"""
\usepackage{setspace}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{microtype}

\sloppy 
\setlength{\parindent}{0pt} % Verhindert das Einrücken nach Überschriften
\setlength{\parskip}{6pt}   % Definiert Abstände zwischen Absätzen

\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm, headsep=1cm}

\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_komp + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
}

\begin{document}
\pagenumbering{gobble}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage

\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}

\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm, includehead}
\setstretch{""" + str(z_abstand) + r"""}
\emergencystretch 3em 

{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip

""" + parsed_content + r"""

\end{document}
"""
                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)
                
                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], capture_output=True)

                if os.path.exists("klausur.pdf"):
                    st.success("PDF erfolgreich erstellt!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Download PDF", f, f"Klausur_{kl_kuerzel}.pdf")

    st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

if __name__ == "__main__":
    main()
