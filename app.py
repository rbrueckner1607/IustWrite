import subprocess
import os
import re
import streamlit as st

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
        first_text = True

        for line in lines:
            line_s = line.strip()

            if not line_s:
                latex_output.append("\\medskip")
                continue

            found_level = False

            for level, pattern in self.star_patterns.items():
                if re.match(pattern, line_s):
                    cmd = ["section*", "subsection*", "subsubsection*", "paragraph*", "subparagraph*"][level-1]
                    latex_output.append(f"\\{cmd}{{{line_s}}}")
                    found_level = True
                    break

            if not found_level:
                for level, pattern in self.prefix_patterns.items():
                    if re.match(pattern, line_s):
                        cmd = ["section", "subsection", "subsubsection", "paragraph", "subparagraph"][min(level,5)-1]
                        indent = max(0, (level - 2) * 0.15) if level > 1 else 0
                        latex_output.append(f"\\{cmd}*{{{line_s}}}")
                        latex_output.append(
                            f"\\addcontentsline{{toc}}{{{cmd}}}{{\\hspace{{{indent}cm}}{line_s}}}"
                        )
                        found_level = True
                        break

            if not found_level:
                line_s = re.sub(self.footnote_pattern, r'\\footnote{\1}', line_s)
                line_s = line_s.replace('§', '\\S~').replace('&', '\\&').replace('%', '\\%')

                if first_text:
                    latex_output.append("\\noindent " + line_s)
                    first_text = False
                else:
                    latex_output.append(line_s)

        return "\n".join(latex_output)


# --- UI ---
st.set_page_config(page_title="IustWrite Editor", layout="wide")

# CSS: mehr Breite für Editor
st.markdown("""
<style>
.block-container {
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100%;
}
</style>
""", unsafe_allow_html=True)

# === CALLBACK FÜR UPLOAD ===
def load_klausur():
    uploaded_file = st.session_state.uploader_key
    if uploaded_file is None:
        return

    text = uploaded_file.read().decode("utf-8")
    lines = text.splitlines()

    meta = {}
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            body_start = i + 1
            break
        if line.startswith("#"):
            key, val = line[1:].split(":", 1)
            meta[key.strip()] = val.strip()

    st.session_state.kl_titel = meta.get("TITEL", "")
    st.session_state.kl_datum = meta.get("DATUM", "")
    st.session_state.kl_kuerzel = meta.get("KUERZEL", "")
    st.session_state.klausur_text = "\n".join(lines[body_start:])
    st.session_state.show_success = True


def main():
    doc_parser = KlausurDocument()
    st.title("⚖️ IustWrite Editor")

    for key, default in {
        "klausur_text": "",
        "kl_titel": "Übungsklausur",
        "kl_datum": "04.02.2026",
        "kl_kuerzel": "K-123",
        "show_success": False
    }.items():
        st.session_state.setdefault(key, default)

    c1, c2, c3 = st.columns(3)
    with c1:
        kl_titel = st.text_input("Klausur-Titel", st.session_state.kl_titel)
    with c2:
        kl_datum = st.text_input("Datum", st.session_state.kl_datum)
    with c3:
        kl_kuerzel = st.text_input("Kürzel / Matrikel", st.session_state.kl_kuerzel)

    st.sidebar.title("📌 Gliederung")

    user_input = st.text_area(
        "Gutachten-Text",
        value=st.session_state.klausur_text,
        height=700,
        key="klausur_text"
    )

    col_pdf, col_save, col_load = st.columns(3)

    with col_save:
        if st.button("💾 Als TXT speichern", type="secondary"):
            txt = (
                f"# TITEL: {kl_titel}\n"
                f"# DATUM: {kl_datum}\n"
                f"# KUERZEL: {kl_kuerzel}\n"
                "---\n"
                f"{user_input}"
            )
            st.download_button(
                "📥 Download TXT",
                txt,
                f"Klausur_{kl_kuerzel}.txt",
                "text/plain"
            )

    with col_load:
        st.file_uploader(
            "📂 Klausur laden",
            type=["txt"],
            key="uploader_key",
            on_change=load_klausur
        )

    if st.session_state.show_success:
        st.success("✅ Klausur geladen!")
        st.session_state.show_success = False


if __name__ == "__main__":
    main()

