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
                        cmd = "section*" if level == 1 else "subsection*" if level == 2 else "subsubsection*"
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

# --- PDF EXTRAKTION ---
def simple_extract_pdf(pdf_file):
    text = ""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text("text")
        doc.close()
        # Nur einfache Zeilenumbruch-Korrektur bei Bindestrichen
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        return text
    except Exception as e:
        return f"Fehler: {e}"

def handle_upload():
    if st.session_state.uploader_key:
        st.session_state["main_editor_key"] = st.session_state.uploader_key.read().decode("utf-8")

# --- UI SETUP ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""
if "sv_fixed" not in st.session_state:
    st.session_state["sv_fixed"] = False

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; max-width: 98% !important; }
        .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 1.1rem; line-height: 1.5; color: #1e1e1e; }
        .sachverhalt-fixed {
            background-color: #f0f2f6; padding: 20px; border-radius: 8px; 
            border-left: 6px solid #ff4b4b; margin-bottom: 15px; 
            line-height: 1.6; font-size: 1rem; white-space: pre-wrap;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR ---
    with st.sidebar.expander("⚙️ Layout-Einstellungen"):
        rand_wert = st.text_input("Korrekturrand rechts (cm)", value="6")
        if not any(u in rand_wert for u in ['cm', 'mm']): rand_wert += "cm"
        zeilenabstand = st.selectbox("Zeilenabstand", ["1.0", "1.2", "1.5", "2.0"], index=1)
        font_options = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
        selected_font = font_options[st.selectbox("Schriftart", list(font_options.keys()))]

    fall_code = st.sidebar.text_input("📖 Fall-Code")
    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- SACHVERHALT LOGIK ---
    if st.session_state.get("sachverhalt_key"):
        if "extracted_sv_text" not in st.session_state:
            st.session_state["extracted_sv_text"] = simple_extract_pdf(st.session_state["sachverhalt_key"])
        
        with st.expander("📄 Sachverhalt (PDF)", expanded=not st.session_state["sv_fixed"]):
            if not st.session_state["sv_fixed"]:
                st.info("Formatierung vornehmen:")
                st.session_state["extracted_sv_text"] = st.text_area("PDF-Inhalt anpassen", value=st.session_state["extracted_sv_text"], height=300)
                if st.button("📌 SV fixieren"):
                    st.session_state["sv_fixed"] = True
                    st.rerun()
            else:
                st.markdown(f'<div class="sachverhalt-fixed">{st.session_state["extracted_sv_text"]}</div>', unsafe_allow_html=True)
                if st.button("🔓 SV bearbeiten"):
                    st.session_state["sv_fixed"] = False
                    st.rerun()

    if fall_code:
        pfad = os.path.join("fealle", f"{fall_code}.txt")
        if os.path.exists(pfad):
            with open(pfad, "r", encoding="utf-8") as f:
                lines = f.read().split('\n')
                with st.expander(f"📖 {lines[0]}", expanded=True):
                    st.markdown(f'<div class="sachverhalt-fixed">{" ".join(lines[1:])}</div>', unsafe_allow_html=True)

    # --- MAIN EDITOR ---
    c1, c2, c3 = st.columns([3, 1, 1])
    kl_titel = c1.text_input("Titel", "Klausur")
    kl_datum = c2.text_input("Datum", "")
    kl_kuerzel = c3.text_input("Kürzel", "")

    current_text = st.text_area("", height=600, key="main_editor_key")

    # --- SIDEBAR GLIEDERUNG ---
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown("&nbsp;" * (level * 2) + line_s)
                    break

    # --- ACTIONS ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sv_up = st.columns(4)
    
    pdf_gen = col_pdf.button("🏁 PDF generieren", use_container_width=True)
    col_save.download_button("💾 Als TXT speichern", current_text, "Gutachten.txt", use_container_width=True)
    col_load.file_uploader("📂 TXT laden", type=['txt'], key="uploader_key", on_change=handle_upload)
    col_sv_up.file_uploader("📄 PDF SV importieren", type=['pdf'], key="sachverhalt_key")

    if pdf_gen:
        if not current_text.strip():
            st.warning("Kein Text vorhanden.")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            if not os.path.exists(cls_path):
                st.error("jurabook.cls fehlt!")
                st.stop()
            with st.spinner("PDF wird generiert..."):
                parsed = doc_parser.parse_content(current_text.split('\n'))
                titel_f = f"{kl_titel} ({kl_datum})" if kl_datum else kl_titel
                
                header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages, setspace, geometry, fancyhdr}
\usepackage{""" + selected_font + r"""}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_f + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
}
\begin{document}
\sloppy
"""
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    shutil.copy(os.path.abspath(cls_path), tmp_path / "jurabook.cls")
                    
                    sv_cmd = ""
                    if st.session_state.get("sachverhalt_key"):
                        with open(tmp_path / "temp_sv.pdf", "wb") as f:
                            f.write(st.session_state.sachverhalt_key.getbuffer())
                        sv_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = header + sv_cmd + r"""
\pagenumbering{gobble}\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}\setcounter{page}{1}\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_f + r""" \par}\bigskip
""" + parsed + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(final_latex)
                    
                    env = os.environ.copy()
                    env["TEXINPUTS"] = f".:{tmp_path}:{os.path.abspath('latex_assets')}:"
                    
                    for _ in range(2):
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname, env=env)

                    if (tmp_path / "klausur.pdf").exists():
                        st.success("PDF bereit!")
                        with open(tmp_path / "klausur.pdf", "rb") as f:
                            st.download_button("📥 Download PDF", f, "Gutachten.pdf", use_container_width=True)
                    else:
                        st.error("Fehler bei LaTeX-Kompilierung.")

if __name__ == "__main__":
    main()
