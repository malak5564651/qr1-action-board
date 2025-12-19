import streamlit as st
from db import init_db

st.set_page_config(page_title="QR1 Action Board", layout="wide")
init_db()

st.title("QR1 Action Board")
st.caption("Pilotage quotidien – Lean / ASSY / Maintenance / Engi / Qualité")

st.info("Utilise le menu à gauche (pages) : Dashboard QR1, Actions, Nouvelle Action.")
