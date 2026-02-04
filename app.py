import streamlit as st
from streamlit_ace import st_ace
import os, subprocess, tempfile, shutil, re

# ═══════════════════════════════════════════════════════════════════════════════
# 1. JURA-LOGIK & PARSER (8 Ebenen)
# ═══════════════════════════════════════════════════════════════════════════════

class KlausurDocument:
    def __init__(self):
        # Erkennt deine Sternchen-Titel (A*, I* etc.)
        self.patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*',
            2: r'^\s*[A-H]\*',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\*',
            4: r'^\s*\d+\*',
            5: r'^\s*[a-z]\)',
            6: r'^\s*[a-z]{2}\)',
            7: r'^\s*\([a-z]\)',
            8: r'^\s*\([a-z]{2}\)'
        }

    def get_toc(self, text):
        toc = []
        lines = text.split('\n')
        for idx, line in enumerate(lines):
            clean = line.strip()
            for level, pattern in self.patterns.items():
                if re.match(pattern, clean):
                    toc.append({"level": level, "text": clean, "line": idx + 1})
                    break
        return toc

# ═══════════════════════════════════════════════════════════════════════════════
# 2. WEB-INTERFACE (DASHBOARD-LOOK)
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="LexGerm iustWrite PRO", layout="wide")

# Sidebar für Gliederung & Metadaten
with st.sidebar:
    st.title("⚖️ LexGerm")
    titel = st.text_input("Klausurtitel", value="Zivilrechtliche Klausur")
    
    st.divider()
    
    # SPEICHERN & LADEN (.txt Dateien)
    st.subheader("💾 Projekt")
    uploaded = st.file_uploader("Lade .txt Datei", type="txt")
    if uploaded:
        st.session_state.content = uploaded.read().decode("utf-8")
    
    # GLIEDERUNG MIT SPRUNG-FUNKTION
    st.subheader("📋 Gliederung")
    doc = KlausurDocument()
    current_content = st.session_state.get("content", "")
    toc_data = doc.get_toc(current_content)
    
    for item in toc_data:
        indent = "&nbsp;" * (item["level"] * 2)
        # Button simuliert den Sprung zur Zeile
        if st.button(f"{indent}{item['text']}", key=f"btn_{item['line']}"):
            st.info(f"Gehe zu Zeile {item['line']} (Nutze die Suche im Editor)")

# HAUPTBEREICH: EDITOR
st.subheader(f"Editor: {titel}")

# Der Profi-Editor (Ace) mit Zeilennummern und Highlighting
content = st_ace(
    value=st.session_state.get("content", ""),
    placeholder="Schreibe dein Gutachten... Nutze A* für Überschriften.",
    height=650,
    language="latex", # Syntax-Highlighting für bessere Lesbarkeit
    theme="chrome",
    font_size=16,
    wrap=True,
    auto_update=True,
    key="jura_editor"
)
st.session_state.content = content

# ═══════════════════════════════════════════════════════════════════════════════
# 3. PDF EXPORT (MIT ASSETS & JURABASE)
# ═══════════════════════════════════════════════════════════════════════════════

if st.button("🚀 PDF GENERIEREN (mit 6cm Rand)"):
    if content:
        with st.spinner("Kompiliere mit jurabase.cls..."):
            with tempfile.TemporaryDirectory() as tmpdir:
                # KOPIERE DEINE LOKALEN ASSETS (CLS-DATEIEN) IN DEN TEMP-ORDNER
                asset_folder = "latex_assets"
                if os.path.exists(asset_folder):
                    for filename in os.listdir(asset_folder):
                        shutil.copy(os.path.join(asset_folder, filename), tmpdir)
                
                # ERSTELLE DIE LATEX DATEI
                tex_path = os.path.join(tmpdir, "klausur.tex")
                # Hier nutzt du deinen speziellen Header!
                latex_final = r"\documentclass{jurabase}" + "\n"
                latex_final += r"\usepackage[ngerman]{babel}" + "\n"
                latex_final += r"\begin{document}" + "\n"
                latex_final += r"\tableofcontents\newpage" + "\n"
                latex_final += content.replace("\n", "\n\n")
                latex_final += r"\end{document}"

                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(latex_final)
                
                # 2x Kompilieren
                pdflatex = shutil.which("pdflatex")
                for _ in range(2):
                    subprocess.run([pdflatex, "-interaction=nonstopmode", "klausur.tex"], cwd=tmpdir)
                
                pdf_path = os.path.join(tmpdir, "klausur.pdf")
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button("⬇️ PDF Herunterladen", f, file_name=f"{titel}.pdf")
                    st.success("Erfolgreich erstellt!")
                else:
                    st.error("LaTeX Fehler. Prüfe die Logs.")
