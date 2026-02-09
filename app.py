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

# --- HELPER FÜR PDF EXTRAKTION ---
def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                page_text = re.sub(r'-\s*\n\s*', '', page_text)
                text += page_text + "\n"
        doc.close()
    except Exception as e:
        return f"Fehler beim PDF-Einlesen: {e}"
    return text.strip()

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

# Session States
if "main_editor_content" not in st.session_state: st.session_state["main_editor_content"] = ""
if "sachverhalt_content" not in st.session_state: st.session_state["sachverhalt_content"] = ""
if "edit_mode" not in st.session_state: st.session_state["edit_mode"] = False

def handle_upload():
    if st.session_state.uploader_key is not None:
        st.session_state["main_editor_content"] = st.session_state.uploader_key.read().decode("utf-8")

def main():
    doc_parser = KlausurDocument()
    
    # CSS für Styling
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; max-width: 98% !important; }
        .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 1.1rem; line-height: 1.5; color: #1e1e1e; }
        
        /* Die fixierte Box (Lese-Modus) */
        .sachverhalt-box-fixed {
            background-color: #f0f4f8;
            padding: 20px;
            border-radius: 8px;
            border-left: 6px solid #007bff;
            margin-bottom: 10px;
            font-size: 1rem;
            line-height: 1.6;
            white-space: pre-wrap; /* Bewahrt Zeilenumbrüche */
            max-height: 400px;
            overflow-y: auto;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR SETTINGS ---
    with st.sidebar.expander("⚙️ Layout-Einstellungen"):
        rand_wert = st.text_input("Korrekturrand rechts (in cm)", value="6")
        if not any(unit in rand_wert for unit in ['cm', 'mm']): rand_wert += "cm"
        zeilenabstand = st.selectbox("Zeilenabstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)
        font_options = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
        font_choice = st.selectbox("Schriftart", options=list(font_options.keys()), index=0)
        selected_font_package = font_options[font_choice]

    with st.sidebar.expander("📖 Fall abrufen"):
        fall_code = st.text_input("Fall-Code")
        if fall_code:
            pfad_zu_fall = os.path.join("fealle", f"{fall_code}.txt")
            if os.path.exists(pfad_zu_fall):
                with open(pfad_zu_fall, "r", encoding="utf-8") as f:
                    ganzer_text = f.read().split('\n')
                st.session_state["sachverhalt_content"] = "\n".join(ganzer_text[1:]).strip()
            else: st.sidebar.error("Fall nicht gefunden.")

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- SACHVERHALT LOGIK (FIXIERTE BOX MIT EDIT-OPTION) ---
    if st.session_state["sachverhalt_content"]:
        c_title, c_edit = st.columns([0.85, 0.15])
        with c_title: st.subheader("📄 Sachverhalt")
        with c_edit: 
            if st.button("📝 Bearbeiten" if not st.session_state["edit_mode"] else "✅ Fertig"):
                st.session_state["edit_mode"] = not st.session_state["edit_mode"]
                st.rerun()

        if st.session_state["edit_mode"]:
            # Bearbeitungsmodus: Textarea
            st.session_state["sachverhalt_content"] = st.text_area(
                "Sachverhalt Edit", value=st.session_state["sachverhalt_content"], 
                height=300, label_visibility="collapsed"
            )
        else:
            # Fixierter Modus: HTML Box
            st.markdown(f'<div class="sachverhalt-box-fixed">{st.session_state["sachverhalt_content"]}</div>', unsafe_allow_html=True)

    # --- EDITOR AREA ---
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area("", value=st.session_state["main_editor_content"], height=600, key="main_editor")
    st.session_state["main_editor_content"] = current_text

    # Dynamische Gliederung
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    indent = "&nbsp;" * (level * 2)
                    st.sidebar.markdown(f"{indent}{line_s}")
                    break

    # --- BUTTONS & UPLOADS (UNTER DEM EDITOR) ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sachverhalt = st.columns([1, 1, 1, 1])

    with col_pdf: pdf_button = st.button("🏁 PDF generieren", use_container_width=True)
    with col_save: st.download_button("💾 Als TXT speichern", data=current_text, file_name="Gutachten.txt", use_container_width=True)
    with col_load: st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)
    
    with col_sachverhalt: 
        sachverhalt_file = st.file_uploader("📄 Sachverhalt (PDF)", type=['pdf'], key="sachverhalt_key")
        if sachverhalt_file:
            st.session_state["sachverhalt_content"] = extract_text_from_pdf(sachverhalt_file)
            st.rerun()

    # --- PDF GENERATOR ---
    if pdf_button:
        if not current_text.strip(): st.warning("Text leer!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            with st.spinner("PDF wird erstellt..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                font_latex = f"\\usepackage{{{selected_font_package}}}"
                if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                full_header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{pdfpages}
\addto\captionsngerman{\renewcommand{\contentsname}{Gliederung}}""" + font_latex + r"""
\usepackage{setspace}\usepackage{geometry}\usepackage{fancyhdr}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\fancypagestyle{iustwrite}{\fancyhf{}\fancyhead[L]{\small """ + kl_kuerzel + r"""}\fancyhead[R]{\small """ + titel_komp + r"""}\fancyfoot[R]{\thepage}\renewcommand{\headrulewidth}{0.5pt}}
\begin{document}\sloppy"""
                
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    shutil.copy(os.path.abspath(cls_path), tmp_path / "jurabook.cls")
                    
                    sachverhalt_cmd = ""
                    if sachverhalt_file:
                        sachverhalt_file.seek(0)
                        with open(tmp_path / "temp_sv.pdf", "wb") as f: f.write(sachverhalt_file.getbuffer())
                        sachverhalt_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = full_header + sachverhalt_cmd + r"""
\pagenumbering{gobble}\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}\setcounter{page}{1}\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f: f.write(final_latex)
                    env = os.environ.copy()
                    env["TEXINPUTS"] = f".:{tmp_path}:"
                    for _ in range(2):
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname, env=env)

                    pdf_file = tmp_path / "klausur.pdf"
                    if pdf_file.exists():
                        with open(pdf_file, "rb") as f: st.download_button("📥 Download PDF", f, "Gutachten.pdf", use_container_width=True)
                    else: st.error("LaTeX Fehler!")

if __name__ == "__main__":
    main()
