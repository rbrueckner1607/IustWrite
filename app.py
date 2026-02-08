import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path

# --- OPTIMIERTE PARSER KLASSE ---
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
            # Star-Patterns (Manuelle Steuerung)
            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*"}
                    cmd = cmds.get(level, "subsubsection*")
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    break

            # Standard-Gliederung (Automatisch)
            if not found_level:
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        if level >= 3:
                            cmd = "subsubsection*"
                        elif level == 2:
                            cmd = "subsection*"
                        else:
                            cmd = "section*"
                        
                        # Inhaltsverzeichnis-Eintrag mit manuellem Einzug
                        toc_indent = f"{max(0, level - 3)}em" if level > 3 else "0em"
                        latex_output.append(f"\\{cmd}{{{line_s}}}")
                        
                        # Wir mappen alle tiefen Ebenen (4-8) auf subsubsection im TOC
                        toc_level_cmd = "subsubsection" if level >= 3 else cmd.replace("*", "")
                        latex_output.append(f"\\addcontentsline{{toc}}{{{toc_level_cmd}}}{{\\hspace{{{toc_indent}}}{line_s}}}")
                        found_level = True
                        break

            if not found_level:
                # Normaler Text & Sonderzeichen
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        [data-testid="stSidebar"] .stMarkdown { margin-bottom: -18px; }
        [data-testid="stSidebar"] p { font-size: 0.82rem !important; line-height: 1.1 !important; }
        [data-testid="stSidebar"] h2 { font-size: 1.1rem; padding-bottom: 5px; }
        .block-container { padding-top: 2rem; max-width: 95%; }
        .stTextArea textarea { font-family: 'Courier New', Courier, monospace; }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR SETTINGS ---
    st.sidebar.title("⚙️ Layout")
    rand_wert = st.sidebar.text_input("Korrekturrand rechts (in cm)", value="6")
    if not any(unit in rand_wert for unit in ['cm', 'mm']): rand_wert += "cm"
    
    zeilenabstand = st.sidebar.selectbox("Zeilenabstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)

    # lmodern gemäß deinen Vorgaben
    font_options = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
    font_choice = st.sidebar.selectbox("Schriftart", options=list(font_options.keys()), index=0)
    selected_font_package = font_options[font_choice]

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- SIDEBAR OUTLINE (AKTUALISIERT FÜR EBENE 7 & 8) ---
    if st.session_state["main_editor_key"]:
        for line in st.session_state["main_editor_key"].split('\n'):
            line_s = line.strip()
            if not line_s: continue
            
            found = False
            for level, pattern in doc_parser.star_patterns.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 2)}{line_s}")
                    found = True; break
            
            if not found:
                for level, pattern in doc_parser.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        indent = "&nbsp;" * (level * 2)
                        st.sidebar.markdown(f"{indent}{line_s}")
                        found = True; break

    # --- EDITOR AREA ---
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "Gutachten")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area("Gutachten", value=st.session_state["main_editor_key"], height=600, key="editor_area")
    st.session_state["main_editor_key"] = current_text

    # --- ACTIONS ---
    st.markdown("---")
    col_pdf, col_save, col_load = st.columns([1, 1, 1])

    with col_pdf: pdf_button = st.button("🏁 PDF generieren", use_container_width=True)
    with col_save: st.download_button("💾 Als TXT speichern", data=current_text, file_name="Gutachten.txt", use_container_width=True)
    with col_load: st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

    if pdf_button:
        if not current_text.strip():
            st.warning("Bitte Text eingeben!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            with st.spinner("PDF wird erstellt..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                
                font_latex = f"\\usepackage{{{selected_font_package}}}"
                if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                # HEADER MIT TOC-FIX
                full_latex_header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
""" + font_latex + r"""
\usepackage{setspace}
\usepackage{geometry}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}

% Zwingt LaTeX alle Gliederungsebenen ins Inhaltsverzeichnis aufzunehmen
\setcounter{tocdepth}{8}
\setcounter{secnumdepth}{8}

\setlength{\parindent}{0pt}
\begin{document}
\sloppy
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}
\setcounter{page}{1}
\setstretch{""" + zeilenabstand + r"""}
""" + parsed_content + r"\end{document}"

                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    if os.path.exists(cls_path):
                        shutil.copy(os.path.abspath(cls_path), tmp_path / "jurabook.cls")
                    
                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(full_latex_header)
                    
                    # 2 Runs für korrektes Inhaltsverzeichnis
                    for _ in range(2):
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname)

                    pdf_file = tmp_path / "klausur.pdf"
                    if pdf_file.exists():
                        st.success("PDF erfolgreich erstellt!")
                        with open(pdf_file, "rb") as f:
                            st.download_button("📥 Download PDF", f, "Gutachten.pdf", use_container_width=True)
                    else:
                        st.error("LaTeX Fehler!")

if __name__ == "__main__":
    main()
