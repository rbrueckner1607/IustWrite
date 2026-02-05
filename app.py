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

# --- SESSION STATE INITIALISIERUNG ---
if "klausur_text" not in st.session_state:
    st.session_state.klausur_text = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state.klausur_text = content
        # Der Trick: Wir setzen das Widget-Value direkt im Session State
        st.session_state["main_editor_key"] = content

def main():
    doc_parser = KlausurDocument()
    
    # --- CSS FÜR COMPACT SIDEBAR ---
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] .stMarkdown { margin-bottom: -18px; }
        [data-testid="stSidebar"] p { font-size: 0.82rem !important; line-height: 1.1 !important; }
        [data-testid="stSidebar"] h2 { font-size: 1.1rem; padding-bottom: 5px; }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("⚖️ IustWrite Editor")

    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Titel", "Klausur Gutachten")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    st.sidebar.title("📌 Gliederung")

    # WICHTIG: Die text_area nutzt einen stabilen Key aus dem Session State
    user_input = st.text_area(
        "Gutachten", 
        value=st.session_state.klausur_text, 
        height=700, 
        key="main_editor_key" 
    )
    
    # Textänderungen zurückschreiben
    st.session_state.klausur_text = user_input

    # Gliederungsvorschau
    if user_input:
        col1, col2 = st.columns([4, 1])
        with col2: st.metric("Zeichen", f"{len(user_input):,}")

        for line in user_input.split('\n'):
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

    # Action Buttons
    col_pdf, col_save, col_load = st.columns([1, 1, 1])

    with col_pdf:
        if st.button("🏁 PDF generieren"):
            with st.spinner("Kompiliere..."):
                parsed_content = doc_parser.parse_content(user_input.split('\n'))
                titel_komplett = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage{setspace}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}
\begin{document}
\tableofcontents\clearpage
\setstretch{1.2}
{\noindent\Large\bfseries """ + titel_komplett + r""" \par}\bigskip
""" + parsed_content + r"""
\end{document}"""
                with open("klausur.tex", "w", encoding="utf-8") as f: f.write(full_latex)
                for _ in range(2): subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], capture_output=True)
                if os.path.exists("klausur.pdf"):
                    with open("klausur.pdf", "rb") as f: st.download_button("📥 Download PDF", f, "Klausur.pdf")

    with col_save:
        st.download_button("💾 Als TXT speichern", data=user_input, file_name="Klausur.txt")

    with col_load:
        # Hier triggert on_change die Funktion handle_upload
        st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

if __name__ == "__main__":
    main()
