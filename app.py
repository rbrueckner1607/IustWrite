import streamlit as st
import tempfile
import os
import subprocess
import re
from datetime import datetime
import io

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DEINE LOGIK-KLASSEN (Optimiert für Streamlit)
# ═══════════════════════════════════════════════════════════════════════════════

class HeadingCounter:
    def __init__(self, max_level=13):
        self.max_level = max_level
        self.counters = [0] * max_level

    def increment(self, level):
        idx = level - 1
        if idx < self.max_level:
            self.counters[idx] += 1
            for i in range(idx + 1, self.max_level):
                self.counters[i] = 0

    def get_numbering(self, level):
        romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV"]
        def letter(n): return chr(96 + n) if 1 <= n <= 26 else str(n)
        parts = []
        for i in range(level):
            n = self.counters[i]
            if n == 0: continue
            if i == 0: parts.append(f"Teil {n}.")
            elif i == 1: parts.append(chr(64 + n) + ".")
            elif i == 2: parts.append(romans[n] + "." if n < len(romans) else str(n) + ".")
            elif i == 3: parts.append(f"{n}.")
            elif i == 4: parts.append(f"{letter(n)})")
            elif i == 5: parts.append(f"{letter(n)*2})")
            elif i == 6: parts.append(f"({letter(n)})")
        return " ".join([x for x in parts if x])

class KlausurDocument:
    def __init__(self):
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',   
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)(\s|$)'
        }
        
    def generate_toc(self, text):
        toc = []
        counter = HeadingCounter()
        for line in text.split('\n'):
            line_strip = line.strip()
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, line_strip):
                    counter.increment(level)
                    indent = "&nbsp;" * (level * 4)
                    toc.append(f"{indent}**{counter.get_numbering(level)}** {line_strip}")
                    break
        return toc

    def to_latex(self, title, date, matrikel, content):
        # 6cm Korrekturrand rechts gemäß deiner Anforderung
        latex = [
            r"\documentclass[12pt, a4paper]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm, right=6cm, top=2.5cm, bottom=3cm]{geometry}",
            r"\usepackage{setspace}",
            r"\onehalfspacing",
            r"\begin{document}",
            fr"\section*{{{title}}}",
            fr"\noindent Datum: {date} \hfill Matrikel-Nr.: {matrikel}",
            r"\vfill",
            r"\tableofcontents",
            r"\newpage",
            content.replace("\n", "\n\n"),
            r"\end{document}"
        ]
        return "\n".join(latex)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. STREAMLIT FRONTEND
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="LexGerm Editor", layout="wide")

# Styling für die Sidebar Gliederung
st.markdown("""<style> .stTextArea textarea { font-family: 'Courier New', monospace; } </style>""", unsafe_allow_html=True)

st.title("👨‍⚖️ LexGerm | iustWrite Editor")

with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel der Klausur", "Zivilrechtliche Übung")
    date = st.date_input("Datum", datetime.now())
    matrikel = st.text_input("Matrikel-Nummer", "123456")
    st.divider()
    st.header("📋 Live-Gliederung")
    
# Editor Layout
col_editor, col_spacer = st.columns([4, 1])

with col_editor:
    content = st.text_area("Schreibe hier dein Gutachten (Nutze A., I., 1. für Überschriften)", 
                          height=600, key="editor_input")

# Logik für Gliederung in Sidebar
doc = KlausurDocument()
toc_items = doc.generate_toc(content)
with st.sidebar:
    for item in toc_items:
        st.markdown(item, unsafe_allow_html=True)

# PDF Export Prozess
if st.button("🎯 PDF generieren"):
    if content:
        with st.spinner("LaTeX wird kompiliert..."):
            latex_code = doc.to_latex(title, str(date), matrikel, content)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                tex_path = os.path.join(tmpdir, "klausur.tex")
                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(latex_code)
                
                # WICHTIG: Auf dem Server rufen wir einfach "pdflatex" auf
                try:
                    process = subprocess.run(
                        ["pdflatex", "-interaction=nonstopmode", "klausur.tex"],
                        cwd=tmpdir, capture_output=True, text=True
                    )
                    
                    pdf_path = os.path.join(tmpdir, "klausur.pdf")
                    if os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                "⬇️ Datei herunterladen",
                                data=f.read(),
                                file_name=f"Klausur_{title}.pdf",
                                mime="application/pdf"
                            )
                        st.success("✅ PDF erfolgreich erstellt!")
                    else:
                        st.error("LaTeX Fehler: PDF wurde nicht generiert.")
                        st.code(process.stdout[:500]) # Zeige erste Fehlerzeilen
                except Exception as e:
                    st.error(f"Systemfehler: {e}")
    else:
        st.warning("Dein Editor ist noch leer!")
