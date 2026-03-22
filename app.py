import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path
from streamlit_local_storage import LocalStorage
from streamlit_autorefresh import st_autorefresh

# --- OPTIMIERTE PARSER KLASSE ---
class KlausurDocument:
    def main():
    # --- INITIALISIERUNG & AUTO-SAVE ---
    ls = LocalStorage()                                # <-- NEU
    doc_parser = KlausurDocument()
    
    # Taktgeber für das automatische Speichern (30 Sek.)
    st_autorefresh(interval=30000, key="autosave_heartbeat") # <-- NEU

    # Lädt das Backup aus dem Browser, falls vorhanden
    if "main_editor_key" not in st.session_state or st.session_state["main_editor_key"] == "":
        try:
            stored = ls.getItem("iustwrite_backup")
            if stored:
                st.session_state["main_editor_key"] = stored
        except:
            pass
            
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
            # --- 1. BLOCK: Verarbeitung der Sternchen-Überschriften (Versteckte Gliederung) ---
            for level, pattern in self.star_patterns.items():
                match = re.match(pattern, line_s)
                if match:
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*"}
                    cmd = cmds.get(level, "subsubsection*")
                    
                    # Hier wird der Marker (z.B. "Teil 1*") abgeschnitten
                    display_text = line_s[match.end():].strip()
                    
                    # Falls kein Text nach dem Sternchen folgt, nimm die Zeile ohne Stern
                    if not display_text:
                        display_text = line_s.replace('*', '').strip()
                        
                    latex_output.append(f"\\{cmd}{{{display_text}}}")
                    found_level = True
                    break

            # --- 2. BLOCK: Verarbeitung der normalen Überschriften (In Gliederung) ---
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
    
    # CSS für maximale Breite, bewegliche Sidebar und LESERLICHE Schrift
    st.markdown("""
        <style>
        .block-container { 
            padding-top: 1.5rem; 
            padding-left: 2rem; 
            padding-right: 2rem; 
            max-width: 98% !important; 
        }
        [data-testid="stSidebar"] .stMarkdown { margin-bottom: -18px; }
        [data-testid="stSidebar"] p { font-size: 0.85rem !important; line-height: 1.2 !important; }
        
        /* UPDATE: Bearbeiterfreundliche, moderne Schriftart für den Editor */
        .stTextArea textarea { 
            font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif; 
            font-size: 1.1rem;
            line-height: 1.5;
            padding: 15px;
            color: #1e1e1e;
        }
        
        .sachverhalt-box {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 8px;
            border-left: 6px solid #4682B4;
            margin-bottom: 25px;
            line-height: 1.6;
            font-size: 1rem;
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

   # --- SIDEBAR SETTINGS (EINGEKLAPPT) ---

    # 1. DER "NEU"-BUTTON
    if st.sidebar.button("🗑️ Neues Gutachten", use_container_width=True, help="Löscht den aktuellen Text im Editor und im Browser-Backup."):
        # Alles hier drunter muss 4 Leerzeichen weiter rechts stehen als das 'if'
        st.session_state["main_editor_key"] = ""
        try:
            ls.removeItem("iustwrite_backup")
        except:
            pass
        st.rerun()

    # 2. TRENNLINIE UND BESTEHENDE EINSTELLUNGEN
    # Diese Zeile muss wieder auf derselben Ebene wie das 'if' stehen
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("⚙️ Layout-Einstellungen", expanded=False):
        rand_wert = st.text_input("Korrekturrand rechts (in cm)", value="6")
        if not any(unit in rand_wert for unit in ['cm', 'mm']): 
            rand_wert += "cm"
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
        else:
            st.sidebar.error(f"Fall {fall_code} nicht gefunden.")

    # --- EDITOR AREA ---
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "")

    # Das Editorfenster nutzt nun die neue CSS-Klasse
    current_text = st.text_area(
        "", 
        value=st.session_state["main_editor_key"],
        height=600, 
        key="main_editor_widget"
    )

    # DIESER BLOCK SPEICHERT AUTOMATISCH:
    if current_text != st.session_state["main_editor_key"]:
        st.session_state["main_editor_key"] = current_text
        try:
            ls.setItem("iustwrite_backup", current_text)
        except:
            pass

    # --- NEU: ZEICHENZÄHLER ---
    if current_text:
        char_count = len(current_text)
        word_count = len(current_text.split())
        # Anzeige direkt unter dem Editor
        st.markdown(f"*📝 {char_count} Zeichen | {word_count} Wörter*")

    # --- SIDEBAR OUTLINE ---
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            found = False
            for level, pattern in doc_parser.star_patterns.items():
                if re.match(pattern, line_s):
                    indent = "&nbsp;" * (level * 2)
                    st.sidebar.markdown(f"{indent}{line_s}")
                    found = True
                    break
            if not found:
                for level, pattern in doc_parser.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        indent = "&nbsp;" * (level * 2)
                        weight = "**" if level <= 2 else ""
                        st.sidebar.markdown(f"{indent}{weight}{line_s}{weight}")
                        break

    # --- ACTIONS ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sachverhalt = st.columns([1, 1, 1, 1])

    # 1. Dateiname VORAB zentral definieren (verhindert NameError)
    t_clean = (kl_titel or "Gutachten").replace(" ", "_")
    d_clean = (kl_datum or "Datum").replace(" ", "_")
    k_clean = (kl_kuerzel or "Kuerzel").replace(" ", "_")
    dateiname_basis = f"{t_clean}_{d_clean}_{k_clean}"

    with col_pdf: 
        pdf_button = st.button("🏁 PDF generieren", use_container_width=True)

    with col_save:
        # TXT-Button
        st.download_button(
            label="💾 Als TXT speichern", 
            data=current_text, 
            file_name=f"{dateiname_basis}.txt", 
            use_container_width=True
        )

        # TEX-Button (Direkt darunter in derselben Spalte)
        # Wir bereiten den Inhalt vor
        parsed_content = doc_parser.parse_content(current_text.split('\n'))
        titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
        
        font_latex = f"\\usepackage{{{selected_font_package}}}"
        if "helvet" in selected_font_package: 
            font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

        full_tex_code = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
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
""" + parsed_content + r"""
\end{document}"""

        st.download_button(
            label="📄 Als TEX speichern",
            data=full_tex_code,
            file_name=f"{dateiname_basis}.tex",
            mime="text/x-tex",
            use_container_width=True
        )

    with col_load: 
        st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

    with col_sachverhalt: 
        sachverhalt_file = st.file_uploader("📄 Sachverhalt beifügen (PDF)", type=['pdf'], key="sachverhalt_key")

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
                if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                full_latex_header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\usepackage{xcolor}

% --- Textfarben mir Alias ---
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
    \fancyhfoffset[R]{0pt}
}
\begin{document}
\sloppy
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
                    if sachverhalt_file is not None:
                        with open(tmp_path / "temp_sv.pdf", "wb") as f:
                            f.write(sachverhalt_file.getbuffer())
                        sachverhalt_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = full_latex_header + sachverhalt_cmd + r"""
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(final_latex)
                    
                    env = os.environ.copy()
                    env["TEXINPUTS"] = f".:{tmp_path}:{assets_folder}:"

                    result = None
                    for _ in range(2):
                        result = subprocess.run(
                            ["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                            cwd=tmpdirname, env=env, capture_output=True, text=False
                        )

                    pdf_file = tmp_path / "klausur.pdf"
                    if pdf_file.exists():
                        st.success("PDF erfolgreich erstellt!")
                        with open(pdf_file, "rb") as f:
                            # Namen für das PDF nach dem gleichen Schema generieren
                            t_pdf = (kl_titel or "Gutachten").replace(" ", "_")
                            d_pdf = (kl_datum or "Datum").replace(" ", "_")
                            k_pdf = (kl_kuerzel or "Kuerzel").replace(" ", "_")
                            
                            pdf_name = f"{t_pdf}_{d_pdf}_{k_pdf}.pdf"
                            
                            st.download_button(
                                label="📥 Download PDF", 
                                data=f, 
                                file_name=pdf_name, 
                                use_container_width=True
                            )
                    else:
                        st.error("LaTeX Fehler!")
                        if result:
                            error_log = result.stdout.decode('utf-8', errors='replace')
                            st.code(error_log)

if __name__ == "__main__":
    main()
