import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path
import fitz  # PyMuPDF

# --- PARSER KLASSE ---
class KlausurDocument:
    def __init__(self):
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)\s*', 6: r'^\s*[a-z]{2}\)\s*', 7: r'^\s*\([a-z]\)\s*', 8: r'^\s*\([a-z]{2}\)\s*'
        }
        self.star_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*(\s|$)',
            2: r'^\s*[A-H]\*(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*(\s|$)',
            4: r'^\s*\d+\*(\s|$)', 5: r'^\s*[a-z]\)\*(\s|$)'
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
            for level, pattern in {**self.star_patterns, **self.prefix_patterns}.items():
                if re.match(pattern, line_s):
                    cmd = "section*" if level == 1 else "subsection*" if level == 2 else "subsubsection*"
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    if level in self.prefix_patterns:
                        toc_cmd = "subsubsection" if level >= 3 else cmd.replace("*", "")
                        indent = f"{max(0, level-1)}em"
                        latex_output.append(f"\\addcontentsline{{toc}}{{{toc_cmd}}}{{\\hspace{{{indent}}}{line_s}}}")
                    found_level = True
                    break
            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- PDF FUNKTIONEN ---
def clean_pdf_text(pdf_file):
    text = ""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        # Zeilenumbruch-Korrektur
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        # Harte Umbrüche entfernen für volle Breite, aber Absätze erhalten
        paragraphs = text.split('\n\n')
        cleaned = [p.replace('\n', ' ').strip() for p in paragraphs if p.strip()]
        return '\n\n'.join(cleaned)
    except Exception as e:
        return f"Fehler: {e}"

def handle_upload():
    if st.session_state.uploader_key:
        st.session_state["main_editor_key"] = st.session_state.uploader_key.read().decode("utf-8")

# --- UI SETUP ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

if "main_editor_key" not in st.session_state: st.session_state["main_editor_key"] = ""
if "sv_fixed" not in st.session_state: st.session_state["sv_fixed"] = False
if "sv_text" not in st.session_state: st.session_state["sv_text"] = ""

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; max-width: 98% !important; }
        .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 1.1rem; line-height: 1.5; }
        .sachverhalt-box {
            background-color: #f1f3f6; padding: 20px; border-radius: 8px; 
            border-left: 6px solid #ff4b4b; margin-bottom: 20px; 
            line-height: 1.6; font-size: 1.05rem; white-space: pre-wrap; width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR ---
    with st.sidebar.expander("⚙️ Layout"):
        rand = st.text_input("Rand rechts (cm)", "6")
        abstand = st.selectbox("Zeilenabstand", ["1.0", "1.2", "1.5", "2.0"], index=1)
        font_opt = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo"}
        selected_font = font_opt[st.selectbox("Schriftart", list(font_opt.keys()), index=0)]

    with st.sidebar.expander("📖 Fall abrufen", expanded=False):
        fall_code = st.text_input("Fall-Code")

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- SACHVERHALT BEREICH ---
    sv_upload = st.file_uploader("📄 Sachverhalt PDF importieren", type=['pdf'], key="sachverhalt_key")
    
    if sv_upload:
        if not st.session_state["sv_text"]:
            st.session_state["sv_text"] = clean_pdf_text(sv_upload)

        if not st.session_state["sv_fixed"]:
            st.info("Sachverhalt bearbeiten:")
            st.session_state["sv_text"] = st.text_area("SV Editor", value=st.session_state["sv_text"], height=250, label_visibility="collapsed")
            if st.button("🔒 Sachverhalt fixieren"):
                st.session_state["sv_fixed"] = True
                st.rerun()
        else:
            st.markdown(f'<div class="sachverhalt-box">{st.session_state["sv_text"]}</div>', unsafe_allow_html=True)
            if st.button("🔓 Bearbeiten"):
                st.session_state["sv_fixed"] = False
                st.rerun()

    if fall_code:
        pfad = os.path.join("fealle", f"{fall_code}.txt")
        if os.path.exists(pfad):
            with open(pfad, "r", encoding="utf-8") as f:
                content = f.read().split('\n')
                with st.expander(f"📖 {content[0]}", expanded=True):
                    st.markdown(f'<div class="sachverhalt-box">{" ".join(content[1:])}</div>', unsafe_allow_html=True)

    # --- MAIN EDITOR ---
    c1, c2, c3 = st.columns([3, 1, 1])
    kl_titel = c1.text_input("Titel", "Klausur")
    kl_datum = c2.text_input("Datum", "")
    kl_kuerzel = c3.text_input("Kürzel", "")

    current_text = st.text_area("", height=600, key="main_editor_key", placeholder="Hier Gutachten schreiben...")

    # Gliederung Live in Sidebar
    if current_text:
        for line in current_text.split('\n'):
            for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                if re.match(pattern, line.strip()):
                    st.sidebar.markdown("&nbsp;"*(level*2) + line.strip())
                    break

    # --- FOOTER ---
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    if col1.button("🏁 PDF generieren", use_container_width=True):
        if not current_text.strip():
            st.warning("Kein Text!")
        else:
            with st.spinner("PDF wird erstellt..."):
                header = r"""\documentclass[12pt, a4paper]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[T1]{fontenc}
\usepackage{pdfpages, setspace, geometry, fancyhdr}
\usepackage{""" + selected_font + r"""}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}

% Inhaltsverzeichnis kompakter machen
\usepackage{tocloft}
\setlength{\cftbeforesecskip}{2pt}
\setlength{\cftbeforesubsecskip}{0pt}

\begin{document}
"""
                with tempfile.TemporaryDirectory() as tmp:
                    cls_src = os.path.join("latex_assets", "jurabook.cls")
                    if os.path.exists(cls_src):
                        shutil.copy(cls_src, os.path.join(tmp, "jurabook.cls"))
                        sv_inc = ""
                        if sv_upload:
                            with open(os.path.join(tmp, "sv.pdf"), "wb") as f:
                                f.write(sv_upload.getbuffer())
                            sv_inc = r"\includepdf[pages=-]{sv.pdf}"

                        # LaTeX mit begrenzter Kopfzeile und Inhaltsverzeichnis
                        t_str = f"{kl_titel} ({kl_datum})" if kl_datum else kl_titel
                        final_tex = header + sv_inc + \
                                    r"\pagenumbering{gobble}\tableofcontents\clearpage" + \
                                    r"\newgeometry{left=2cm, right=" + rand + r"cm, top=2.5cm, bottom=3cm}" + \
                                    r"\pagestyle{fancy}\fancyhf{}" + \
                                    r"\fancyhead[L]{\small " + kl_kuerzel + r"}\fancyhead[R]{\small " + t_str + r"}" + \
                                    r"\fancyfoot[R]{\thepage}\setstretch{" + abstand + r"}" + \
                                    r"\pagenumbering{arabic}\setcounter{page}{1}" + \
                                    doc_parser.parse_content(current_text.split('\n')) + r"\end{document}"
                        
                        with open(os.path.join(tmp, "k.tex"), "w", encoding="utf-8") as f:
                            f.write(final_tex)
                        
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "k.tex"], cwd=tmp)
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "k.tex"], cwd=tmp)

                        if os.path.exists(os.path.join(tmp, "k.pdf")):
                            with open(os.path.join(tmp, "k.pdf"), "rb") as f:
                                st.download_button("📥 PDF laden", f, "Gutachten.pdf", use_container_width=True)

    col2.download_button("💾 TXT speichern", current_text, "Gutachten.txt", use_container_width=True)
    col3.file_uploader("📂 TXT laden", type=['txt'], key="uploader_key", on_change=handle_upload)

if __name__ == "__main__":
    main()
