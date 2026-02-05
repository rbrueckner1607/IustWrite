import subprocess
import os
import re
import streamlit as st

# --- PARSER KLASSE ---
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
        self.star_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*(\s|$)',
            2: r'^\s*[A-H]\*(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*(\s|$)',
            4: r'^\s*\d+\*(\s|$)',
            5: r'^\s*[a-z]\)\*(\s|$)'
        }

    def apply_shortcuts(self, text):
        """
        Ersetzt \bf(...), \it(...) und \fn(...) durch LaTeX-Befehle.
        Unterstützt verschachtelte Klammern durch einen gierigen Scan von innen nach außen.
        """
        shortcuts = [
            (r'\\bf\(', r'\\textbf{'),
            (r'\\it\(', r'\\textit{'),
            (r'\\fn\(', r'\\footnote{')
        ]
        
        for cmd_pattern, latex_cmd in shortcuts:
            # Wir suchen nach dem Muster \cmd(
            while True:
                match = re.search(cmd_pattern, text)
                if not match:
                    break
                
                start_idx = match.start()
                content_start = match.end()
                
                # Klammern zählen, um das richtige Ende zu finden
                bracket_level = 1
                current_idx = content_start
                found_end = False
                
                while current_idx < len(text):
                    if text[current_idx] == '(':
                        bracket_level += 1
                    elif text[current_idx] == ')':
                        bracket_level -= 1
                    
                    if bracket_level == 0:
                        content_end = current_idx
                        # Ersetzung vornehmen
                        content = text[content_start:content_end]
                        text = text[:start_idx] + latex_cmd + content + "}" + text[content_end+1:]
                        found_end = True
                        break
                    current_idx += 1
                
                if not found_end: # Falls keine schließende Klammer gefunden wurde
                    break
        return text

    def parse_content(self, lines):
        latex_output = []
        for line in lines:
            line_s = line.strip()
            if not line_s:
                latex_output.append("\\medskip")
                continue

            found_level = False
            # 1. Überschriften (Stern)
            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*", 4: "paragraph*", 5: "subparagraph*"}
                    cmd = cmds.get(level, "subparagraph*")
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    break

            if not found_level:
                # 2. Gliederung
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        cmds = {1: "section", 2: "subsection", 3: "subsubsection", 4: "paragraph", 5: "subparagraph", 6: "subparagraph", 7: "subparagraph", 8: "subparagraph"}
                        cmd = cmds.get(level, "subparagraph")
                        toc_indent = f"{max(0, level - 3)}em" if level > 3 else "0em"
                        latex_output.append(f"\\{cmd}*{{{line_s}}}")
                        toc_cmd = "subsubsection" if level >= 3 else cmd
                        latex_output.append(f"\\addcontentsline{{toc}}{{{toc_cmd}}}{{\\hspace{{{toc_indent}}}{line_s}}}")
                        found_level = True
                        break

            if not found_level:
                # 3. Fließtext & Shortcuts
                line_s = self.apply_shortcuts(line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- STREAMLIT UI ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

if "klausur_text" not in st.session_state:
    st.session_state.klausur_text = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content
        st.session_state.klausur_text = content

def main():
    doc_parser = KlausurDocument()
    
    st.markdown("""
        <style>
        [data-testid="stSidebar"] .stMarkdown { margin-bottom: -18px; }
        [data-testid="stSidebar"] p { font-size: 0.82rem !important; line-height: 1.1 !important; }
        [data-testid="stSidebar"] h2 { font-size: 1.1rem; padding-bottom: 5px; }
        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 98% !important;
        }
        .stTextArea textarea {
            font-family: 'Courier New', Courier, monospace;
            font-size: 1.05rem;
            line-height: 1.4;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

    # SIDEBAR
    st.sidebar.title("⚙️ Layout")
    rand_input = st.sidebar.text_input("Korrekturrand rechts (in cm)", value="6")
    rand_wert = rand_input.strip() + ("cm" if not any(u in rand_input for u in ['cm', 'mm']) else "")
    zeilenabstand = st.sidebar.selectbox("Zeilenabstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)
    
    font_options = {"lmodern (Standard)": "lmodern", "Times (klassisch)": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet", "Computer Modern": ""}
    font_choice = st.sidebar.selectbox("Schriftart", options=list(font_options.keys()), index=0)
    selected_font_package = font_options[font_choice]

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    # HEADER
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: kl_titel = st.text_input("Titel", "Gutachten")
    with c2: kl_datum = st.text_input("Datum", "")
    with c3: kl_kuerzel = st.text_input("Kürzel/Matrikel", "")

    current_text = st.text_area("Gutachten", value=st.session_state.klausur_text, height=750, key="main_editor_key")

    # COUNTER
    char_count = len(current_text)
    word_count = len(current_text.split())
    st.info(f"📊 {char_count} Zeichen | {word_count} Wörter")

    # SIDEBAR LIVE PREVIEW
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            for level, pattern in {**doc_parser.prefix_patterns, **doc_parser.star_patterns}.items():
                if re.match(pattern, line_s):
                    st.sidebar.markdown(f"{'&nbsp;' * (level * 2)}{'**' if level <= 2 else ''}{line_s}{'**' if level <= 2 else ''}")
                    break

    st.markdown("---")
    
    # ACTIONS
    col_pdf, col_save, col_load, col_sach = st.columns([1, 1, 1, 1])
    with col_pdf: pdf_btn = st.button("🏁 PDF generieren", use_container_width=True)
    with col_save: st.download_button("💾 Als TXT speichern", data=current_text, file_name="Gutachten.txt", use_container_width=True)
    with col_load: st.file_uploader("📂 TXT laden", type=['txt'], key="uploader_key", on_change=handle_upload)
    with col_sach: sach_file = st.file_uploader("📄 Sachverhalt (PDF)", type=['pdf'], key="sachverhalt_key")

    if pdf_btn:
        if not current_text.strip():
            st.warning("Editor ist leer.")
        else:
            with st.spinner("Kompiliere..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                titel_komp = f"{kl_titel} ({kl_datum})" if kl_datum.strip() else kl_titel
                font_latex = f"\\usepackage{{{selected_font_package}}}" if selected_font_package else ""
                if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                sach_cmd = ""
                if sach_file:
                    with open("temp_sach.pdf", "wb") as f: f.write(sach_file.getbuffer())
                    sach_cmd = r"\includepdf[pages=-]{temp_sach.pdf}"

                full_latex = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages, setspace, geometry, fancyhdr}
""" + font_latex + r"""
\geometry{left=2cm, right=3cm, top=2.5cm, bottom=3cm}
\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_komp + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
}
\begin{document}
\sloppy
""" + sach_cmd + r"""
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}\setcounter{page}{1}\pagestyle{iustwrite}
\setstretch{""" + str(zeilenabstand) + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"""
\end{document}
"""
                with open("klausur.tex", "w", encoding="utf-8") as f: f.write(full_latex)
                for ext in ["pdf", "aux", "log", "toc"]:
                    if os.path.exists(f"klausur.{ext}"): os.remove(f"klausur.{ext}")
                for _ in range(2):
                    subprocess.run(["pdflatex", "-interaction=nonstopmode", "klausur.tex"], capture_output=True)

                if os.path.exists("klausur.pdf"):
                    st.success("PDF bereit!")
                    with open("klausur.pdf", "rb") as f:
                        st.download_button("📥 Download", f, "Gutachten.pdf", use_container_width=True)
                else:
                    st.error("LaTeX Fehler.")

if __name__ == "__main__":
    main()
