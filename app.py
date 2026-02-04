import streamlit as st
import os
import re
import shutil
import subprocess
import tempfile

# ----------------------
# Pfad zu Assets
def get_asset_path(filename):
    return os.path.join("assets", filename)

# ----------------------
# Tectonic PDF Export
def export_latex(latex_content: str, filename: str):
    work_dir = os.path.dirname(filename)
    os.makedirs(work_dir, exist_ok=True)
    
    # 1. .tex Datei schreiben
    with open(filename, "w", encoding="utf-8") as f:
        f.write(latex_content)
    
    # 2. Assets kopieren
    assets = ["jurabook.cls", "jurabase.sty", "remreset.sty"]
    for asset in assets:
        src = get_asset_path(asset)
        dst = os.path.join(work_dir, asset)
        if os.path.exists(src):
            shutil.copy(src, dst)
    
    # 3. Tectonic-Pfad
    tectonic_bin = os.path.join("assets", "tectonic", "tectonic")
    if not os.path.exists(tectonic_bin):
        st.error("Tectonic-Binary fehlt! Bitte unter assets/tectonic/tectonic einfügen.")
        return
    
    # 4. PDF kompilieren
    try:
        subprocess.run([tectonic_bin, filename, "--outdir", work_dir], check=True)
        st.success("PDF erfolgreich erstellt!")
    except subprocess.CalledProcessError as e:
        st.error(f"PDF-Kompilierung fehlgeschlagen: {e}")

# ----------------------
# Heading Counter für Nummerierung
class HeadingCounter:
    def __init__(self, max_level=8):
        self.max_level = max_level
        self.counters = [0]*max_level
    
    def increment(self, level):
        idx = level-1
        self.counters[idx] += 1
        for i in range(idx+1, self.max_level):
            self.counters[i] = 0
    
    def get_numbering(self, level):
        romans = ["", "I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX"]
        def letter(n): return chr(96+n) if 1<=n<=26 else str(n)
        parts=[]
        for i in range(level):
            n = self.counters[i]
            if n==0: continue
            if i==0: parts.append(f"Teil {n}.")
            elif i==1: parts.append(chr(64+n)+".")
            elif i==2: parts.append(romans[n] if n<len(romans) else str(n)+".")
            elif i==3: parts.append(f"{n}.")
            elif i==4: parts.append(f"{letter(n)})")
            elif i==5: parts.append(f"{letter(n)*2})")
            elif i==6: parts.append(f"({letter(n)})")
            elif i==7: parts.append(f"({letter(n)*2})")
            else: parts.append(str(n))
        return " ".join([x for x in parts if x])

# ----------------------
# Streamlit App
st.set_page_config(page_title="iustWrite", layout="wide")

st.title("iustWrite – Online Klausur Editor")

# Metadaten
col1, col2, col3 = st.columns(3)
title_text = col1.text_input("Titel")
date_text = col2.text_input("Datum")
matrikel_text = col3.text_input("Matrikelnummer")

# Editor + Gliederung
counter = HeadingCounter()
toc = []

st.markdown("### Klausurtext")
text_content = st.text_area("Schreibe hier deine Klausur...", height=500, key="editor")

# ----------------------
# Überschrift erkennen & TOC aufbauen
prefix_patterns = {
    1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
    2: r'^\s*[A-H]\.(\s|$)',
    3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
    4: r'^\s*\d+\.(\s|$)',
    5: r'^\s*[a-z]\)(\s|$)',
    6: r'^\s*[a-z]{2}\)(\s|$)',
    7: r'^\s*\([a-z]\)(\s|$)',
    8: r'^\s*\([a-z]{2}\)(\s|$)',
}

title_patterns = {
    1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*\s*(.*)',
    2: r'^\s*([A-H])\*\s*(.*)',
    3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*\s*(.*)',
    4: r'^\s*(\d+)\*\s*(.*)',
    5: r'^\s*([a-z])\*\s*(.*)',
    6: r'^\s*([a-z]{2})\*\s*(.*)',
    7: r'^\s*\(([a-z])\)\*\s*(.*)',
    8: r'^\s*\(([a-z]{2})\)\*\s*(.*)',
}

footnote_pattern = r'\\fn\(([^)]*)\)'

lines = text_content.splitlines()
toc = []

for lineno, line in enumerate(lines):
    line_strip = line.strip()
    if not line_strip: continue
    
    found=False
    for level, pattern in sorted(title_patterns.items()):
        m=re.match(pattern, line_strip)
        if m:
            toc.append((level, m.group(2)))
            found=True
            break
    if not found:
        for level, pattern in sorted(prefix_patterns.items()):
            if re.match(pattern, line_strip):
                toc.append((level, line_strip))
                break

# ----------------------
# Seitenleiste für TOC
st.sidebar.title("Gliederung")
for lvl, txt in toc:
    st.sidebar.write("  "*(lvl-1) + txt)

# ----------------------
# Export Button
if st.button("Export PDF"):
    if not title_text or not date_text or not matrikel_text:
        st.warning("Bitte Titel, Datum und Matrikelnummer eingeben!")
    else:
        # LaTeX Inhalt zusammenstellen
        latex=[]
        latex.append(r"\documentclass[12pt,a4paper,oneside]{jurabook}")
        latex.append(r"\usepackage[ngerman]{babel}")
        latex.append(r"\usepackage[utf8]{inputenc}")
        latex.append(r"\usepackage[T1]{fontenc}")
        latex.append(r"\usepackage{lmodern}")
        latex.append(r"\usepackage{geometry}")
        latex.append(r"\usepackage{fancyhdr}")
        latex.append(r"\usepackage{titlesec}")
        latex.append(r"\usepackage{enumitem}")
        latex.append(r"\usepackage{tocloft}")
        latex.append(r"\geometry{left=2cm,right=6cm,top=2.5cm,bottom=3cm}")
        latex.append(r"\setcounter{secnumdepth}{6}")
        latex.append(r"\setcounter{tocdepth}{6}")
        latex.append(r"\begin{document}")
        latex.append(fr"\chapter*{{{title_text} ({date_text})}}")
        latex.append(r"\tableofcontents\clearpage")

        for line in lines:
            line_strip=line.strip()
            if not line_strip:
                latex.append("")
                continue
            # Fußnoten ersetzen
            fn_match=re.search(footnote_pattern,line_strip)
            if fn_match:
                fn_text=fn_match.group(1)
                clean_line=re.sub(footnote_pattern,"",line_strip)
                if clean_line:
                    latex.append(clean_line + f"\\footnote{{{fn_text}}}")
                else:
                    latex.append(f"\\footnote{{{fn_text}}}")
            else:
                latex.append(line_strip)
        
        latex.append(r"\end{document}")
        latex_content="\n".join(latex)

        # Temporärer Pfad
        tmp_dir=tempfile.gettempdir()
        tex_path=os.path.join(tmp_dir,"klausur.tex")
        export_latex(latex_content, tex_path)
