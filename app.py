import streamlit as st
import subprocess
import os
import re

# --- KONFIGURATION & STYLING ---
st.set_page_config(page_title="Jura Klausur-Editor", layout="wide")

# CSS für eine schönere Sidebar und Editor
st.markdown("""
    <style>
    .stTextArea textarea {
        font-family: 'Courier New', Courier, monospace;
        font-size: 14px;
    }
    .gliederung-item {
        font-size: 14px;
        line-height: 1.5;
        color: #31333F;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DEIN PARSER (VON LEXGERM.DE ÜBERNOMMEN) ---
def parse_to_latex(text):
    lines = text.split('\n')
    latex_lines = []
    
    # Muster für Überschriften (A., I., 1., a), aa))
    patterns = {
        'haupt': r'^[A-Z]\.\s.*',          # A.
        'römisch': r'^[IVX]+\.\s.*',       # I.
        'arabisch': r'^[0-9]+\.\s.*',      # 1.
        'klein_buchstabe': r'^[a-z]\)\s.*', # a)
        'klein_doppel': r'^[a-z][a-z]\)\s.*'# aa)
    }

    for line in lines:
        line = line.strip()
        if not line:
            latex_lines.append("\\medskip")
            continue

        # Überschriften-Erkennung & LaTeX-Umwandlung
        if re.match(patterns['haupt'], line):
            latex_lines.append(f"\\subsection*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{subsection}}{{{line}}}")
        elif re.match(patterns['römisch'], line):
            latex_lines.append(f"\\subsubsection*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{subsubsection}}{{{line}}}")
        elif re.match(patterns['arabisch'], line):
            latex_lines.append(f"\\paragraph*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{paragraph}}{{{line}}}")
        elif re.match(patterns['klein_buchstabe'], line) or re.match(patterns['klein_doppel'], line):
            latex_lines.append(f"\\subparagraph*{{{line}}}")
            latex_lines.append(f"\\addcontentsline{{toc}}{{subparagraph}}{{{line}}}")
        else:
            # Normaler Text mit automatischer Kursivsetzung für Paragraphen (optional)
            processed_line = line.replace('§', '\\S~')
            latex_lines.append(processed_line)

    return "\n".join(latex_lines)

# --- HAUPTPROGRAMM ---
def main():
    st.sidebar.title("📌 Gliederung")
    
    # Eingabefeld
    st.subheader("Klausur-Editor")
    user_input = st.text_area(
        "Tippe hier dein Gutachten. Nutze 'A. ', 'I. ', '1. ' für Überschriften.",
        height=500,
        placeholder="A. Zulässigkeit\nDer Antrag ist zulässig...",
        key="main_editor"
    )

    # Sidebar Gliederung (Live-Vorschau)
    if user_input:
        lines = user_input.split('\n')
        for line in lines:
            line = line.strip()
            # Prüfen auf Überschriften für die Sidebar
            if re.match(r'^[A-Z]\..*', line):
                st.sidebar.markdown(f"**{line}**")
            elif re.match(r'^[IVX]+\..*', line):
                st.sidebar.markdown(f"&nbsp;&nbsp;{line}")
            elif re.match(r'^[0-9]+\..*', line):
                st.sidebar.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{line}")
            elif re.match(r'^[a-z]\).*', line):
                st.sidebar.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{line}")

    # Export Button
    if st.button("🏁 Klausur als PDF generieren"):
        if not user_input:
            st.error("Bitte gib erst einen Text ein!")
            return

        with st.spinner("LaTeX wird verarbeitet..."):
            latex_body = parse_to_latex(user_input)
            
            # Deine exakte Präambel
            full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage{setspace}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{enumitem}
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

            # Datei schreiben
            with open("klausur.tex", "w", encoding="utf-8") as f:
                f.write(full_latex)

            # LaTeX Aufruf (2x für Inhaltsverzeichnis)
            try:
                subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], check=True)
                subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], check=True)
                
                if os.path.exists("klausur.pdf"):
                    with open("klausur.pdf", "rb") as pdf_file:
                        st.download_button(
                            label="📥 PDF herunterladen",
                            data=pdf_file,
                            file_name="Jura_Klausur.pdf",
                            mime="application/pdf"
                        )
                st.success("PDF erfolgreich erstellt!")
            except Exception as e:
                st.error(f"Fehler beim Kompilieren: {e}")

if __name__ == "__main__":
    main()
