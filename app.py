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
            # --- 1. Sternchen-Überschriften ---
            for level, pattern in self.star_patterns.items():
                match = re.match(pattern, line_s)
                if match:
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*"}
                    cmd = cmds.get(level, "subsubsection*")
                    display_text = line_s[match.end():].strip()
                    if not display_text:
                        display_text = line_s.replace('*', '').strip()
                    latex_output.append(f"\\{cmd}{{{display_text}}}")
                    found_level = True
                    break

            # --- 2. Normale Überschriften ---
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
                # 1. Fußnoten
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                
                # 2. Hinweisbox (Sichere Methode ohne re.sub Verluste)
                if "\\hinweis{" in line_s:
                    match = re.search(r'\\hinweis\{(.*?)\}', line_s)
                    if match:
                        inhalt = match.group(1)
                        line_s = f"\\begin{{hinweisbox}}{inhalt}\\end{{hinweisbox}}"
                
                # 3. Sonderzeichen (Nur wenn kein Befehl drin ist)
                if "\\begin" not in line_s:
                    line_s = line_s.replace('&', '\\&').replace('%', '\\%')
                
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

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
        .block-container { padding-top: 1.5rem; padding-left: 2rem; padding-right: 2rem; max-width: 98% !important; }
        .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 1.1rem; line-height: 1.5; padding: 15px; color: #1e1e1e; }
        .sachverhalt-box { background-color: #f0f2f6; padding: 20px; border-radius: 8px; border-left: 6px solid #4682B4; margin-bottom: 25px; }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

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

    if fall_code:
        pfad_zu_fall = os.path.join("fealle", f"{fall_code}.txt")
        if os.path.exists(pfad_zu_fall):
            with open(pfad_zu_fall, "r", encoding="utf-8") as f:
                ganzer_text = f.read()
            zeilen = ganzer_text.split('\n')
            if zeilen:
                sauberer_titel = re.sub(r'^#+\s*(Fall\s+\d+:\s*)?', '', zeilen[0]).strip()
                rest_text = "\n".join(zeilen[1:]).strip()
                with st.expander(f"📄 {sauberer_titel}", expanded=True):
                    st.markdown(f'<div class="sachverhalt-box">{rest_text}</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area("", height=600, key="main_editor_key")

    if pdf_button := st.button("🏁 PDF generieren", use_container_width=True):
        if not current_text.strip():
            st.warning("Bitte Text eingeben!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            with st.spinner("PDF wird erstellt..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                font_latex = f"\\usepackage{{{selected_font_package}}}"

                full_latex_header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages}
\usepackage[most]{tcolorbox}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
""" + font_latex + r"""
\usepackage{setspace}
\usepackage{geometry}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\setcounter{secnumdepth}{8}
\setlength{\parindent}{0pt}

\newtcolorbox{hinweisbox}{
    colback=white, colframe=black, fonttitle=\bfseries, title=Hinweis:,
    arc=0mm, outer arc=0mm, left=3mm, right=3mm, top=2mm, bottom=2mm,
    boxrule=0.6pt, width=\linewidth, breakable
}

\begin{document}
\sloppy
"""
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    if os.path.exists(cls_path): shutil.copy(cls_path, tmp_path / "jurabook.cls")
                    
                    final_latex = full_latex_header + r"""
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}
\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(final_latex)
                    
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname)
                    pdf_file = tmp_path / "klausur.pdf"
                    if pdf_file.exists():
                        st.success("Erfolgreich!")
                        with open(pdf_file, "rb") as f:
                            st.download_button("📥 Download PDF", f, file_name="Gutachten.pdf")

if __name__ == "__main__":
    main()
