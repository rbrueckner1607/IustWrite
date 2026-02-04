import streamlit as st
import subprocess
import os
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Jura Klausur-Editor", layout="wide")

# --- PARSER-LOGIK ---
def parse_to_latex(text):
    chars_to_escape = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '_': r'\_',
        '#': r'\#',
    }
    
    # Bekannte LaTeX-Befehle, die NICHT escapet werden sollen
    valid_commands = ['vspace', 'hspace', 'textit', 'textbf', 'underline', 'newpage', 'bigskip', 'medskip', 'S~']

    lines = text.split('\n')
    latex_lines = []
    
    patterns = {
        'haupt': r'^[A-Z]\.\s.*',
        'roemisch': r'^[IVX]+\.\s.*',
        'arabisch': r'^[0-9]+\.\s.*',
        'klein_buchstabe': r'^[a-z]\)\s.*',
        'klein_doppel': r'^[a-z][a-z]\)\s.*'
    }

    for line in lines:
        line = line.strip()
        if not line:
            latex_lines.append("\\medskip")
            continue

        # Prüfen, ob es ein echter Befehl ist oder nur ein Wort wie \siehe
        if line.startswith('\\'):
            cmd_name = line.split('{')[0].replace('\\', '')
            if cmd_name not in valid_commands:
                line = '\\' + line # Verdoppelt den Backslash für Text-Anzeige

        # Sonderzeichen escapen
        for char, escaped in chars_to_escape.items():
            line = line.replace(char, escaped)

        # Überschriften-Logik
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

def main():
    st.sidebar.title("📌 Gliederung")
    st.title("Jura Klausur-Editor")
    
    user_input = st.text_area("Schreibe hier dein Gutachten...", height=500, key="main_editor")

    if user_input:
        for line in user_input.split('\n'):
            line = line.strip()
            if re.match(r'^[A-Z]\..*', line):
                st.sidebar.markdown(f"**{line}**")
            elif re.match(r'^[IVX]+\..*', line):
                st.sidebar.markdown(f"&nbsp;&nbsp;{line}")

    if st.button("🏁 PDF generieren"):
        with st.spinner("PDF wird erstellt..."):
            latex_body = parse_to_latex(user_input)
            full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{setspace}
\usepackage{fancyhdr}
\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[R]{\thepage}
\begin{document}
    \tableofcontents
    \clearpage
    \setstretch{1.2}
""" + latex_body + r"\end{document}"

            with open("klausur.tex", "w", encoding="utf-8") as f:
                f.write(full_latex)

            env = os.environ.copy()
            env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

            # Wir fangen den Fehler nicht hart ab, sondern schauen ob das PDF existiert
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], env=env)
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], env=env)
            
            if os.path.exists("klausur.pdf"):
                with open("klausur.pdf", "rb") as f:
                    st.download_button("📥 PDF herunterladen", f, "Klausur.pdf")
                st.success("PDF wurde erstellt (evtl. mit Warnungen).")
            else:
                st.error("Kritischer Fehler: PDF konnte nicht erzeugt werden.")

if __name__ == "__main__":
    main()
