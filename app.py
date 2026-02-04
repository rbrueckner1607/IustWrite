import streamlit as st
import subprocess
import os
import re
import tempfile

# --- PARSER KLASSE (DEIN ORIGINAL-CODE OPTIMIERT FÜR WEB) ---
class KlausurDocument:
    def __init__(self):
        # Muster für Zeilen, die mit der Gliederung beginnen (z.B. "A. Zulässigkeit")
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
        # Muster für Zeilen mit Sternchen-Notation (z.B. "A* Zulässigkeit")
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
        self.footnote_pattern = r'\\fn\((.*?)\)'

    def get_latex_level_command(self, level, title_text):
        """Ordnet die 8 Ebenen den LaTeX-Befehlen zu."""
        commands = {
            1: ("section", title_text),
            2: ("subsection", title_text),
            3: ("subsubsection", title_text),
            4: ("paragraph", title_text),
            5: ("subparagraph", title_text),
            6: ("subparagraph", title_text), # jurabook tiefer legen
            7: ("subparagraph", title_text),
            8: ("subparagraph", title_text)
        }
        cmd, txt = commands.get(level, ("subparagraph", title_text))
        return f"\\{cmd}*{{{txt}}}\n\\addcontentsline{{toc}}{{{cmd}}}{{{txt}}}"

    def parse_content(self, lines):
        latex_output = []
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex_output.append("\\medskip")
                continue

            # 1. Check Title Patterns (mit Sternchen)
            title_match = False
            for level, pattern in self.title_patterns.items():
                match = re.match(pattern, line_strip)
                if match:
                    title_text = match.group(2).strip() if level > 1 else match.group(0).strip()
                    latex_output.append(self.get_latex_level_command(level, title_text))
                    title_match = True
                    break
            if title_match: continue

            # 2. Check Prefix Patterns (normale Gliederung)
            prefix_match = False
            for level, pattern in self.prefix_patterns.items():
                if re.match(pattern, line_strip):
                    latex_output.append(self.get_latex_level_command(level, line_strip))
                    prefix_match = True
                    break
            if prefix_match: continue

            # 3. Check Footnotes & Normal Text
            processed_line = line_strip
            # Ersetze Fußnoten \fn(text) durch \footnote{text}
            processed_line = re.sub(self.footnote_pattern, r'\\footnote{\1}', processed_line)
            # Ersetze Paragraphenzeichen
            processed_line = processed_line.replace('§', '\\S~')
            
            latex_output.append(processed_line)
            
        return "\n".join(latex_output)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Jura Klausur-Editor", layout="wide")

def main():
    doc_parser = KlausurDocument()
    
    st.sidebar.title("📌 Gliederung")
    st.title("Jura Klausur-Editor")

    user_input = st.text_area("Gutachten hier verfassen...", height=500, key="editor")

    # Sidebar Live-Vorschau (basiert auf deinem Gliederungs-Logik)
    if user_input:
        lines = user_input.split('\n')
        for line in lines:
            line_s = line.strip()
            for level, pattern in doc_parser.prefix_patterns.items():
                if re.match(pattern, line_s):
                    indent = "&nbsp;" * (level * 4)
                    st.sidebar.markdown(f"{indent}{line_s}")
                    break

    if st.button("🏁 PDF generieren"):
        if not user_input:
            st.error("Text fehlt!")
            return

        with st.spinner("LaTeX-Kompilierung läuft..."):
            lines = user_input.split('\n')
            parsed_latex = doc_parser.parse_content(lines)

            full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{tocloft}
\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}
\setcounter{secnumdepth}{6}
\setcounter{tocdepth}{6}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[R]{\thepage}
\begin{document}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage
\setstretch{1.2}
""" + parsed_latex + r"\end{document}"

            # Speichern und pdflatex Aufruf
            with open("klausur.tex", "w", encoding="utf-8") as f:
                f.write(full_latex)

            env = os.environ.copy()
            assets_path = os.path.join(os.getcwd(), "latex_assets")
            env["TEXINPUTS"] = f".:{assets_path}:"

            try:
                for _ in range(2): # 2x für Inhaltsverzeichnis
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   env=env, check=True, capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 PDF herunterladen", f, "Klausur.pdf")
                    st.success("PDF erfolgreich erstellt!")
            except subprocess.CalledProcessError as e:
                st.error("LaTeX Fehler!")
                if os.path.exists("klausur.log"):
                    with open("klausur.log", "r", encoding="utf-8", errors="replace") as log:
                        st.code(log.read()[-2000:])

if __name__ == "__main__":
    main()
