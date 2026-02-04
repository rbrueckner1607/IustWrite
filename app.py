import streamlit as st
import subprocess
import os
import re

# --- PARSER KLASSE (MAXIMAL EINFACH) ---
class KlausurDocument:
    def __init__(self):
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+',
            2: r'^\s*[A-H]\.',
            3: r'^\s*[IVX]+[IVX]*\.',
            4: r'^\s*\d+\.',
            5: r'^\s*[a-z]\)',
            6: r'^\s*[a-z]{2}\)',
            7: r'^\s*\([a-z]\)',
            8: r'^\s*\([a-z]{2}\)'
        }
        self.footnote_pattern = r'\\fn\((.*?)\)'

    def parse_content(self, lines):
        latex_output = []
        for line in lines:
            line_s = line.strip()
            if not line_s:
                latex_output.append(r"\medskip")
                continue
            
            found_level = False
            for level, pattern in self.prefix_patterns.items():
                if re.match(pattern, line_s):
                    if level == 1:
                        latex_output.append(f"\\section*{{{line_s}}}")
                    elif level == 2:
                        latex_output.append(f"\\subsection*{{{line_s}}}")
                    elif level == 3:
                        latex_output.append(f"\\subsubsection*{{{line_s}}}")
                    else:
                        latex_output.append(f"\\paragraph*{{{line_s}}}")
                    found_level = True
                    break
            
            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{{\\1}}', line_s)
                line_s = line_s.replace('§', r'\S~').replace('&', r'\&').replace('%', r'\%').replace('#', r'\#')
                latex_output.append(line_s)
        
        return "\\n".join(latex_output)

# --- UI ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

def main():
    st.title("⚖️ IustWrite Editor")
    
    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Klausur-Titel", "Übungsklausur")
    with c2: kl_datum = st.text_input("Datum", "04.02.2026")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "K-123")

    st.sidebar.title("📌 Gliederung")
    user_input = st.text_area("Gutachten-Text", height=500, key="editor")

    doc_parser = KlausurDocument()
    if user_input:
        for line in user_input.split('\n'):
            line_s = line.strip()
            for level, pattern in doc_parser.prefix_patterns.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown(" " * (level * 2) + "• " + line_s)
                    break

    if st.button("🏁 PDF generieren"):
        if user_input:
            with st.spinner("Kompiliere..."):
                parsed_content = doc_parser.parse_content(user_input.split('\n'))
                titel_komplett = f"{kl_titel} ({kl_datum})"
                
                # FIX: Triple-Quotes mit korrekten Escapes
                full_latex = r'''\\documentclass[12pt,a4paper]{article}
\\usepackage[ngerman]{babel}
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage{palatino}
\\usepackage[margin=2.5cm,right=6cm]{geometry}
\\usepackage{fancyhdr}
\\usepackage{tocloft}
\\pagestyle{fancy}
\\fancyhf{}
\\fancyhead[L]{{''' + kl_kuerzel + r'''}}
\\fancyhead[R]{{''' + titel_komplett + r'''}}
\\renewcommand{\\headrulewidth}{0.5pt}
\\fancyfoot[R]{\\\\thepage}

\\setlength{\\cftbeforesecskip}{3pt}
\\setlength{\\cftbeforesubsecskip}{2pt}
\\renewcommand{\\cftsecindent}{0em}
\\renewcommand{\\cftsubsecindent}{1em}
\\renewcommand{\\cftsubsubsecindent}{2em}

\\begin{document}
\\pagenumbering{gobble}
\\tableofcontents
\\clearpage
\\pagenumbering{arabic}
\\setcounter{page}{1}

\\noindent\\textbf{\\Large ''' + titel_komplett + r'''}}\\\\ \\vspace{1em}
''' + parsed_content + r'''
\\end{document}'''

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                 capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    st.success("✅ PDF erstellt!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Download", f, f"Klausur_{kl_kuerzel}.pdf")
                else:
                    st.error("❌ PDF Fehler!")

if __name__ == "__main__":
    main()
