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

# --- HILFSFUNKTIONEN ---
def clean_pdf_text(pdf_file):
    text = ""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        paragraphs = text.split('\n\n')
        cleaned = [p.replace('\n', ' ').strip() for p in paragraphs if p.strip()]
        return '\n\n'.join(cleaned)
    except Exception as e:
        return f"Fehler: {e}"

def handle_upload():
    if st.session_state.uploader_key:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

# --- UI SETUP ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

# Session State Initialisierung
if "main_editor_key" not in st.session_state: st.session_state["main_editor_key"] = ""
if "sv_fixed" not in st.session_state: st.session_state["sv_fixed"] = False
if "sv_text" not in st.session_state: st.session_state["sv_text"] = ""
if "last_sv_name" not in st.session_state: st.session_state["last_sv_name"] = ""

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; max-width: 98% !important; }
        .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 1.1rem; line-height: 1.5; background: rgba(255,255,255,0.7); border-radius: 10px; }
        
        .sidebar-outline { font-size: 0.82rem; line-height: 1.2; margin-bottom: 2px; color: #333; }
        .outline-lvl-1 { font-weight: bold; color: #000; border-bottom: 1px solid rgba(0,0,0,0.1); margin-top: 5px; }

        /* Die Box mit der blauen Linie links */
        .glassy-box {
            display: flex !important;
            background: rgba(241, 243, 246, 0.7);
            backdrop-filter: blur(10px);
            border-radius: 8px;
            margin-bottom: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            overflow: hidden;
            border-left: 8px solid #003366 !important; /* Direkte Linie */
        }
        .box-content {
            padding: 20px;
            line-height: 1.6;
            font-size: 1.05rem;
            color: #1e293b;
            flex-grow: 1;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR ---
    with st.sidebar.expander("⚙️ Layout"):
        rand = st.text_input("Rand rechts (cm)", "6")
        abstand = st.selectbox("Zeilenabstand", ["1.0", "1.2", "1.5", "2.0"], index=1)
        font_opt = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
        selected_font = font_opt[st.selectbox("Schriftart", list(font_opt.keys()), index=0)]

    with st.sidebar.expander("📖 Fall abrufen"):
        fall_code = st.text_input("Fall-Code")

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")
    outline_container = st.sidebar.container()

    # --- SACHVERHALT (PDF) ---
    sv_upload = st.file_uploader("📄 Sachverhalt PDF importieren", type=['pdf'], key="sachverhalt_key")
    if sv_upload:
        if st.session_state["last_sv_name"] != sv_upload.name:
            st.session_state["sv_text"] = clean_pdf_text(sv_upload)
            st.session_state["last_sv_name"] = sv_upload.name
            st.session_state["sv_fixed"] = False

        if not st.session_state["sv_fixed"]:
            st.session_state["sv_text"] = st.text_area("SV Editor", value=st.session_state["sv_text"], height=200, label_visibility="collapsed")
            if st.button("🔒 Sachverhalt fixieren"):
                st.session_state["sv_fixed"] = True
                st.rerun()
        else:
            st.markdown(f'<div class="glassy-box"><div class="box-content">{st.session_state["sv_text"]}</div></div>', unsafe_allow_html=True)
            if st.button("🔓 Fixierung lösen"):
                st.session_state["sv_fixed"] = False
                st.rerun()

    # --- EXTERNE FÄLLE ---
    if fall_code:
        pfad = os.path.join("fealle", f"{fall_code}.txt")
        if os.path.exists(pfad):
            with open(pfad, "r", encoding="utf-8") as f:
                content = f.read().split('\n')
                rest = "\n".join(content[1:])
                with st.expander(f"📖 {content[0]}", expanded=True):
                    # Hier wird die blaue Linie über die CSS-Klasse erzwungen
                    st.markdown(f'<div class="glassy-box"><div class="box-content">{rest}</div></div>', unsafe_allow_html=True)

    # --- MAIN EDITOR ---
    c1, c2, c3 = st.columns([3, 1, 1])
    kl_titel = c1.text_input("Titel", "Klausur")
    kl_datum = c2.text_input("Datum", "")
    kl_kuerzel = c3.text_input("Kürzel", "")
    
    # FIX: Bindung an Session State verhindert das Löschen des Textes beim Fixieren
    current_text = st.text_area("", height=500, key="main_editor_key", placeholder="Gutachten hier verfassen...")

    # Sidebar Gliederung
    if current_text:
        with outline_container:
            for line in current_text.split('\n'):
                line_s = line.strip()
                for level, pattern in {**doc_parser.star_patterns, **doc_parser.prefix_patterns}.items():
                    if re.match(pattern, line_s):
                        px_indent = level * 8
                        css_class = "sidebar-outline outline-lvl-1" if level == 1 else "sidebar-outline"
                        st.markdown(f'<div class="{css_class}" style="padding-left:{px_indent}px;">{line_s}</div>', unsafe_allow_html=True)
                        break

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    if col1.button("🏁 PDF generieren", use_container_width=True):
        if not current_text.strip():
            st.warning("Kein Text!")
        else:
            with st.spinner("PDF wird erstellt..."):
                font_package = f"\\usepackage{{{selected_font}}}"
                if selected_font == "helvet":
                    font_package += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\addto\captionsngerman{\renewcommand{\contentsname}{Gliederung}}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{cmap, pdfpages, setspace, geometry, fancyhdr, tocloft}
\usepackage[protrusion=true, expansion=true]{microtype}
""" + font_package + r"""
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\setlength{\cftbeforesecskip}{1pt}
\setlength{\cftbeforesubsecskip}{0pt}
\begin{document}
"""
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_p = Path(tmp)
                    asset_src = os.path.abspath("latex_assets")
                    if os.path.exists(asset_src):
                        for file in os.listdir(asset_src):
                            shutil.copy(os.path.join(asset_src, file), tmp_p / file)

                    sv_inc = ""
                    if sv_upload:
                        with open(tmp_p / "sv.pdf", "wb") as f:
                            f.write(sv_upload.getbuffer())
                        sv_inc = r"\includepdf[pages=-]{sv.pdf}"

                    t_str = f"{kl_titel} ({kl_datum})" if kl_datum else kl_titel
                    final_tex = header + sv_inc + \
                                r"\pagenumbering{gobble}\tableofcontents\clearpage" + \
                                r"\newgeometry{left=2cm, right=" + rand + r"cm, top=2.5cm, bottom=3cm}" + \
                                r"\pagestyle{fancy}\fancyhf{}" + \
                                r"\setlength{\headwidth}{\textwidth}" + \
                                r"\fancyhead[L]{\small " + kl_kuerzel + r"}\fancyhead[R]{\small " + t_str + r"}" + \
                                r"\fancyfoot[R]{\thepage}\setstretch{" + abstand + r"}" + \
                                r"\pagenumbering{arabic}\setcounter{page}{1}" + \
                                r"{\noindent\Large\bfseries " + t_str + r" \par}\bigskip\noindent " + \
                                doc_parser.parse_content(current_text.split('\n')) + r"\end{document}"
                    
                    with open(tmp_p / "k.tex", "w", encoding="utf-8") as f:
                        f.write(final_tex)
                    
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "k.tex"], cwd=tmp)
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "k.tex"], cwd=tmp)

                    if (tmp_p / "k.pdf").exists():
                        st.success("✅ PDF erfolgreich erstellt!")
                        with open(tmp_p / "k.pdf", "rb") as f:
                            st.download_button("📥 PDF herunterladen", f, "Gutachten.pdf", use_container_width=True)

    col2.download_button("💾 Als TXT speichern", current_text, "Gutachten.txt", use_container_width=True)
    col3.file_uploader("📂 TXT laden", type=['txt'], key="uploader_key", on_change=handle_upload)

if __name__ == "__main__":
    main()
