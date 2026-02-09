import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path
import fitz  # PyMuPDF

# --- OPTIMIERTE PARSER KLASSE ---
class KlausurDocument:
    def __init__(self):
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)\s*',       
            6: r'^\s*[a-z]{2}\)\s*',    
            7: r'^\s*\([a-z]\)\s*',     
            8: r'^\s*\([a-z]{2}\)\s*'   
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
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*"}
                    cmd = cmds.get(level, "subsubsection*")
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    break

            if not found_level:
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        if level >= 3:
                            cmd = "subsubsection*"
                        elif level == 2:
                            cmd = "subsection*"
                        else:
                            cmd = "section*"
                        
                        toc_indent = f"{max(0, level - 1)}em" 
                        latex_output.append(f"\\{cmd}{{{line_s}}}")
                        
                        toc_cmd = "subsubsection" if level >= 3 else cmd.replace("*", "")
                        latex_output.append(f"\\addcontentsline{{toc}}{{{toc_cmd}}}{{\\hspace{{{toc_indent}}}{line_s}}}")
                        found_level = True
                        break

            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

# Session States
if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""
if "sv_text" not in st.session_state:
    st.session_state["sv_text"] = ""
if "sv_fixed" not in st.session_state:
    st.session_state["sv_fixed"] = False

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

def extract_pdf_text():
    if st.session_state.sachverhalt_key:
        doc = fitz.open(stream=st.session_state.sachverhalt_key.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        # Silbentrennung entfernen: Bindestrich + Zeilenumbruch
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', full_text)
        # Normale Zeilenumbrüche durch Leerzeichen ersetzen für Blocksatz
        text = text.replace('\n', ' ')
        st.session_state["sv_text"] = text.strip()
        st.session_state["sv_fixed"] = True

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        .block-container { 
            padding-top: 1.5rem; padding-left: 2rem; padding-right: 2rem; max-width: 98% !important; 
        }
        .stTextArea textarea { 
            font-family: 'Inter', sans-serif; font-size: 1.1rem; line-height: 1.5; padding: 15px; color: #1e1e1e;
        }
        .sachverhalt-box {
            background-color: #f0f2f6; padding: 20px; border-radius: 8px;
            border-left: 6px solid #003366; /* Dunkelblau */
            margin-bottom: 20px; line-height: 1.6; font-size: 1rem;
            width: 100%; text-align: justify; /* Gleichmäßig verteilt */
        }
        .stats-container {
            font-size: 0.85rem; color: #666; margin-top: -15px; margin-bottom: 15px; text-align: right;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- 1. SACHVERHALT OBEN ---
    if st.session_state["sv_text"]:
        if st.session_state["sv_fixed"]:
            st.markdown(f'<div class="sachverhalt-box">{st.session_state["sv_text"]}</div>', unsafe_allow_html=True)
            if st.button("🔓 Sachverhalt bearbeiten"):
                st.session_state["sv_fixed"] = False
                st.rerun()
        else:
            new_sv = st.text_area("Sachverhalt anpassen:", value=st.session_state["sv_text"], height=250)
            st.session_state["sv_text"] = new_sv
            if st.button("🔒 Sachverhalt fixieren"):
                st.session_state["sv_fixed"] = True
                st.rerun()

    # --- SIDEBAR SETTINGS ---
    with st.sidebar.expander("⚙️ Layout-Einstellungen", expanded=False):
        rand_wert = st.text_input("Korrekturrand rechts (in cm)", value="6")
        if not any(unit in rand_wert for unit in ['cm', 'mm']): rand_wert += "cm"
        zeilenabstand = st.selectbox("Zeilenabstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)
        font_options = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
        font_choice = st.selectbox("Schriftart", options=list(font_options.keys()), index=0)
        selected_font_package = font_options[font_choice]

    with st.sidebar.expander("📖 Fall abrufen", expanded=False):
        fall_code = st.text_input("Fall-Code eingeben")

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- EDITOR AREA ---
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area("", height=600, key="main_editor_key", placeholder="Schreibe hier dein Gutachten...")
    
    # Zähler
    words = len(current_text.split())
    chars = len(current_text)
    st.markdown(f'<div class="stats-container">Wörter: {words} | Zeichen: {chars}</div>', unsafe_allow_html=True)

    # Sidebar Gliederung (Logik bleibt identisch)
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            for level, pattern in doc_parser.star_patterns.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 2)}{line_s}")
            for level, pattern in doc_parser.prefix_patterns.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 2)}{'**' if level <= 2 else ''}{line_s}{'**' if level <= 2 else ''}")

    # --- ACTIONS ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sachverhalt = st.columns([1, 1, 1, 1])

    with col_pdf: pdf_button = st.button("🏁 PDF generieren", use_container_width=True)
    with col_save: st.download_button("💾 Als TXT speichern", data=current_text, file_name="Gutachten.txt", use_container_width=True)
    with col_load: st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)
    with col_sachverhalt: 
        st.file_uploader("📄 Sachverhalt (PDF)", type=['pdf'], key="sachverhalt_key", on_change=extract_pdf_text)

    # --- PDF GENERIERUNG ---
    if pdf_button:
        if not current_text.strip():
            st.warning("Bitte Text eingeben!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            if not os.path.exists(cls_path):
                st.error("🚨 jurabook.cls fehlt!")
                st.stop()

            with st.spinner("PDF wird erstellt..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                font_latex = f"\\usepackage{{{selected_font_package}}}"
                if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                full_latex_header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages}
\addto\captionsngerman{\renewcommand{\contentsname}{Gliederung}}
""" + font_latex + r"""
\usepackage{setspace}
\usepackage{geometry}
\usepackage{fancyhdr}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\setcounter{tocdepth}{8}
\setcounter{secnumdepth}{8}
\setlength{\parindent}{0pt}
\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_komp + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
}
\begin{document}
\sloppy
"""
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    shutil.copy(os.path.abspath(cls_path), tmp_path / "jurabook.cls")
                    
                    # SV PDF Management
                    sachverhalt_cmd = ""
                    if st.session_state.sachverhalt_key:
                        with open(tmp_path / "temp_sv.pdf", "wb") as f:
                            f.write(st.session_state.sachverhalt_key.getbuffer())
                        sachverhalt_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = full_latex_header + sachverhalt_cmd + r"""
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(final_latex)
                    
                    env = os.environ.copy()
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname, env=env)
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname, env=env)

                    pdf_file = tmp_path / "klausur.pdf"
                    if pdf_file.exists():
                        st.success("PDF erfolgreich erstellt!")
                        with open(pdf_file, "rb") as f:
                            st.download_button("📥 Download PDF", f, "Gutachten.pdf", use_container_width=True)
                    else:
                        st.error("LaTeX Fehler!")

if __name__ == "__main__":
    main()
