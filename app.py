import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path

# --- PARSER KLASSE ---
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

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

# Initialisiere Session State
if "main_text" not in st.session_state:
    st.session_state["main_text"] = ""

# Callback-Funktion: Wird bei JEDER Änderung im Editor ausgeführt
def update_text():
    st.session_state["main_text"] = st.session_state["editor_widget"]

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_text"] = content

def main():
    doc_parser = KlausurDocument()
    
    # CSS
    st.markdown("""
        <style>
        .stats-container {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 10px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        .stat-item { text-align: center; }
        .stat-value { font-size: 1.5rem; font-weight: bold; color: #ff4b4b; }
        .stat-label { font-size: 0.8rem; color: #6c757d; text-transform: uppercase; }
        </style>
        """, unsafe_allow_html=True)

    # --- ZÄHLER GANZ OBEN ---
    txt = st.session_state["main_text"]
    w_count = len(txt.split())
    c_count = len(txt)

    st.markdown(f"""
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-label">Wörter</div>
                <div class="stat-value">{w_count}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Zeichen</div>
                <div class="stat-value">{c_count}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # --- SIDEBAR ---
    with st.sidebar.expander("⚙️ Layout", expanded=False):
        rand_wert = st.text_input("Rand (cm)", value="6")
        zeilenabstand = st.selectbox("Abstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)
        font_choice = st.selectbox("Schrift", options=["lmodern", "Times", "Palatino"], index=0)

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")
    if txt:
        for line in txt.split('\n'):
            if any(re.match(p, line.strip()) for p in {**doc_parser.prefix_patterns, **doc_parser.star_patterns}.values()):
                st.sidebar.write(line.strip())

    # --- EDITOR AREA ---
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1: kl_titel = st.text_input("Titel", "Gutachten")
    with col2: kl_datum = st.text_input("Datum", "")
    with col3: kl_kuerzel = st.text_input("Kürzel", "")

    # Der Editor nutzt jetzt den Callback 'on_change'
    st.text_area(
        "Dein Text", 
        value=st.session_state["main_text"],
        height=500, 
        key="editor_widget", 
        on_change=update_text,
        label_visibility="collapsed"
    )

    # --- BUTTONS ---
    st.markdown("---")
    c_pdf, c_save, c_load = st.columns(3)
    
    with c_pdf:
        if st.button("🏁 PDF erstellen", use_container_width=True):
            st.info("PDF-Generierung gestartet...")
            # (Hier käme deine bestehende PDF-Logik hin)

    with c_save:
        st.download_button("💾 Speichern", data=st.session_state["main_text"], file_name="klausur.txt", use_container_width=True)
    
    with c_load:
        st.file_uploader("📂 Laden", type=['txt'], key="uploader_key", on_change=handle_upload)

if __name__ == "__main__":
    main()
