import streamlit as st
import subprocess
import os
import re

# --- KONFIGURATION & STYLING ---
st.set_page_config(page_title="Jura Klausur-Editor", layout="wide")

st.markdown("""
    <style>
    .stTextArea textarea {
        font-family: 'Courier New', Courier, monospace;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- PARSER-LOGIK ---
def parse_to_latex(text):
    # Gefährliche LaTeX-Sonderzeichen automatisch escapen
    chars_to_escape = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '_': r'\_',
        '#': r'\#',
        '{': r'\{',
        '}': r'\}',
    }
    for char, escaped in chars_to_escape.items():
        text = text.replace(char, escaped)

    lines = text.split('\n')
    latex_lines = []
    
    # Muster für Jura-Gliederung
    patterns = {
        'haupt': r'^[A-Z]\.\s.*',          # A.
        'roemisch': r'^[IVX]+\.\s.*',       # I.
        'arabisch': r'^[0-9]+\.\s.*',      # 1.
        'klein_buchstabe': r'^[a-z]\)\s.*', # a)
        'klein_doppel': r'^[a-z][a-z]\)\s.*'# aa)
    }

    for line in lines:
        line = line.strip()
        if not line:
            latex_lines.append("\\medskip")
            continue

        if re.match(patterns['haupt'], line):
            latex_lines.append(f"\\subsection*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{subsection}}{{{line}}}")
        elif re.match(patterns['roemisch'], line):
            latex_lines.append(f"\\subsubsection*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{subsubsection}}{{{line}}}")
        elif re.match(patterns['arabisch'], line):
            latex_lines.append(f"\\paragraph*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{paragraph}}{{{line}}}")
        elif re.match(patterns['klein_buchstabe'], line) or re.match(patterns['klein_doppel'], line):
            latex_lines.append(f"\\subparagraph*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{subparagraph}}{{{line}}}")
        else:
            line = line.replace('§', '\\S~')
            latex_lines.append(line)

    return "\n".join(latex_lines)

# --- HAUPTPROGRAMM ---
def main():
    st.sidebar.title("📌 Gliederung")
    st.title("Jura Klausur-Editor")
    
    user_input = st.text_area(
        "Schreibe hier dein Gutachten...",
        height=500,
        placeholder="A. Zulässigkeit\nI. Zuständigkeit...",
        key="main_editor"
    )

    # Sidebar Live-Gliederung
    if user_input:
        for line in user_input.split('\n'):
            line = line.strip()
            if re.match(r'^[A-Z]\..*', line):
                st.sidebar.markdown(f"**{line}**")
            elif re.match(r'^[IVX]+\..*', line):
                st.sidebar.markdown(f"&nbsp;&nbsp;{line}")
            elif re.match(r'^[0-9]+\..*', line):
                st.sidebar.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{line}")

    if st.button("🏁 PDF generieren"):
        if not user_input:
            st.warning("Bitte gib Text ein.")
            return

        with st.spinner("Erstelle PDF..."):
            latex_body = parse_to_latex(user_input)
            
            # Deine Präambel
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
""" + latex_body + r"\end{document}"

            with open("klausur.tex", "w", encoding="utf-8") as f:
                f.write(full_latex)

            try:
                # Umgebungsvariablen für LaTeX setzen, damit Assets gefunden werden
                env = os.environ.copy()
                assets_path = os.path.join(os.getcwd(), "latex_assets")
                # TEXINPUTS: . (aktuell), assets_path, und dann Standardpfade (:)
                env["TEXINPUTS"] = f".:{assets_path}:"

                # LaTeX Durchläufe (zweimal für Inhaltsverzeichnis)
                for _ in range(2):
                    result = subprocess.run(
                        ["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                        check=True, capture_output=True, env=env
                    )
                
                if os.path.exists("klausur.pdf"):
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 PDF herunterladen", f, "Klausur.pdf", "application/pdf")
                    st.success("PDF wurde erfolgreich erstellt!")
            except subprocess.CalledProcessError as e:
                st.error("LaTeX-Fehler beim Kompilieren!")
                # Sichereres Auslesen des Logs bei Fehlern
                if os.path.exists("klausur.log"):
                    with open("klausur.log", "r", encoding="utf-8", errors="replace") as log:
                        log_content = log.read()
                        st.code(log_content[-2000:], language="text")
                else:
                    st.write("Kein Logfile gefunden.")

if __name__ == "__main__":
    main()
