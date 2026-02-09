import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path
import fitz  # PyMuPDF für die PDF-Extraktion

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

# --- HILFSFUNKTIONEN ---
def simple_extract_pdf(pdf_file):
    """Extrahiert Text und entfernt nur harte Trennstriche am Zeilenende."""
    text = ""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text("text")
        doc.close()
        # Entfernt Bindestriche am Zeilenende: "Haft-\n ung" -> "Haftung"
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        return text
    except Exception as e:
        return f"Fehler beim Lesen der PDF: {e}"

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; max-width: 98% !important; }
        .stTextArea textarea { 
            font-family: 'Inter', sans-serif; font-size: 1.1rem; 
            line-height: 1.5; padding: 15px; color: #1e1e1e;
        }
        /* Styling für die PDF-Vorschau Box */
        div[data-testid="stExpander"] .stTextArea textarea {
            background-color: #f8f9fb;
            border-left: 5px solid #ff4b4b;
            font-size: 0.95rem;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

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

    # --- CASE LOGIC (BEARBEITBARER SACHVERHALT) ---
    if st.session_state.get("sachverhalt_key") is not None:
        # Initiales Auslesen
        if "extracted_sv_text" not in st.session_state:
            st.session_state["extracted_sv_text"] = simple_extract_pdf(st.session_state["sachverhalt_key"])
        
        with st.expander("📄 Sachverhalt bearbeiten & vorbereiten", expanded=True):
            st.info("Hier kannst du den Text aus der PDF zurechtrücken (Absätze, AGB etc.), bevor du ihn ins Gutachten kopierst.")
            # Nutzer kann den Text hier bearbeiten
            edited_sv = st.text_area("PDF-Inhalt", value=st.session_state["extracted_sv_text"], height=300, key="sv_editor_field")
            
            col_a, col_b = st.columns(2)
            if col_a.button("✅ In Gutachten übernehmen"):
                st.session_state["main_editor_key"] += "\n\n" + edited_sv
                st.rerun()
            if col_b.button("🗑️ PDF-Daten verwerfen"):
                del st.session_state["extracted_sv_text"]
                # Wir können den uploader nicht direkt löschen, aber den State bereinigen
                st.rerun()
    
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
                    st.text_area("Fall-Inhalt", value=rest_text, height=200)

    # --- EDITOR AREA ---
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area("", height=600, key="main_editor_key", placeholder="Schreibe hier dein Gutachten...")

    # --- SIDEBAR OUTLINE ---
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            found = False
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    indent = "&nbsp;" * (level * 2)
                    st.sidebar.markdown(f"{indent}{line_s}")
                    break

    # --- ACTIONS ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sachverhalt = st.columns([1, 1, 1, 1])

    with col_pdf: pdf_button = st.button("🏁 PDF generieren", use_container_width=True)
    with col_save: st.download_button("💾 Als TXT speichern", data=current_text, file_name="Gutachten.txt", use_container_width=True)
    with col_load: st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)
    with col_sachverhalt: 
        st.file_uploader("📄 Sachverhalt (PDF importieren)", type=['pdf'], key="sachverhalt_key")

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
    \renewcommand{\headrulewidth}{0.5pt}
}
\begin{document}
"""
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    shutil.copy(os.path.abspath(cls_path), tmp_path / "jurabook.cls")
                    
                    assets_folder = os.path.abspath("latex_assets")
                    if os.path.exists(assets_folder):
                        for item in os.listdir(assets_folder):
                            s = os.path.join(assets_folder, item)
                            d = os.path.join(tmpdirname, item)
                            if os.path.isfile(s) and not item.endswith('.cls'):
                                shutil.copy2(s, d)

                    sachverhalt_cmd = ""
                    if st.session_state.get("sachverhalt_key") is not None:
                        with open(tmp_path / "temp_sv.pdf", "wb") as f:
                            f.write(st.session_state.sachverhalt_key.getbuffer())
                        sachverhalt_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = full_latex_header + sachverhalt_cmd + r"""
\pagenumbering{gobble}\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}\setcounter{page}{1}\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(final_latex)
                    
                    env = os.environ.copy()
                    env["TEXINPUTS"] = f".:{tmp_path}:{assets_folder}:"

                    for _ in range(2):
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
