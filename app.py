import re
from typing import List


class KlausurLatexExporter:
    """
    KANONISCHE Export-Logik.
    Diese Klasse ist die einzige Wahrheit für den LaTeX-Export.
    """

    # ---------- Muster ----------
    PREFIX_PATTERNS = {
        1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\.?',
        2: r'^\s*[A-H]\.',
        3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.',
        4: r'^\s*\d+\.',
        5: r'^\s*[a-z]\)',
        6: r'^\s*[a-z]{2}\)',
        7: r'^\s*\([a-z]\)',
        8: r'^\s*\([a-z]{2}\)',
    }

    TITLE_PATTERNS = {
        1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*\s*(.+)',
        2: r'^\s*([A-H])\*\s*(.+)',
        3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\*\s*(.+)',
        4: r'^\s*(\d+)\*\s*(.+)',
        5: r'^\s*([a-z])\*\s*(.+)',
        6: r'^\s*([a-z]{2})\*\s*(.+)',
        7: r'^\s*\(([a-z])\)\*\s*(.+)',
        8: r'^\s*\(([a-z]{2})\)\*\s*(.+)',
    }

    FOOTNOTE_PATTERN = r'\\fn\(([^)]*)\)'

    # ---------- API ----------
    def export(
        self,
        lines: List[str],
        title: str,
        date: str,
        matrikel: str,
    ) -> str:
        latex = []

        # ---------- Präambel ----------
        latex.extend([
            r"\documentclass[12pt,a4paper]{jurabook}",
            r"\usepackage[ngerman]{babel}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage{lmodern}",
            r"\usepackage{geometry}",
            r"\geometry{left=2cm,right=6cm,top=2.5cm,bottom=3cm}",
            r"\usepackage{fancyhdr}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            rf"\fancyhead[L]{{{title}}}",
            rf"\fancyhead[R]{{{date}}}",
            r"\fancyfoot[R]{\thepage}",
            r"\renewcommand{\contentsname}{Gliederung}",
            r"\begin{document}",
            r"\pagenumbering{gobble}",
            r"\tableofcontents",
            r"\clearpage",
            r"\pagenumbering{arabic}",
        ])

        # ---------- Inhalt ----------
        for raw in lines:
            line = raw.rstrip()
            if not line:
                latex.append("")
                continue

            # Titel-Zeilen (*)
            handled = False
            for level, pattern in self.TITLE_PATTERNS.items():
                m = re.match(pattern, line)
                if m:
                    text = m.group(2).strip()
                    latex.append(self._latex_heading(level, text))
                    handled = True
                    break

            if handled:
                continue

            # Normale Gliederung
            for level, pattern in self.PREFIX_PATTERNS.items():
                if re.match(pattern, line):
                    latex.append(self._latex_heading(level, line))
                    handled = True
                    break

            if handled:
                continue

            # Fußnoten
            fn = re.search(self.FOOTNOTE_PATTERN, line)
            if fn:
                fn_text = fn.group(1)
                clean = re.sub(self.FOOTNOTE_PATTERN, "", line).strip()
                if clean:
                    latex.append(f"{clean}\\footnote{{{fn_text}}}")
                else:
                    latex.append(f"\\footnote{{{fn_text}}}")
                continue

            # Normaler Text
            latex.append(line)

        latex.append(r"\end{document}")
        return "\n".join(latex)

    # ---------- Intern ----------
    def _latex_heading(self, level: int, text: str) -> str:
        """
        Juristische Gliederung:
        ALLES manuell ins TOC, KEINE automatische Nummerierung.
        """
        indent = r"\hspace*{" + str((level - 1) * 1.5) + r"em}"

        return "\n".join([
            rf"\noindent {indent}\textbf{{{text}}}\par",
            rf"\addcontentsline{{toc}}{{section}}{{{indent}{text}}}",
            r"\vspace{0.5em}",
        ])
