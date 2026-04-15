import subprocess
import os
import re
import streamlit as st
import tempfile
import shutil
from pathlib import Path
from streamlit_local_storage import LocalStorage
from streamlit_autorefresh import st_autorefresh

# --- OPTIMIERTE PARSER KLASSE ---
class KlausurDocument:      
    def __init__(self):
        self.prefix_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+(\.|)(\s|$)',
            2: r'^\s*[A-H]\.(\s|$)',
            3: r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\.(\s|$)',
            4: r'^\s*\d+\.(\s|$)',
            5: r'^\s*[a-z]\)\s*',
            6: r'^\s*[a-z]{2}\)\s*',   
            7: r'^\s*\(\d+\)\s*',       
            8: r'^\s*\([a-z]\)\s*', 
            9: r'^\s*\([a-z]{2}\)\s*' 
        }

        # Falls du die Sternchen-Logik (versteckte Gliederung) 
        # ebenfalls erweitern willst, hier das neue Pattern:
        self.star_patterns = {
            1: r'^\s*(Teil|Tatkomplex|Aufgabe)\s+\d+\*(\s|$)',
            2: r'^\s*[A-H]\*(\s|$)',   # KEIN Punkt vor dem Stern!
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
            # --- 1. BLOCK: Verarbeitung der Sternchen-Überschriften (Versteckte Gliederung) ---
            for level, pattern in self.star_patterns.items():
                match = re.match(pattern, line_s)
                if match:
                    cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*"}
                    cmd = cmds.get(level, "subsubsection*")
                    
                    # Hier wird der Marker (z.B. "Teil 1*") abgeschnitten
                    display_text = line_s[match.end():].strip()
                    
                    # Falls kein Text nach dem Sternchen folgt, nimm die Zeile ohne Stern
                    if not display_text:
                        display_text = line_s.replace('*', '').strip()
                        
                    latex_output.append(f"\\{cmd}{{{display_text}}}")
                    found_level = True
                    break

           # --- 2. BLOCK: Verarbeitung der normalen Überschriften (In Gliederung) ---
            if not found_level:
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        # --- NEU: Prüfung auf manuelles Fett-Sternchen am Ende ---
                        # Wenn die Zeile auf * endet (z.B. "A. Diebstahl*")
                        manual_bold = False
                        if line_s.endswith('*'):
                            manual_bold = True
                            line_s = line_s[:-1].strip() # Sternchen für die Ausgabe entfernen
                        
                        if level >= 3:
                            cmd = "subsubsection*"
                        elif level == 2:
                            cmd = "subsection*"
                        else:
                            cmd = "section*"
                        
                        # --- FORMATIERUNG & EINRÜCKUNG ---
                        # Wenn es Ebene 1 ist ODER das manuelle Sternchen gesetzt wurde -> FETT
                        if level == 1 or manual_bold:
                            display_text = f"\\textbf{{{line_s}}}"
                        else:
                            display_text = line_s
                        
                        # Einrückungs-Logik (deine aktuellen Werte)
                        if level == 1:
                            indent_val = 0.0
                        else:
                            if level == 2:
                                indent_val = -1.4
                            elif level == 3:
                                indent_val = -1.6
                            else:
                                indent_val = -1.6 + (level - 3) * 1.0
                        
                        toc_indent = f"{indent_val}em"
                        
                        # Ausgabe im Dokument
                        latex_output.append(f"\\{cmd}{{{display_text}}}")
                        
                        # Eintrag ins Inhaltsverzeichnis (TOC)
                        toc_cmd = "subsubsection" if level >= 3 else cmd.replace("*", "")
                        latex_output.append(f"\\addcontentsline{{toc}}{{{toc_cmd}}}{{\\hspace{{{toc_indent}}}{display_text}}}")
                        
                        found_level = True
                        break
            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('&', '\\&').replace('%', '\\%')
                latex_output.append(line_s)
        return "\n".join(latex_output)

# --- UI CONFIG ---
st.set_page_config(page_title="IustWrite Editor", layout="wide", initial_sidebar_state="expanded")

if "main_editor_key" not in st.session_state:
    st.session_state["main_editor_key"] = ""

def handle_upload():
    if st.session_state.uploader_key is not None:
        content = st.session_state.uploader_key.read().decode("utf-8")
        st.session_state["main_editor_key"] = content

def main():
    ls = LocalStorage() 
    doc_parser = KlausurDocument()
    
    # --- 1. DIE LÖSCH-FUNKTION (Nur einmal definieren) ---
    def reset_gutachten():
        # Session State leeren
        st.session_state["main_editor_key"] = ""
        st.session_state["stamm_titel"] = ""
        st.session_state["stamm_datum"] = ""
        st.session_state["stamm_kuerzel"] = ""
        
        # Browser-Speicher leeren
        try:
            ls.removeItem("iustwrite_backup")
            ls.removeItem("iustwrite_titel")
            ls.removeItem("iustwrite_datum")
            ls.removeItem("iustwrite_kuerzel")
        except:
            pass
        st.toast("Neues Gutachten gestartet.")

    # --- 2. INITIAL-LADEN (Beim ersten Seitenaufruf) ---
    if "initialized" not in st.session_state:
        try:
            st.session_state["main_editor_key"] = ls.getItem("iustwrite_backup") or ""
            st.session_state["stamm_titel"] = ls.getItem("iustwrite_titel") or ""
            st.session_state["stamm_datum"] = ls.getItem("iustwrite_datum") or ""
            st.session_state["stamm_kuerzel"] = ls.getItem("iustwrite_kuerzel") or ""
        except:
            st.session_state["main_editor_key"] = ""
            # Falls Felder fehlen, leer initialisieren
            for k in ["stamm_titel", "stamm_datum", "stamm_kuerzel"]:
                if k not in st.session_state: st.session_state[k] = ""
        
        st.session_state["initialized"] = True

    # --- 3. UI-ELEMENTE (Autorefresh & Button) ---
    st_autorefresh(interval=30000, key="autosave_heartbeat")
    
    # CSS für maximale Breite, bewegliche Sidebar und LESERLICHE Schrift
    st.markdown("""
        <style>
        .block-container { 
            padding-top: 1.5rem; 
            padding-left: 2rem; 
            padding-right: 2rem; 
            max-width: 98% !important; 
        }
        [data-testid="stSidebar"] .stMarkdown { margin-bottom: -18px; }
        [data-testid="stSidebar"] p { font-size: 0.85rem !important; line-height: 1.2 !important; }
        
        /* UPDATE: Bearbeiterfreundliche, moderne Schriftart für den Editor */
        .stTextArea textarea { 
            font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif; 
            font-size: 1.1rem;
            line-height: 1.5;
            padding: 15px;
            color: #1e1e1e;
        }
        
        .sachverhalt-box {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 8px;
            border-left: 6px solid #4682B4;
            margin-bottom: 25px;
            line-height: 1.6;
            font-size: 1rem;
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("⚖️ IustWrite Editor")

   # --- SIDEBAR SETTINGS (EINGEKLAPPT) ---

# --- DAS VOLLSTÄNDIGE & DETAILLIERTE HILFE-POPOVER ---
    with st.sidebar.popover("💡 Anleitung & Datenschutz", use_container_width=True):
        st.markdown("# ⚖️ IustWrite Editor v2.0")
        
        tab_anleitung, tab_gliederung, tab_format, tab_dsgvo = st.tabs([
            "📖 Anleitung", "⌨️ Gliederung", "🎨 Formatierung", "🛡️ DSGVO"
        ])
        
        with tab_anleitung:
            st.markdown("### 1. Grundlegende Bedienung")
            st.write("""
            Dieser frei nutzbare und kostenlose Editor ist auf die Erstellung juristischer Gutachten im Jurastudium optimiert. Er nutzt im Hintergrund die professionelle LATEX-Klasse `jurabook`.
            Dadurch kann ein fokussierter Schreibflow sowie ästhetisches Endergebnis ohne Formatierungsärgernisse erreicht werden. Wenn du die Funktionsweise und Grundbefehle des des Editors 
            einmal verinnerlicht hast, wirst du dich nicht mehr mit Formatierungseinstellungen anderer Standartprogramme herumschlagen müssen. Stattdessen kannst du dich voll und ganz 
            auf deine rechtliche Subsumtion und den Gutachtenstil konzentrieren, während der Editor im Hintergrund für die perfekte Einhaltung formaler Vorgaben, korrekte Einrückungen und 
            ein makelloses Schriftbild sorgt. So wird aus deiner juristischen Arbeit nicht nur ein inhaltlich überzeugendes Werk, sondern auch ein optisches Aushängeschild deines Studiums.
            
            * **Stammdaten:** Fülle Titel, Datum und Kürzel aus. Diese werden automatisch in die Kopfzeile des fertigen Gutachtens übernommen. Es ist egal, ob du eine Klausur schreibst, 
            einen Fall löst oder eine Falllösung für deine AG formatierst – die Logik für deine Kopfzeile kannst du hier je nach Bedarf für dich verwenden. Die Namens-/Kürzelangabe erscheint 
            oben links in der Kopfzeile, während die Datumsanzeige in Klammern hinter den Titel gesetzt wird, welcher oben rechts steht. Auf die Datumsangabe kann freilich auch verzichtet werden.
            * **Zeichenzähler:** Die Anzeige unter dem Editorfenster hilft dir, die Vorgaben für Klausuren o.ä. (z.B. max. 25.000 Zeichen) einzuhalten.
            * **Automatisches Backup:** Alle 30 Sekunden wird dein Text im lokalen Speicher deines 
              Browsers gesichert. So geht bei einem Absturz oder nach dem Schließen der Editorseite nichts verloren.
            """)
            st.info("⚠️ **Wichtig:** Deaktiviere den Darkmode deines Browsers, falls Eingabefelder schwarz auf schwarz erscheinen.")

        with tab_gliederung:
            st.markdown("### 2. Die 9 Gliederungsebenen")
            st.write("Eingaben werden automatisch als Überschriften erkannt und korrekt formatiert. Bitte verwende konsequent die standardmäßige alphanumerische Gliederungslogik. Beginne bei einer neuen Überschrift einfach in einer jeweils neuen Zeile, um die Hierarchie zu steuern.")
            st.markdown("""
            | Ebene | Kürzel / Beispiel | Typ |
            | :--- | :--- | :--- |
            | **1** | `Teil 1.` / `Aufgabe 1.` / `Tatkomplex 1.` | Hauptüberschrift (Zentriert) |
            | **2** | `A.` | Großbuchstabe |
            | **3** | `I.` | Römische Zahl |
            | **4** | `1.` | Arabische Zahl |
            | **5** | `a)` | Kleinbuchstabe |
            | **6** | `aa)` | Doppel-Kleinbuchstabe |
            | **7** | `(1)` | Zahl in Klammern |
            | **8** | `(a)` | Buchstabe in Klammern |
            | **9** | `(aa)`| Doppel-Buchstabe in Klammern |
            
            **Profitipps für Profis:**
            * **Erzwungener Fettdruck:** Standardmäßig wird nur die Ebene 1 (`Teil. 1`) in der Gliederung fett dargestellt. Wenn du aber ein Sternchen ans Ende der Zeile setzt (z. B. `A. Diebstahl*`), wird die Überschrift in der Gliederung fett gedruckt. Dies ist z. B. im Strafrecht sinnvoll, um eine übersichtliche Gliederung zu erhalten.
            * **Versteckte Gliederung:** Nutzt du den Stern direkt nach dem Kürzel (z.B. `A*`), erscheint 
              die Überschrift ohne Nummerierung und wird nicht ins Inhaltsverzeichnis aufgenommen.
            """)

        with tab_format:
            st.markdown("### 3. Manuelle LaTeX-Befehle")
            st.write("Für den Feinschliff im Gutachtenstil kannst du diese Befehle nutzen:")
            
            st.markdown("**Schrifttypen:**")
            st.code("\\textbf{fett}\n\\textit{kursiv}\n\\underline{unterstrichen}")
            
            st.markdown("**Layout-Steuerung:**")
            st.code("\\\\ oder \\par      --> Neuer Absatz / Umbruch\n\\noindent         --> Keine Einrückung (linksbündig)\n\\vspace{1cm}      --> Vertikaler Abstand\n\\medskip          --> Standard-Abstand")
            
            st.markdown("**Spezialfunktionen:**")
            st.code("\\fn(Text)         --> Automatische Fußnote\n\\red{Text}         --> Text in Rot\n\\blue{Text}        --> Text in Blau\n\\green{Text}       --> Text in Grün")
            
            st.write("""
            **Sonderzeichen:** Zeichen wie `&`, `%` oder `$` werden vom Editor automatisch erkannt 
            und für LaTeX "entschärft". Du kannst sie also ganz normal im Text verwenden.
            """)

        with tab_dsgvo:
            st.success("### 4. Datensicherheit & DSGVO")
            st.markdown("""
            Dieses Tool wurde nach dem Prinzip **'Privacy by Design'** entwickelt und nutzt die native Architektur von Streamlit zur maximalen Datentrennung:
            
            * **Isolierte Sessions:** Jedes Mal, wenn du diese Seite lädst, wird eine komplett neue, isolierte Instanz (Session) auf dem Server gestartet. Deine Daten sind strikt von anderen Nutzern getrennt.
            * **Flüchtiger Arbeitsspeicher (RAM):** Deine Texte werden ausschließlich im Arbeitsspeicher der laufenden Session verarbeitet. Es findet **keine persistente Speicherung** in einer Datenbank oder auf Festplatten statt.
            * **Automatisches Purging:** Sobald du den Browser-Tab schließt oder die Verbindung unterbrochen wird, wird die zugehörige Session auf dem Server terminiert. Alle im RAM befindlichen Daten deines Gutachtens werden dabei **unwiderruflich gelöscht**.
            * **Lokale Souveränität (LocalStorage):** Das Auto-Save-Backup nutzt den *LocalStorage* deines eigenen Browsers. Das bedeutet: Die Sicherung deines Textes verlässt nie dein Endgerät, bis du explizit auf 'PDF generieren' klickst.
            * **Keine KI-Verwertung:** Im Gegensatz zu kommerziellen Online-Editoren werden deine juristischen Ausführungen **nicht** zur Verbesserung von Sprachmodellen (LLM) oder zu Analysezwecken ausgewertet.
            
            **Tipp:** Nutze den Button **'Neues Gutachten'**, um auch das lokale Backup in deinem Browser aktiv zu bereinigen.
            """)

    # --- ENDE DES POPOVER BLOCKS ---
    st.sidebar.markdown("---")

   # Der Button nutzt nun die oben definierte Funktion
    st.sidebar.button(
        "🗑️ Neues Gutachten", 
        on_click=reset_gutachten, 
        use_container_width=True,
        help="Löscht Text und Backup."
    )

    # 2. TRENNLINIE UND BESTEHENDE EINSTELLUNGEN
    # Diese Zeile muss wieder auf derselben Ebene wie das 'if' stehen
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("⚙️ Layout-Einstellungen", expanded=False):
        rand_wert = st.text_input("Korrekturrand rechts (in cm)", value="6")
        if not any(unit in rand_wert for unit in ['cm', 'mm']): 
            rand_wert += "cm"
        zeilenabstand = st.selectbox("Zeilenabstand", options=["1.0", "1.2", "1.5", "2.0"], index=1)
        font_options = {"lmodern (Standard)": "lmodern", "Times": "mathptmx", "Palatino": "mathpazo", "Helvetica": "helvet"}
        font_choice = st.selectbox("Schriftart", options=list(font_options.keys()), index=0)
        selected_font_package = font_options[font_choice]

    with st.sidebar.expander("📖 Fall abrufen", expanded=False):
        fall_code = st.text_input("Fall-Code eingeben")

    st.sidebar.markdown("---")
    st.sidebar.title("📌 Gliederung")

    if fall_code:
        pfad_zu_fall = os.path.join("fealle", f"{fall_code}.txt")
        if os.path.exists(pfad_zu_fall):
            with open(pfad_zu_fall, "r", encoding="utf-8") as f:
                ganzer_text = f.read()
            zeilen = ganzer_text.split('\n')
            if zeilen:
                sauberer_titel = re.sub(r'^#+\s*(Fall\s+\d+:\s*)?', '', zeilen[0]).strip()
                rest_text = "\n".join(zeilen[1:]).strip()
                with st.expander(f"📄 {sauberer_titel}", expanded=True):
                    st.markdown(f'<div class="sachverhalt-box">{rest_text}</div>', unsafe_allow_html=True)
        else:
            st.sidebar.error(f"Fall {fall_code} nicht gefunden.")

    # --- TITELZEILE ---
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: 
        kl_titel = st.text_input("Titel", key="stamm_titel")
    with c2: 
        kl_datum = st.text_input("Datum", key="stamm_datum")
    with c3: 
        kl_kuerzel = st.text_input("Kürzel / Matrikel", key="stamm_kuerzel")

    if kl_datum.strip():
        titel_komp = f"{kl_titel} ({kl_datum})"
    else:
        titel_komp = kl_titel

    # --- EDITOR ---
    # Wir nutzen den State direkt als Key. 
    # Änderungen in 'main_editor_key' fließen sofort in 'current_text'.
    current_text = st.text_area(
        "", 
        height=600, 
        key="main_editor_key"
    )

    # 5. SOFORT-BACKUP (Nach jeder Änderung)
    if st.session_state["main_editor_key"]:
        try:
            ls.setItem("iustwrite_backup", st.session_state["main_editor_key"])
            ls.setItem("iustwrite_titel", st.session_state["stamm_titel"])
            ls.setItem("iustwrite_datum", st.session_state["stamm_datum"])
            ls.setItem("iustwrite_kuerzel", st.session_state["stamm_kuerzel"])
        except:
            pass

    # --- NEU: ZEICHENZÄHLER ---
    if current_text:
        char_count = len(current_text)
        word_count = len(current_text.split())
        # Anzeige direkt unter dem Editor
        st.markdown(f"*📝 {char_count} Zeichen | {word_count} Wörter*")

    # --- SIDEBAR OUTLINE ---
    if current_text:
        for line in current_text.split('\n'):
            line_s = line.strip()
            if not line_s: continue
            found = False
            for level, pattern in doc_parser.star_patterns.items():
                if re.match(pattern, line_s):
                    indent = "&nbsp;" * (level * 2)
                    st.sidebar.markdown(f"{indent}{line_s}")
                    found = True
                    break
            if not found:
                for level, pattern in doc_parser.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        indent = "&nbsp;" * (level * 2)
                        weight = "**" if level <= 2 else ""
                        st.sidebar.markdown(f"{indent}{weight}{line_s}{weight}")
                        break

    # --- ACTIONS ---
    st.markdown("---")
    col_pdf, col_save, col_load, col_sachverhalt = st.columns([1, 1, 1, 1])

    # 1. Dateiname VORAB zentral definieren (verhindert NameError)
    t_clean = (kl_titel or "Gutachten").replace(" ", "_")
    d_clean = (kl_datum or "Datum").replace(" ", "_")
    k_clean = (kl_kuerzel or "Kuerzel").replace(" ", "_")
    dateiname_basis = f"{t_clean}_{d_clean}_{k_clean}"

    with col_pdf: 
        pdf_button = st.button("🏁 PDF generieren", use_container_width=True)

    with col_save:
        # TXT-Button
        st.download_button(
            label="💾 Als TXT speichern", 
            data=current_text, 
            file_name=f"{dateiname_basis}.txt", 
            use_container_width=True
        )

        # TEX-Button (Direkt darunter in derselben Spalte)
        # Wir bereiten den Inhalt vor
        parsed_content = doc_parser.parse_content(current_text.split('\n'))
        if kl_datum.strip():
            titel_komp = f"{kl_titel} ({kl_datum})"
        else:
            titel_komp = kl_titel
        
        font_latex = f"\\usepackage{{{selected_font_package}}}"
        if "helvet" in selected_font_package: 
            font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

        full_tex_code = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\usepackage{xcolor}

\definecolor{myRed}{RGB}{190, 20, 20}
\definecolor{myBlue}{RGB}{0, 80, 160}
\definecolor{myGreen}{RGB}{0, 120, 50}

\newcommand{\red}[1]{{\color{myRed}#1}}
\newcommand{\blue}[1]{{\color{myBlue}#1}}
\newcommand{\green}[1]{{\color{myGreen}#1}}

\addto\captionsngerman{\renewcommand{\contentsname}{Gliederung}}
""" + font_latex + r"""
\usepackage{setspace}
\usepackage{geometry}
\usepackage{fancyhdr}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\setcounter{tocdepth}{9}
\setcounter{secnumdepth}{9}
\setlength{\parindent}{0pt}

\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_komp + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
}

\begin{document}
\sloppy
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"""
\end{document}"""

        st.download_button(
            label="📄 Als TEX speichern",
            data=full_tex_code,
            file_name=f"{dateiname_basis}.tex",
            mime="text/x-tex",
            use_container_width=True
        )

    with col_load: 
        st.file_uploader("📂 Datei laden", type=['txt'], key="uploader_key", on_change=handle_upload)

    with col_sachverhalt: 
        sachverhalt_file = st.file_uploader("📄 Sachverhalt beifügen (PDF)", type=['pdf'], key="sachverhalt_key")

    if pdf_button:
        if not current_text.strip():
            st.warning("Bitte Text eingeben!")
        else:
            cls_path = os.path.join("latex_assets", "jurabook.cls")
            if not os.path.exists(cls_path):
                st.error("🚨 jurabook.cls fehlt!")
                st.stop()

            with st.spinner("PDF wird erstellt..."):
                parsed_content = doc_parser.parse_content(current_text.split('\n'))
                if kl_datum.strip():
                    titel_komp = f"{kl_titel} ({kl_datum})"
                else:
                    titel_komp = kl_titel
                
                font_latex = f"\\usepackage{{{selected_font_package}}}"
                if "helvet" in selected_font_package: font_latex += "\n\\renewcommand{\\familydefault}{\\sfdefault}"

                full_latex_header = r"""\documentclass[12pt, a4paper, oneside]{jurabook}
\usepackage[ngerman]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{pdfpages}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\usepackage{xcolor}

% --- Textfarben mir Alias ---
\definecolor{myRed}{RGB}{190, 20, 20}
\definecolor{myBlue}{RGB}{0, 80, 160}
\definecolor{myGreen}{RGB}{0, 120, 50}

\newcommand{\red}[1]{{\color{myRed}#1}}
\newcommand{\blue}[1]{{\color{myBlue}#1}}
\newcommand{\green}[1]{{\color{myGreen}#1}}

\addto\captionsngerman{\renewcommand{\contentsname}{Gliederung}}

""" + font_latex + r"""
\usepackage{setspace}
\usepackage{geometry}
\usepackage{fancyhdr}
\geometry{left=2cm, right=2cm, top=2.5cm, bottom=3cm}
\setcounter{tocdepth}{8}
\setcounter{secnumdepth}{8}
\setlength{\parindent}{0pt}

\fancypagestyle{iustwrite}{
    \fancyhf{}
    \fancyhead[L]{\small """ + kl_kuerzel + r"""}
    \fancyhead[R]{\small """ + titel_komp + r"""}
    \fancyfoot[R]{\thepage}
    \renewcommand{\headrulewidth}{0.5pt}
    \fancyhfoffset[R]{0pt}
}
\begin{document}
\sloppy
"""
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tmp_path = Path(tmpdirname)
                    shutil.copy(os.path.abspath(cls_path), tmp_path / "jurabook.cls")
                    
                    assets_folder = os.path.abspath("latex_assets")
                    if os.path.exists(assets_folder):
                        for item in os.listdir(assets_folder):
                            s = os.path.join(assets_folder, item)
                            d = os.path.join(tmpdirname, item)
                            if os.path.isfile(s) and not item.endswith('.cls'):
                                shutil.copy2(s, d)

                    sachverhalt_cmd = ""
                    if sachverhalt_file is not None:
                        with open(tmp_path / "temp_sv.pdf", "wb") as f:
                            f.write(sachverhalt_file.getbuffer())
                        sachverhalt_cmd = r"\includepdf[pages=-]{temp_sv.pdf}"

                    final_latex = full_latex_header + sachverhalt_cmd + r"""
\pagenumbering{gobble}
\tableofcontents\clearpage
\newgeometry{left=2cm, right=""" + rand_wert + r""", top=2.5cm, bottom=3cm}
\pagenumbering{arabic}
\setcounter{page}{1}
\pagestyle{iustwrite}\setstretch{""" + zeilenabstand + r"""}
{\noindent\Large\bfseries """ + titel_komp + r""" \par}\bigskip
""" + parsed_content + r"\end{document}"

                    with open(tmp_path / "klausur.tex", "w", encoding="utf-8") as f:
                        f.write(final_latex)
                    
                    env = os.environ.copy()
                    env["TEXINPUTS"] = f".:{tmp_path}:{assets_folder}:"

                    result = None
                    for _ in range(2):
                        result = subprocess.run(
                            ["pdflatex", "-interaction=nonstopmode", "klausur.tex"], 
                            cwd=tmpdirname, env=env, capture_output=True, text=False
                        )

                    pdf_file = tmp_path / "klausur.pdf"
                    if pdf_file.exists():
                        st.success("PDF erfolgreich erstellt!")
                        with open(pdf_file, "rb") as f:
                            # Namen für das PDF nach dem gleichen Schema generieren
                            t_pdf = (kl_titel or "Gutachten").replace(" ", "_")
                            d_pdf = (kl_datum or "Datum").replace(" ", "_")
                            k_pdf = (kl_kuerzel or "Kuerzel").replace(" ", "_")
                            
                            pdf_name = f"{t_pdf}_{d_pdf}_{k_pdf}.pdf"
                            
                            st.download_button(
                                label="📥 Download PDF", 
                                data=f, 
                                file_name=pdf_name, 
                                use_container_width=True
                            )
                    else:
                        st.error("LaTeX Fehler!")
                        if result:
                            error_log = result.stdout.decode('utf-8', errors='replace')
                            st.code(error_log)

if __name__ == "__main__":
    main()
