import subprocess
import os
import re
import streamlit as st
import webbrowser
import tempfile
import shutil
import requests
from bs4 import BeautifulSoup
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

# --- 2. HILFSFUNKTION: NORM-TEXT SCRAPEN ---
def fetch_norm_content(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        response.encoding = 'iso-8859-15' 
        soup = BeautifulSoup(response.text, 'html.parser')
        norm_body = soup.find('div', class_='jurabox')
        if norm_body:
            text = norm_body.get_text(separator='\n')
            return re.sub(r'\n\s*\n', '\n\n', text).strip()
        return "Der Text dieser Norm konnte leider nicht automatisch geladen werden."
    except Exception as e:
        return f"Fehler beim Abrufen der Norm: {e}"

# --- 3. POPUP DIALOG FUNKTION ---
@st.dialog("Norm-Vorschau", width="large")
def show_law_popup(num, law, prefix):
    mapping = {
        "BGB": "bgb", "GG": "gg", "STGB": "stgb", "ZPO": "zpo", 
        "VWGOP": "vwgo", "VWVFG": "vwvfg", "STPO": "stpo", "HGB": "hgb"
    }
    law_code = mapping.get(law.upper(), law.lower())
    full_ref = f"{prefix} {num} {law}"
    
    # URL FIX: Nur ein Unterstrich (_) für Paragrafen
    url_prefix = "art" if "Art" in prefix or law.upper() == "GG" else "_"
    clean_num = re.sub(r'[^0-9a-z]', '', num.lower())
    url = f"https://www.gesetze-im-internet.de/{law_code}/{url_prefix}_{clean_num}.html"
    
    st.subheader(full_ref)
    
    with st.spinner("Lade Wortlaut..."):
        norm_text = fetch_norm_content(url)
    
    st.text_area("Wortlaut:", value=norm_text, height=400, key="norm_display")
    st.text_input("Zitation kopieren:", value=full_ref)
    st.caption(f"Quelle: {url}")

# --- 4. UI CONFIG & MAIN ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

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
        .block-container { padding-top: 1rem; max-width: 99% !important; padding-left: 1rem; padding-right: 1rem; }
        [data-testid="stSidebar"] .stMarkdown p { font-size: 0.8rem !important; line-height: 1.2 !important; margin-bottom: 2px !important; }
        .stTextArea textarea { font-family: 'Inter', sans-serif; font-size: 1.05rem; line-height: 1.5; padding: 10px; }
        .sachverhalt-box { background-color: #f0f2f6; padding: 15px; border-radius: 8px; border-left: 6px solid #4682B4; margin-bottom: 20px; font-size: 0.9rem;}
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # Sidebar Logik
    st.sidebar.button("🗑️ Neues Gutachten", on_click=reset_gutachten, use_container_width=True)
    st.sidebar.markdown("---")
    
    rand_wert, zeilenabstand, selected_font_package = "6cm", "1.5", "lmodern"

    with st.sidebar.expander("⚙️ Layout-Einstellungen"):
        rand_in = st.text_input("Korrekturrand rechts (cm)", value="6")
        rand_wert = f"{rand_in}cm" if "cm" not in rand_in else rand_in
        zeilenabstand = st.selectbox("Zeilenabstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)
        font_options = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
        font_choice = st.selectbox("Schriftart", options=list(font_options.keys()), index=0)
        selected_font_package = font_options[font_choice]

    with st.sidebar.expander("📖 Fall abrufen"):
        fall_code = st.text_input("Fall-Code")
        if fall_code:
            pfad = os.path.join("fealle", f"{fall_code}.txt")
            if os.path.exists(pfad):
                with open(pfad, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                st.markdown(f'<div class="sachverhalt-box">{"".join(lines)}</div>', unsafe_allow_html=True)

    # Editor Bereich
    c1, c2, c3 = st.columns([3, 1, 1])
    kl_titel = c1.text_input("Titel", key="stamm_titel")
    kl_datum = c2.text_input("Datum", key="stamm_datum")
    kl_kuerzel = c3.text_input("Kürzel", key="stamm_kuerzel")

    current_text = st.text_area("", height=600, key="main_editor_key")

    # Normen in Sidebar
    if current_text:
        found_norms = re.findall(r'(§+|Art\.)\s*(\d+[a-z]?)\s*([A-Z]{2,5})', current_text)
        if found_norms:
            st.sidebar.markdown("---")
            st.sidebar.caption("🔗 Erkannte Normen")
            seen = set()
            cols = st.sidebar.columns(3)
            col_idx = 0
            for prefix, num, law in found_norms:
                ref = f"{num} {law}"
                u_id = f"sb_{prefix}_{num}_{law}".replace(" ", "").replace(".", "").replace("§", "p")
                if u_id not in seen:
                    if cols[col_idx % 3].button(ref, key=u_id, use_container_width=True):
                        show_law_popup(num, law, prefix)
                    seen.add(u_id); col_idx += 1

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # Gliederung in Sidebar (Klein)
    if current_text:
        with st.sidebar:
            for line in current_text.split('\n'):
                line_s = line.strip()
                if not line_s: continue
                found = False
                for level, pattern in doc_parser.star_patterns.items():
                    if re.match(pattern, line_s):
                        st.markdown(f"{'&nbsp;' * (level * 2)}{line_s}")
                        found = True; break
                if not found:
                    for level, pattern in doc_parser.prefix_patterns.items():
                        if re.match(pattern, line_s):
                            weight = "**" if level <= 2 else ""
                            st.markdown(f"{'&nbsp;' * (level * 2)}{weight}{line_s}{weight}")
                            break

    # Export & Actions
    st.markdown("---")
    col_pdf, col_save, col_load, _ = st.columns([1, 1, 1, 1])

    t_clean = (kl_titel or "Gutachten").replace(" ", "_")
    d_clean = (kl_datum or "Datum").replace(" ", "_")
    k_clean = (kl_kuerzel or "Kuerzel").replace(" ", "_")
    dateiname = f"{t_clean}_{d_clean}_{k_clean}"

    if col_pdf.button("🏁 PDF generieren", use_container_width=True):
        if current_text.strip():
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            if os.path.exists(cls_path):
                with st.spinner("PDF wird erstellt..."):
                    parsed = doc_parser.parse_content(current_text.split('\n'))
                    titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                    font_latex = f"\\usepackage{{{selected_font_package}}}"
                    if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"
                    
                    full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{pdfpages}
\usepackage[hidelinks]{hyperref}\usepackage{xurl}\usepackage{xcolor}
\definecolor{myRed}{RGB}{190, 20, 20}\definecolor{myBlue}{RGB}{0, 80, 160}\definecolor{myGreen}{RGB}{0, 120, 50}
\newcommand{\red}[1]{{\color{myRed}#1}}\newcommand{\blue}[1]{{\color{myBlue}#1}}\newcommand{\green}[1]{{\color{myGreen}#1}}
\addto\captionsngerman{\renewcommand{\contentsname}{Gliederung}}
""" + font_latex + r"""\usepackage{setspace}\usepackage{geometry}\usepackage{fancyhdr}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}\setcounter{tocdepth}{8}\setcounter{secnumdepth}{8}\setlength{\parindent}{0pt}
\fancypagestyle{iustwrite}{\fancyhf{}\fancyhead[L]{\small """ + kl_kuerzel + r"""}\fancyhead[R]{\small """ + titel_komp + r"""}\fancyfoot[R]{\thepage}\renewcommand{\headrulewidth}{0.5pt}}
\begin{document}\sloppy\pagenumbering{gobble}\tableofcontents\clearpage\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}\setcounter{page}{1}\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed + r"\end{document}"

                    with tempfile.TemporaryDirectory() as tmp:
                        tmp_p = Path(tmp)
                        shutil.copy(cls_path, tmp_p / "jurabook.cls")
                        (tmp_p / "klausur.tex").write_text(full_latex, encoding="utf-8")
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmp, capture_output=True)
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], cwd=tmp, capture_output=True)
                        if (tmp_p / "klausur.pdf").exists():
                            st.download_button("📥 Download PDF", (tmp_p / "klausur.pdf").read_bytes(), file_name=f"{dateiname}.pdf", use_container_width=True)

    col_save.download_button("💾 Als TXT speichern", current_text, file_name=f"{dateiname}.txt", use_container_width=True)
    col_load.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

    if current_text:
        try:
            ls.setItem("iustwrite_backup", current_text)
            ls.setItem("iustwrite_titel", kl_titel)
            ls.setItem("iustwrite_datum", kl_datum)
            ls.setItem("iustwrite_kuerzel", kl_kuerzel)
        except: pass

if __name__ == "__main__":
    main()
