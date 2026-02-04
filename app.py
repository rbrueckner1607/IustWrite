import streamlit as st
import subprocess
import os
import re

# --- ERWEITERTE PARSER KLASSE ---
class KlausurDocument:
    def __init__(self):
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)\s.*', 
            6: r'^\s*[a-z]{2}\)\s.*',
            7: r'^\s*\([a-z]\)\s.*',
            8: r'^\s*\([a-z]{2}\)\s.*'
        }
        # Sterne-Überschriften (KEIN TOC, KEINE Nummerierung)
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
            
            # Sterne-Überschriften (nur visuell, KEIN TOC!)
            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*", 
                           4: "paragraph*", 5: "subparagraph*"}
                    cmd = cmds.get(level, "subparagraph*")
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    break
            
            # Normale Überschriften (IM TOC)
            if not found_level:
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        cmds = {1: "section", 2: "subsection", 3: "subsubsection", 
                               4: "paragraph", 5: "subparagraph", 6: "subparagraph", 
                               7: "subparagraph", 8: "subparagraph"}
                        cmd = cmds.get(level, "subparagraph")
                        indent = max(0, (level - 2) * 0.15) if level > 1 else 0
                        
                        latex_output.append(f"\\{cmd}*{{{line_s}}}")
                        latex_output.append(f"\\addcontentsline{{toc}}{{{cmd}}}{{\\hspace{{{indent}cm}}{line_s}}}")
                        found_level = True
                        break
            
            if not found_level:
                # Markdown zu LaTeX konvertieren
                line_s = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\\1}', line_s)
                line_s = re.sub(r'\*(.*?)\*', r'\\emph{\\1}', line_s)
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
            
        return "\\n".join(latex_output)

# --- UI ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

# === CALLBACK FÜR UPLOAD ===
def load_klausur():
    uploaded_file = st.session_state.uploader_key
    if uploaded_file is not None:
        loaded_text = uploaded_file.read().decode("utf-8")
        st.session_state.klausur_text = st.session_state.klausur_text + "\n\n--- NEU GELADETE KLASUR ---\n\n" + loaded_text
        st.session_state.show_success = True

def main():
    doc_parser = KlausurDocument()
    st.title("⚖️ IustWrite Editor")
    
    # === SESSION STATE ===
    if "klausur_text" not in st.session_state:
        st.session_state.klausur_text = ""
    if "show_success" not in st.session_state:
        st.session_state.show_success = False
    
    # === EDITOR EINSTELLUNGEN (mit CSS!) ===
    col_font, col_size = st.columns(2)
    with col_font:
        font_size = st.selectbox("Editor-Schriftgröße", ["12px", "14px", "16px", "18px"], index=2, key="font_size")
    
    c1, c2, c3 = st.columns(3)
    with c1: kl_titel = st.text_input("Klausur-Titel", "Übungsklausur")
    with c2: kl_datum = st.text_input("Datum", "04.02.2026")
    with c3: kl_kuerzel = st.text_input("Kürzel / Matrikel", "K-123")

    st.sidebar.title("📌 Gliederung")
    
    # === GRÖßERES TEXTAREA mit FORMATIERUNG ===
    st.markdown(f"""
    <style>
    textarea[data-baseweb="base-input"][key="klausur_text"] {{
        font-size: {font_size} !important;
        font-family: 'Georgia', serif !important;
        line-height: 1.5 !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    user_input = st.text_area("Gutachten-Text", 
                             value=st.session_state.klausur_text, 
                             height=700,
                             help="**Fett:** **Text** | *Kursiv:* *Text* | Sterne: A*, I*, 1*, a)*",
                             key="klausur_text")

    # === Zeichenzähler ===
    if user_input:
        char_count = len(user_input)
        col1, col2 = st.columns([4, 1])
        with col1:
            st.empty()
        with col2:
            st.metric("Zeichen", f"{char_count:,}")

    # === FIX: Sidebar Gliederung (NUR Kennzeichen, KEIN Text danach) ===
    if user_input:
        for line in user_input.split('\n'):
            line_s = line.strip()
            if not line_s:
                continue
                
            found = False
            
            # Sterne zuerst (NUR Kennzeichen fett)
            for level, pattern in doc_parser.star_patterns.items():
                if re.match(pattern, line_s):
                    # NUR "A*" zeigen, nicht "A* Text"
                    prefix = re.match(pattern, line_s).group(0).strip()
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 4)}**{prefix}**")
                    found = True
                    break
            
            # Normale Überschriften
            if not found:
                for level, pattern in doc_parser.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        prefix = re.match(pattern, line_s).group(0).strip()
                        st.sidebar.markdown(f"{'&nbsp;' * (level * 4)}{prefix}")
                        found = True
                        break

    # === Buttons ===
    col_pdf, col_save, col_load = st.columns([1, 1, 1])
    
    with col_pdf:
        if st.button("🏁 PDF generieren"):
            with st.spinner("Präzisions-Kompilierung läuft..."):
                parsed_content = doc_parser.parse_content(user_input.split('\n'))
                titel_komplett = f"{kl_titel} ({kl_datum})"
                
                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage{setspace}
\usepackage[T1]{fontenc}
\usepackage{palatino}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{tocloft}
\geometry{left=2cm, right=6cm, top=2.5cm, bottom=3cm}

\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_komplett + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
    \renewcommand{\footrulewidth}{0pt}
}

\makeatletter
\renewcommand{\@cfoot}{}
\makeatother

\begin{document}
\pagenumbering{gobble}
\renewcommand{\contentsname}{Gliederung}
\tableofcontents
\clearpage

\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}
\setstretch{1.2}

{\noindent\Large\bfseries """ + titel_komplett + r""" \par}\bigskip
""" + parsed_content + r"""\end{document}"""

                with open("klausur.tex", "w", encoding="utf-8") as f:
                    f.write(full_latex)

                env = os.environ.copy()
                env["TEXINPUTS"] = f".:{os.path.join(os.getcwd(), 'latex_assets')}:"

                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                                   env=env, capture_output=True)
                
                if os.path.exists("klausur.pdf"):
                    st.success("PDF erfolgreich erstellt!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Download", f, f"Klausur_{kl_kuerzel}.pdf")
                else:
                    st.error("Fehler beim Erzeugen.")

    with col_save:
        if st.button("💾 Als TXT speichern", type="secondary"):
            st.download_button(
                label="📥 Download TXT",
                data=user_input,
                file_name=f"Klausur_{kl_kuerzel}_{kl_titel.replace(' ', '_')}.txt",
                mime="text/plain"
            )

    with col_load:
        st.file_uploader("📂 Klausur laden", 
                        type=['txt'], 
                        key="uploader_key",
                        on_change=load_klausur)
        
        if st.session_state.get("show_success", False):
            st.success("✅ Klausur geladen!")
            st.session_state.show_success = False

if __name__ == "__main__":
    main()
