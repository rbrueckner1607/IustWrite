import subprocess
import os
import re
import streamlit as st
import webbrowser
import tempfile
import shutil
from pathlib import Path
from streamlit_local_storage import LocalStorage
from streamlit_autorefresh import st_autorefresh

# --- 1. OPTIMIERTE PARSER KLASSE ---
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
                line_s = line_s.replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- 2. POPUP DIALOG FUNKTION ---
@st.dialog("Norm-Vorschau")
def show_law_popup(num, law, prefix):
    mapping = {
        "BGB": "bgb", "GG": "gg", "STGB": "stgb", "ZPO": "zpo", 
        "VWGOP": "vwgo", "VWVFG": "vwvfg", "STPO": "stpo", "HGB": "hgb"
    }
    law_code = mapping.get(law.upper(), law.lower())
    full_ref = f"{prefix} {num} {law}"
    
    url_prefix = "art" if "Art" in prefix or law.upper() == "GG" else "__"
    clean_num = re.sub(r'[^0-9a-z]', '', num.lower())
    url = f"https://www.gesetze-im-internet.de/{law_code}/{url_prefix}_{clean_num}.html"
    
    st.subheader(full_ref)
    st.text_input("Zitation kopieren:", value=full_ref)
    st.link_button("🌐 Auf gesetze-im-internet.de öffnen", url, use_container_width=True)
    st.divider()
    st.caption("Nutze Strg+C im Textfeld oben, um die Norm schnell zu kopieren.")

# --- 3. UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

# --- 4. MAIN APP ---
def main():
    ls = LocalStorage() 
    doc_parser = KlausurDocument()
    
    def reset_gutachten():
        st.session_state["main_editor_key"] = ""
        st.session_state["stamm_titel"] = ""
        st.session_state["stamm_datum"] = ""
        st.session_state["stamm_kuerzel"] = ""
        try:
            ls.removeItem("iustwrite_backup")
            ls.removeItem("iustwrite_titel")
            ls.removeItem("iustwrite_datum")
            ls.removeItem("iustwrite_kuerzel")
        except: pass
        st.toast("Neues Gutachten gestartet.")

    if "initialized" not in st.session_state:
        try:
            st.session_state["main_editor_key"] = ls.getItem("iustwrite_backup") or ""
            st.session_state["stamm_titel"] = ls.getItem("iustwrite_titel") or ""
            st.session_state["stamm_datum"] = ls.getItem("iustwrite_datum") or ""
            st.session_state["stamm_kuerzel"] = ls.getItem("iustwrite_kuerzel") or ""
        except:
            st.session_state["main_editor_key"] = ""
            for k in ["stamm_titel", "stamm_datum", "stamm_kuerzel"]:
                if k not in st.session_state: st.session_state[k] = ""
        st.session_state["initialized"] = True

    st_autorefresh(interval=30000, key="autosave_heartbeat")
    
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; max-width: 98% !important; }
        [data-testid="stSidebar"] .stMarkdown { margin-bottom: -18px; }
        .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 1.1rem; line-height: 1.5; padding: 15px; }
        .sachverhalt-box { background-color: #f0f2f6; padding: 20px; border-radius: 8px; border-left: 6px solid #4682B4; margin-bottom: 25px; }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR OBEN ---
    st.sidebar.button("🗑️ Neues Gutachten", on_click=reset_gutachten, use_container_width=True)
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("⚙️ Layout-Einstellungen", expanded=False):
        rand_in = st.text_input("Korrekturrand rechts (cm)", value="6")
        rand_wert = f"{rand_in}cm" if "cm" not in rand_in else rand_in
        zeilenabstand = st.selectbox("Zeilenabstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)
        font_options = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
        font_choice = st.selectbox("Schriftart", options=list(font_options.keys()), index=0)
        selected_font_package = font_options[font_choice]

    with st.sidebar.expander("📖 Fall abrufen", expanded=False):
        fall_code = st.text_input("Fall-Code eingeben")
        if fall_code:
            pfad_zu_fall = os.path.join("fealle", f"{fall_code}.txt")
            if os.path.exists(pfad_zu_fall):
                with open(pfad_zu_fall, "r", encoding="utf-8") as f:
                    ganzer_text = f.read()
                zeilen = ganzer_text.split('\n')
                sauberer_titel = re.sub(r'^#+\s*(Fall\s+\d+:\s*)?', '', zeilen[0]).strip()
                st.info(f"Fall geladen: {sauberer_titel}")
            else:
                st.sidebar.error("Fall nicht gefunden.")

    # --- EDITOR (Wichtig: Vor der Normen-Logik!) ---
    c1, c2, c3 = st.columns([3, 1, 1])
    kl_titel = c1.text_input("Titel", key="stamm_titel")
    kl_datum = c2.text_input("Datum", key="stamm_datum")
    kl_kuerzel = c3.text_input("Kürzel", key="stamm_kuerzel")

    current_text = st.text_area("", height=600, key="main_editor_key")

    # --- NORMEN-LOGIK IN DER SIDEBAR ---
    if current_text:
        found_norms = re.findall(r'(§+|Art\.)\s*(\d+[a-z]?)\s*([A-Z]{2,5})', current_text)
        if found_norms:
            st.sidebar.markdown("---")
            st.sidebar.caption("🔗 Erkannte Normen")
            seen_norms = set()
            cols = st.sidebar.columns(3)
            col_idx = 0
            for prefix, num, law in found_norms:
                ref_label = f"{num} {law}"
                u_id = f"sb_{prefix}_{num}_{law}".replace(" ", "").replace(".", "").replace("§", "p")
                if u_id not in seen_norms:
                    if cols[col_idx % 3].button(ref_label, key=u_id, use_container_width=True):
                        show_law_popup(num, law, prefix)
                    seen_norms.add(u_id)
                    col_idx += 1

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # --- SIDEBAR OUTLINE GENERIERUNG ---
    if current_text:
        for line in current_text.split('\n'):
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
                        weight = "**" if level <= 2 else ""
                        st.sidebar.markdown(f"{'&nbsp;' * (level * 2)}{weight}{line_s}{weight}")
                        break

    # --- ACTIONS & EXPORT ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sachverhalt = st.columns([1, 1, 1, 1])

    t_clean = (kl_titel or "Gutachten").replace(" ", "_")
    d_clean = (kl_datum or "Datum").replace(" ", "_")
    k_clean = (kl_kuerzel or "Kuerzel").replace(" ", "_")
    dateiname_basis = f"{t_clean}_{d_clean}_{k_clean}"

    # PDF Generierung
    if col_pdf.button("🏁 PDF generieren", use_container_width=True):
        if not current_text.strip(): st.warning("Bitte Text eingeben!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            if not os.path.exists(cls_path): st.error("jurabook.cls fehlt!"); st.stop()
            with st.spinner("Erstelle PDF..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                font_latex = f"\\usepackage{{{selected_font_package}}}"
                if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"
                
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\usepackage{xcolor}
\definecolor{myRed}{RGB}{190, 20, 20}
\definecolor{myBlue}{RGB}{0, 80, 160}
\definecolor{myGreen}{RGB}{0, 120, 50}
\newcommand{\red}[1]{{\color{myRed}#1}}
\newcommand{\blue}[1]{{\color{myBlue}#1}}
\newcommand{\green}[1]{{\color{myGreen}#1}}
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
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_p = Path(tmpdirname)
                    shutil.copy(cls_path, tmp_p / "jurabook.cls")
                    with open(tmp_p / "klausur.tex", "w", encoding="utf-8") as f: f.write(full_latex)
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname, capture_output=True)
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdirname, capture_output=True)
                    if (tmp_p / "klausur.pdf").exists():
                        st.success("PDF fertig!")
                        with open(tmp_p / "klausur.pdf", "rb") as f:
                            st.download_button("📥 Download PDF", f, file_name=f"{dateiname_basis}.pdf", use_container_width=True)

    # TXT Download
    col_save.download_button("💾 Als TXT speichern", current_text, file_name=f"{dateiname_basis}.txt", use_container_width=True)
    
    # Datei laden
    col_load.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

    # Backup im LocalStorage
    if current_text:
        try:
            ls.setItem("iustwrite_backup", current_text)
            ls.setItem("iustwrite_titel", kl_titel)
            ls.setItem("iustwrite_datum", kl_datum)
            ls.setItem("iustwrite_kuerzel", kl_kuerzel)
        except: pass

if __name__ == "__main__":
    main()
