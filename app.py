import streamlit as st
import re
import os
import subprocess
import tempfile

# 1. Einfache Gliederungs-Erkennung
def erstelle_gliederung(text):
    gliederung = []
    lines = text.split('\n')
    for line in lines:
        # Wir suchen nach einem Buchstaben/Zahl gefolgt von einem Sternchen
        if "*" in line:
            parts = line.split("*", 1)
            marker = parts[0].strip()
            titel = parts[1].strip()
            # Wir speichern einfach, was wir finden
            gliederung.append(f"Gefunden: {marker} -> {titel}")
    return gliederung

# 2. Web-Oberfläche
st.set_page_config(layout="wide")
st.title("LexGerm Test-Editor")

col1, col2 = st.columns([2, 1])

with col1:
    text_input = st.text_area("Schreibe hier (Beispiel: A* Anspruch):", height=400)

with col2:
    st.subheader("Ergebnis der Erkennung:")
    ergebnisse = erstelle_gliederung(text_input)
    if ergebnisse:
        for e in ergebnisse:
            st.write(e)
    else:
        st.info("Tippe etwas mit einem Sternchen (z.B. A*), um die Erkennung zu testen.")

# 3. Minimaler PDF-Test
if st.button("PDF Test-Lauf"):
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "test.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(r"\documentclass{article}\begin{document}Test\end{document}")
        try:
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "test.tex"], cwd=tmpdir, check=True)
            st.success("LaTeX auf dem Server funktioniert!")
        except Exception as e:
            st.error(f"LaTeX-Fehler: {e}")
