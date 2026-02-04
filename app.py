import streamlit as st
import tempfile
import os
import subprocess
import shutil
import re
from datetime import datetime

# ------------------------
# HEADING COUNTER
# ------------------------
class HeadingCounter:
    def __init__(self, max_level=13):
        self.max_level = max_level
        self.counters = [0] * max_level

    def increment(self, level):
        idx = level - 1
        self.counters[idx] += 1
        for i in range(idx + 1, self.max_level):
            self.counters[i] = 0

    def get_numbering(self, level):
        romans = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII",
                  "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI",
                  "XVII", "XVIII", "XIX", "XX"]
        def letter(n): return chr(96 + n) if 1 <= n <= 26 else str(n)
        parts = []
        for i in range(level):
            n = self.counters[i]
            if n == 0: continue
            if i == 0: parts.append(f"Teil {n}.")
            elif i == 1: parts.append(chr(64 + n) + ".")
            elif i == 2: parts.append(romans[n] + ".") if n < len(romans) else parts.append(str(n)+".")
            elif i == 3: parts.append(f"{n}.")
            elif i == 4: parts.append(f"{letter(n)})")
            elif i == 5: parts.append(f"{letter(n)*2})")
            elif i == 6: parts.append(f"({letter(n)})")
            elif i == 7: parts.append(f"({letter(n)*2})")
            else: parts.append(str(n))
        return " ".join([x for x in parts if x])

# ------------------------
# KLAUSUR DOCUMENT
# ------------------------
class KlausurDocument:
    def __init__(self):
        self.heading_counter = HeadingCounter()
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',   
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)(\s|$)',
            6: r'^\s*[a-z]{2}\)(\s|$)',
            7: r'^\s*\([a-z]\)(\s|$)',
            8: r'^\s*\([a-z]{2}\)(\s|$)'
        }
        self.title_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*\s*(.*)',
            2: r'^\s*([A-H])\*\s*(.*)',                           
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*\s*(.*)',
            4: r'^\s*(\d+)\*\s*(.*)',
            5: r'^\s*([a-z])\*\s*(.*)',
            6: r'^\s*([a-z]{2})\*\s*(.*)',
            7: r'^\s*\(([a-z])\)\*\s*(.*)',
            8: r'^\s*\(([a-z]{2})\)\*\s*(.*)'
        }
        self.footnote_pattern = r'\\fn\([^)]*\)'

    def generate_toc(self, lines):
        toc = []
        for idx, line in enumerate(lines):
            text = line.strip()
            if not text: continue
            found = False
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, text):
                    toc.append({"text": text, "level": level, "line": idx})
                    found = True
                    break
            if not found:
                for level, pattern in sorted(self.title_patterns.items()):
                    match = re.match(pattern, text)
                    if match and match.group(2).strip():
                        toc.append({"text": match.group(2).strip(), "level": level, "line": idx})
                        break
        return toc

    def to_latex(self, title, date, matrikel, lines):
        latex = [
            r"\documentclass[12pt,a4paper]{jurabook}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm,right=6cm,top=2.5cm,bottom=3cm]{geometry}",
            r"\usepackage{fancyhdr}",
            r"\usepackage{tocloft}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            r"\fancyhead[L]{" + title + r"}",
            r"\fancyfoot[R]{\thepage}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\begin{document}",
            r"\enlargethispage{40pt}",
            r"\pagenumbering{gobble}",
            r"\vspace*{-3cm}",
            r"\tableofcontents",
            r"\clearpage",
            r"\pagenumbering{arabic}",
            fr"\section*{{{title} ({date})}}"
        ]

        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append("")
                continue
            # 1. Title patterns
            title_match = False
            for level, pattern in self.title_patterns.items():
                match = re.match(pattern, line_strip)
                if match:
                    title_text = match.group(2).strip()
                    if level == 1:
                        latex.append(r"\section*{" + title_text + "}")
                        latex.append(r"\addcontentsline{toc}{section}{" + title_text + "}")
                    elif level == 2:
                        latex.append(r"\subsection*{" + title_text + "}")
                        latex.append(r"\addcontentsline{toc}{subsection}{" + title_text + "}")
                    elif level == 3:
                        latex.append(r"\subsubsection*{" + title_text + "}")
                        latex.append(r"\addcontentsline{toc}{subsubsection}{" + title_text + "}")
                    else:
                        latex.append(r"\paragraph*{" + title_text + "}")
                        latex.append(r"\addcontentsline{toc}{subparagraph}{" + title_text + "}")
                    title_match = True
                    break
            if title_match: continue

            # 2. Normal prefixes
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, line_strip):
                    if level == 1: latex.append(r"\section*{" + line_strip + "}")
                    elif level == 2: latex.append(r"\subsection*{" + line_strip + "}")
                    elif level == 3: latex.append(r"\subsubsection*{" + line_strip + "}")
                    else: latex.append(r"\paragraph*{" + line_strip + "}")
                    break
            else:
                # Fußnoten
                if re.search(self.footnote_pattern, line_strip):
                    footnote_text = re.search(self.footnote_pattern, line_strip).group(0)
                    clean_line = re.sub(self.footnote_pattern, '', line_strip).strip()
                    if clean_line: latex.append(clean_line + f"\\footnote{{{footnote_text}}}")
                    else: latex.append(f"\\footnote{{{footnote_text}}}")
                else:
                    latex.append(line_strip)

        latex.append(r"\end{document}")
        return "\n".join(latex)

    def to_pdf_bytes(self, latex_content):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "klausur.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # Assets kopieren
            assets_dir = os.path.join(tmpdir, "jura_assets")
            if os.path.exists("jura_assets"):
                shutil.copytree("jura_assets", assets_dir)

            pdflatex_bin = shutil.which("pdflatex")
            if not pdflatex_bin:
                raise FileNotFoundError("pdflatex nicht im PATH!")

            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)

            pdf_path = os.path.join(tmpdir, "klausur.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()
            raise FileNotFoundError("PDF nicht erstellt!")

# ------------------------
# STREAMLIT APP
# ------------------------
st.set_page_config(page_title="iustWrite | lexgerm.de", page_icon="⚖️", layout="wide")

st.title("⚖️ iustWrite - Jura Klausur Editor")
st.markdown("***Automatische Nummerierung • Live-Gliederung • PDF-Export***")

# Sidebar: TOC
with st.sidebar.expander("📋 Gliederung", expanded=True):
    toc_placeholder = st.empty()

# Metadaten
with st.sidebar:
    st.header("📄 Metadaten")
    title = st.text_input("Titel", value="Zivilrecht I - Klausur")
    date = st.date_input("Datum", value=datetime.now())
    matrikel = st.text_input("Matrikel-Nr.", value="12345678")
    if st.button("🆕 Neue Klausur"):
        st.session_state.clear()
        st.experimental_rerun()

# Editor
col1, col2 = st.columns([3, 2])
with col1:
    st.header("✍️ Editor")
    default_content = """Teil 1. Zulässigkeit

A. Formelle Voraussetzungen

I. Antragsbegründung"""
    content = st.text_area("Klausurinhalt", value=st.session_state.get("content", default_content),
                           height=600, key="editor")

# Live TOC
doc = KlausurDocument()
toc = doc.generate_toc(content.splitlines())
st.session_state.toc = toc
st.session_state.content = content

# Sidebar Anzeige TOC
toc_md = ""
for item in toc:
    indent = (item["level"] - 1) * 2
    toc_md += f"{'&nbsp;'*indent}• {item['text']}  \n"
toc_placeholder.markdown(toc_md, unsafe_allow_html=True)

# PDF Export
with col2:
    st.header("📄 PDF Export")
    if st.button("🎯 PDF erstellen"):
        with st.spinner("Erstelle PDF..."):
            try:
                latex = doc.to_latex(title, date.strftime("%d.%m.%Y"), matrikel, content.splitlines())
                pdf_bytes = doc.to_pdf_bytes(latex)
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_name = f"{title.replace(' ', '_')}.pdf"
                st.success("✅ PDF bereit!")
            except Exception as e:
                st.error(f"❌ {e}")

    if "pdf_bytes" in st.session_state:
        st.download_button("⬇️ PDF Download", st.session_state.pdf_bytes,
                           st.session_state.pdf_name, "application/pdf")

# Speichern / Laden
with col2:
    st.header("💾 Speichern / Laden")
    if st.button("Speichern als .txt"):
        file_name = f"{title.replace(' ', '_')}.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(f"Titel: {title}\nDatum: {date}\nMatrikel: {matrikel}\n---\n{content}")
        st.success(f"Datei {file_name} gespeichert!")

    uploaded_file = st.file_uploader("Lade .txt Datei hoch", type=["txt"])
    if uploaded_file:
        data = uploaded_file.read().decode("utf-8")
        meta, body = data.split("---", 1)
        for line i
