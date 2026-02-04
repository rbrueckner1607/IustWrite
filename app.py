import streamlit as st
import tempfile
import os
import subprocess
import shutil
import re
from datetime import datetime

# -----------------------------
# 1. HEADINGCOUNTER
# -----------------------------
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
        def letter(n):
            return chr(96 + n) if 1 <= n <= 26 else str(n)
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

# -----------------------------
# 2. KLAUSURDOCUMENT
# -----------------------------
class KlausurDocument:
    def __init__(self):
        self.heading_counter = HeadingCounter()
        # Muster für Präfixe
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
        # Muster für reine Titel mit *
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
        for lineno, line in enumerate(lines):
            text = line.strip()
            if not text: continue
            found_normal = False
            for level, pattern in sorted(self.prefix_patterns.items()):
                if re.match(pattern, text):
                    indent = (level - 1) * 2
                    spaces = "  " * indent
                    toc.append((spaces + text, lineno))
                    found_normal = True
                    break
            if not found_normal:
                for level, pattern in sorted(self.title_patterns.items()):
                    match = re.match(pattern, text)
                    if match:
                        title_text = match.group(2).strip()
                        if title_text:
                            indent = (level - 1) * 2
                            spaces = "  " * indent
                            toc.append((spaces + title_text, lineno))
                            break
        return toc

    def to_latex(self, title, date, matrikel, lines):
        latex = [
            r"\documentclass[12pt,a4paper]{article}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{lmodern}",
            r"\usepackage[left=2cm,right=6cm,top=2.5cm,bottom=3cm]{geometry}",
            r"\usepackage{fancyhdr}",
            r"\usepackage{tocloft}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            r"\fancyfoot[R]{\thepage}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\begin{document}",
            r"\enlargethispage{40pt}",
            r"\pagenumbering{gobble}",
            r"\vspace*{-3cm}",
            r"\tableofcontents",
            r"\clearpage",
            r"\pagenumbering{arabic}",
            fr"\section*{{{title} ({date})}}",
        ]

        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                latex.append("")
                continue

            # Prüfe Title-Patterns
            title_match = False
            for level, pattern in self.title_patterns.items():
                match = re.match(pattern, line_strip)
                if match:
                    title_text = match.group(2).strip()
                    if level == 1:
                        latex.extend([r"\section*{" + title_text + "}",
                                      r"\addcontentsline{toc}{section}{" + title_text + "}"])
                    elif level == 2:
                        latex.extend([r"\subsection*{" + title_text + "}",
                                      r"\addcontentsline{toc}{subsection}{" + title_text + "}"])
                    elif level == 3:
                        latex.extend([r"\subsubsection*{" + title_text + "}",
                                      r"\addcontentsline{toc}{subsubsection}{" + title_text + "}"])
                    title_match = True
                    break

            if not title_match:
                # Normale Präfixe
                if re.match(self.prefix_patterns[1], line_strip):
                    latex.extend([r"\section*{" + line_strip + "}",
                                  r"\addcontentsline{toc}{section}{" + line_strip + "}"])
                elif re.match(self.prefix_patterns[2], line_strip):
                    latex.extend([r"\subsection*{" + line_strip + "}",
                                  r"\addcontentsline{toc}{subsection}{" + line_strip + "}"])
                else:
                    # Fußnoten
                    if re.search(self.footnote_pattern, line_strip):
                        match = re.search(self.footnote_pattern, line_strip)
                        footnote_text = match.group(1).strip()
                        clean_line = re.sub(self.footnote_pattern, '', line_strip).strip()
                        if clean_line:
                            latex.append(clean_line + f"\\footnote{{{footnote_text}}}")
                        else:
                            latex.append(f"\\footnote{{{footnote_text}}}")
                    else:
                        latex.append(line_strip)

        latex.append(r"\end{document}")
        return "\n".join(latex)

    def to_pdf_bytes(self, latex_content):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "klausur.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # pdflatex im PATH
            pdflatex_bin = shutil.which("pdflatex")
            if not pdflatex_bin:
                raise FileNotFoundError("pdflatex nicht im PATH!")

            # 2x kompilieren
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)
            subprocess.run([pdflatex_bin, "-interaction=nonstopmode", "klausur.tex"],
                           cwd=tmpdir, capture_output=True, check=True)

            pdf_path = os.p_
