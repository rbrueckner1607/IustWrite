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
        # Muster für die automatische Gliederungserkennung
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
            # Check for non-TOC headers (with *)
            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*"}
                    cmd = cmds.get(level, "subsubsection*")
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    break

            if not found_level:
                # Check for standard TOC headers
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
                # Text processing for footnotes and special characters
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- INTELLIGENTE PDF-REINIGUNG ---
def clean_jur_text(text):
    """Säubert extrahierten Text unter Erhalt von Absätzen, Gesetzen und AGB-Strukturen."""
    lines = text.split('\n')
    cleaned_lines = []
    buffer = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                cleaned_lines.append(buffer)
                buffer = ""
            continue

        # Erkennt strukturelle Zeilen (Paragrafen, Listen, AGB-Klauseln, Zitate)
        # Diese Zeilen sollen NICHT mit dem Text davor verschmolzen werden
        is_structural = re.match(r'^(\S~|§|\d+\.|[a-z]\)|-|\"|„|Art\.|[A-Z]\.)', stripped)

        if is_structural:
            if buffer:
                cleaned_lines.append(buffer)
            buffer = stripped
            cleaned_lines.append(buffer)
            buffer = ""
        else:
            # Silbentrennung am Zeilenende entfernen
            if buffer.endswith('-'):
                buffer = buffer[:-1] + stripped
            else:
                buffer = (buffer + " " + stripped).strip()

            # Wenn die Zeile mit einem Punkt/Doppelpunkt endet, ist der Satz oft vorbei
            if stripped.endswith(('.', ':', '!', '?')):
                cleaned_lines.append(buffer)
                buffer = ""

    if buffer:
        cleaned_lines.append(buffer)

    return '\n\n'.join(cleaned_lines)

def extract_text_from_pdf(pdf_file):
    """Extrahiert Text aus PDF und wendet die juristische Reinigung an."""
    text = ""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return clean_jur_text(text)
    except Exception as e:
        return f"Fehler beim Lesen der PDF: {e}"

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

# --- UI SETUP ---
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
        .sachverhalt-box {
            background-color: #f0f2f6; padding: 20px; border-radius: 8px; 
            border-left: 6px solid #ff4b4b; margin-bottom: 25px; 
            line-height: 1.6; font-size: 1rem; white-space: pre-wrap;
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

    fall_code = st.sidebar.text_input("📖 Fall-Code eingeben")
    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- CASE LOGIC (SACHVERHALT) ---
    if st.session_state.get("sachverhalt_key") is not None:
        if "extracted_sv_text" not in st.session_state:
            st.session_state["extracted_sv_text"] = extract_text_from_pdf(st.session_state["sachverhalt_key"])
        
        with st.expander("📄 Aktueller Sachverhalt (PDF)", expanded=True):
            st.markdown(f'<div class="sachverhalt-box">{st.session_state["extracted_sv_text"]}</div>', unsafe_allow_html=True)
            if st.button("Text an Gutachten anfügen"):
                st.session_state["main_editor_key"] += "\n\n" + st.session_state["extracted_sv_text"]
                st.rerun()
    else:
        if "extracted_sv_text" in st.session_state:
            del st.session_state["extracted_sv_text"]

    if fall_code:
        pfad = os.path.join("fealle", f"{fall_code}.txt")
        if os.path.exists(pfad):
            with open(pfad, "r", encoding="utf-8") as f:
                content = f.read().split('\n')
                st.sidebar.info(f"Fall geladen: {content[0]}")
                with st.expander(f"📖 {content[0]}", expanded=True):
                    st.markdown(f'<div class="sachverhalt-box">{" ".join(content[1:])}</div>', unsafe_allow_html=True)

    # --- EDITOR AREA ---
    c1, c2, c3 = st.columns([3, 1, 1])
    kl_titel = c1.text_input("Titel", "Klausur")
    kl_datum = c2.text_input("Datum", "")
    kl_kuerzel = c3.text_input("Kürzel / Matrikel", "")

    current_text = st.text_area("", height=600, key="main_editor_key", placeholder="Hier schreiben...")

    # --- LIVE SIDEBAR OUTLINE ---
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown("&nbsp;" * (level * 2) + line_s)
                    break

    # --- ACTIONS ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sv_up = st.columns(4)
    
    pdf_button = col_pdf.button("🏁 PDF generieren", use_container_width=True)
    col_save.download_button("💾 Als TXT speichern", current_text, "Gutachten.txt", use_container_width=True)
    col_load.file_uploader("📂 TXT laden", type=['txt'], key="uploader_key", on_change=handle_upload)
    col_sv_up.file_uploader("📄 PDF SV importieren", type=['pdf'], key="sachverhalt_key")

    # --- PDF GENERATOR LOGIC ---
    if pdf_button:
        if not current_text.strip():
            st.warning("Bitte Text eingeben!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            if not os.path.exists(cls_path):
                st.error("🚨 jurabook.cls fehlt in /latex_assets!")
                st.stop()

            with st.spinner("Erstelle PDF..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                
                font_latex = f"\\usepackage{{{selected_font_package}}}"
                if "helvet" in selected_font_package: 
                    font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
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
\sloppy
"""
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    shutil.copy(os.path.abspath(cls_path), tmp_path / "jurabook.cls")
                    
                    # Kopiere Assets (Logos etc.) falls vorhanden
                    assets_folder = os.path.abspath("latex_assets")
                    if os.path.exists(assets_folder):
                        for item in os.listdir(assets_folder):
                            s, d = os.path.join(assets_folder, item), os.path.join(tmpdirname, item)
                            if os.path.isfile(s) and not item.endswith('.cls'): shutil.copy2(s, d)

                    sv_cmd = ""
                    if st.session_state.get("sachverhalt_key"):
                        with open(tmp_path / "temp_sv.pdf", "wb") as f:
                            f.write(st.session_state.sachverhalt_key.getbuffer())
                        sv_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = header + sv_cmd + r"""
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
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                       cwd=tmpdirname, env=env, capture_output=True)

                    pdf_file = tmp_path / "klausur.pdf"
                    if pdf_file.exists():
                        st.success("PDF erfolgreich erstellt!")
                        with open(pdf_file, "rb") as f:
                            st.download_button("📥 Download PDF", f, "Gutachten.pdf", use_container_width=True)
                    else:
                        st.error("LaTeX Fehler!")

if __name__ == "__main__":
    main()
