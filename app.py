import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path
import fitz  # PyMuPDF zum Auslesen der PDF

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
                        if level >= 3: cmd = "subsubsection*"
                        elif level == 2: cmd = "subsection*"
                        else: cmd = "section*"
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

# --- PDF HELFER ---
def extract_pdf_text(uploaded_file):
    try:
        # Reset stream position
        uploaded_file.seek(0)
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text
    except Exception as e:
        return f"Fehler beim Lesen der PDF: {e}"

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

# Session State Initialisierung
if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        try:
            content = st.session_state.uploader_key.read().decode("utf-8")
            st.session_state["main_editor_key"] = content
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; max-width: 98% !important; }
        .stTextArea textarea { 
            font-family: 'Inter', sans-serif; 
            font-size: 1.1rem; line-height: 1.5; padding: 15px; 
        }
        .sachverhalt-box {
            background-color: #f0f4f8;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #0056b3;
            border-left: 6px solid #0056b3;
            margin-bottom: 25px;
            line-height: 1.6;
            font-size: 1rem;
            color: #1a365d;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR ---
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

    # --- SACHVERHALT ANZEIGE OBEN ---
    if st.session_state.get("sachverhalt_key"):
        sv_text = extract_pdf_text(st.session_state["sachverhalt_key"])
        with st.expander("📄 Importierter Sachverhalt (Vorschau)", expanded=True):
            st.markdown(f'<div class="sachverhalt-box">{sv_text}</div>', unsafe_allow_html=True)

    # --- EXTERNE FÄLLE ---
    if fall_code:
        pfad_zu_fall = os.path.join("fealle", f"{fall_code}.txt")
        if os.path.exists(pfad_zu_fall):
            with open(pfad_zu_fall, "r", encoding="utf-8") as f:
                ganzer_text = f.read()
            zeilen = ganzer_text.split('\n')
            if zeilen:
                sauberer_titel = re.sub(r'^#+\s*(Fall\s+\d+:\s*)?', '', zeilen[0]).strip()
                rest_text = "\n".join(zeilen[1:]).strip()
                with st.expander(f"📖 {sauberer_titel}", expanded=True):
                    st.markdown(f'<div class="sachverhalt-box">{rest_text}</div>', unsafe_allow_html=True)

    # --- EDITOR AREA ---
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    # Fix: Editor nutzt session_state als Quelle
    current_text = st.text_area(
        "", 
        value=st.session_state["main_editor_key"], 
        height=600, 
        key="main_editor_area", 
        placeholder="Schreibe hier dein Gutachten...",
        label_visibility="collapsed"
    )
    # Synchronisiere den Text zurück in den State
    st.session_state["main_editor_key"] = current_text

    # --- SIDEBAR OUTLINE ---
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    indent = "&nbsp;" * (level * 2)
                    st.sidebar.markdown(f"{indent}{line_s}")
                    break

    # --- AKTIONEN UNTEN ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sachverhalt = st.columns([1, 1, 1, 1])

    with col_pdf:
        pdf_button = st.button("🏁 PDF generieren", use_container_width=True)
    
    with col_save:
        st.download_button("💾 Als TXT speichern", data=current_text, file_name="Gutachten.txt", use_container_width=True)
    
    with col_load:
        st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)
    
    with col_sachverhalt:
        st.file_uploader("📄 Extra Sachverhalt (PDF)", type=['pdf'], key="sachverhalt_key")

    # --- LATEX GENERIERUNG ---
    if pdf_button:
        if not current_text.strip():
            st.warning("Bitte Text eingeben!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            with st.spinner("PDF wird erstellt..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                
                font_latex = f"\\usepackage{{{selected_font_package}}}"
                if "helvet" in selected_font_package:
                    font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                full_latex_header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages, setspace, geometry, fancyhdr}
\addto\captionsngerman{\renewcommand{\contentsname}{Gliederung}}
""" + font_latex + r"""
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_komp + r"""}
    \fancyfoot[R]{\thepage}
}
\begin{document}
"""
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    if os.path.exists("latex_assets"):
                        for item in os.listdir("latex_assets"):
                            shutil.copy(os.path.join("latex_assets", item), tmp_path / item)

                    sachverhalt_cmd = ""
                    if st.session_state["sachverhalt_key"]:
                        with open(tmp_path / "temp_sv.pdf", "wb") as f:
                            f.write(st.session_state["sachverhalt_key"].getbuffer())
                        sachverhalt_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = full_latex_header + sachverhalt_cmd + r"""
\pagenumbering{gobble}\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}\setcounter{page}{1}\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(final_latex)
                    
                    for _ in range(2):
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname)

                    pdf_output = tmp_path / "klausur.pdf"
                    if pdf_output.exists():
                        st.success("✅ PDF erfolgreich erstellt!")
                        with open(pdf_output, "rb") as f:
                            st.download_button("📥 PDF herunterladen", f, "Gutachten.pdf", use_container_width=True)
                    else:
                        st.error("Fehler bei der PDF-Erzeugung.")

if __name__ == "__main__":
    main()
