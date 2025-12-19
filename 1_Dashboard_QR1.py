import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io


from db import kpis, list_actions, get_list



st.title("Dashboard QR1 – Vue 1 page")
st.caption("Ce qu’on traite aujourd’hui : priorités, retards, blocages, pareto, clôtures.")

# KPIs
k = kpis()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Actions ouvertes", k["open"])
c2.metric("En retard", k["late"])
c3.metric("Bloquées", k["blocked"])
c4.metric("Clôturées (7 jours)", k["closed_7d"])

st.divider()

st.subheader("📤 Export")
export_df = list_actions({"only_open": False})
if export_df.empty:
    st.info("Rien à exporter pour le moment.")
else:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Actions")
    st.download_button(
        label="Exporter Excel",
        data=buffer.getvalue(),
        file_name="QR1_Actions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
st.divider()


# Filtres QR1 (optionnels)
deps = ["Tous"] + get_list("departments")
types = ["Tous"] + get_list("types")

fc1, fc2, fc3 = st.columns(3)
with fc1:
    dept = st.selectbox("Département", deps, index=0)
with fc2:
    typ = st.selectbox("Type", types, index=0)
with fc3:
    show_open_only = st.checkbox("Afficher seulement ouvertes", value=True)

df = list_actions({
    "dept_owner": dept,
    "type": typ,
    "only_open": show_open_only
})

if df.empty:
    st.warning("Aucune action avec ces filtres.")
    st.stop()

# TOP Priorités (P1/P2) triées par échéance
st.subheader("🎯 Top priorités (P1/P2) – à traiter au QR1")
top = df[(df["priority"].isin(["P1", "P2"])) & (~df["status"].isin(["Fait", "Annulé"]))].copy()
top = top.sort_values(["priority", "due_date"], ascending=[True, True]).head(10)

show_cols = ["action_id", "type", "problem", "dept_owner", "owner_name", "due_date", "status", "next_step"]
st.dataframe(top[show_cols], use_container_width=True, height=260)

st.divider()

# Blocages
st.subheader("🚧 Actions bloquées / escalades")
blocked = df[df["status"] == "Bloqué"].copy()
blocked = blocked.sort_values(["priority", "due_date"], ascending=[True, True]).head(10)
show_cols_b = ["action_id", "type", "problem", "blockage", "dept_owner", "owner_name", "support_needed", "due_date", "next_step"]
st.dataframe(blocked[show_cols_b], use_container_width=True, height=220)

st.divider()

# Pareto Type (sur ouvertes)
st.subheader("📊 Pareto (actions ouvertes par type)")
open_df = df[~df["status"].isin(["Fait", "Annulé"])].copy()
pareto = open_df.groupby("type")["action_id"].count().sort_values(ascending=False).reset_index()
pareto.columns = ["type", "count"]
st.bar_chart(pareto, x="type", y="count")

st.divider()

# Clôtures 7 jours
st.subheader("✅ Clôturées (7 jours)")
today = date.today()
last7 = today - timedelta(days=7)
closed = list_actions({"only_open": False})
if not closed.empty:
    closed = closed[(closed["status"] == "Fait") & (closed["closed_at"].notna()) & (closed["closed_at"] >= last7)].copy()
    closed = closed.sort_values("closed_at", ascending=False)
    st.dataframe(closed[["action_id","type","problem","dept_owner","owner_name","closed_at","standard_updated","proof_link"]],
                 use_container_width=True, height=220)
else:
    st.info("Aucune clôture récente.")
