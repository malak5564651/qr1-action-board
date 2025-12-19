import streamlit as st
import pandas as pd

from db import list_actions, update_actions_from_df, get_list


st.title("Actions – Liste & mise à jour")
st.caption("Filtrer, rechercher, et mettre à jour rapidement : statut, échéance, prochaine étape, blocage.")

deps = ["Tous"] + get_list("departments")
types = ["Tous"] + get_list("types")
statuses = ["Tous"] + get_list("statuses")
priorities = ["Tous"] + get_list("priorities")

f1, f2, f3, f4, f5 = st.columns([1,1,1,1,2])
with f1:
    dept = st.selectbox("Département", deps, index=0)
with f2:
    typ = st.selectbox("Type", types, index=0)
with f3:
    status = st.selectbox("Statut", statuses, index=0)
with f4:
    prio = st.selectbox("Priorité", priorities, index=0)
with f5:
    search = st.text_input("Recherche (problème / action)", value="")

only_open = st.checkbox("Seulement ouvertes (≠ Fait/Annulé)", value=False)

df = list_actions({
    "dept_owner": dept,
    "type": typ,
    "status": status,
    "priority": prio,
    "search": search,
    "only_open": only_open
})

if df.empty:
    st.warning("Aucune action.")
    st.stop()

st.divider()

st.subheader("Tableau (édition rapide)")

# On montre une table éditable limitée aux champs de pilotage
edit_cols = [
    "action_id", "dept_owner", "owner_name", "support_needed",
    "priority", "due_date", "status", "blockage", "next_step",
    "proof_link", "standard_updated", "quality_validation_required"
]
view = df[edit_cols].copy()

# Rendre action_id non editable
edited = st.data_editor(
    view,
    use_container_width=True,
    height=520,
    disabled=["action_id"],
    column_config={
        "standard_updated": st.column_config.CheckboxColumn("Standard mis à jour ?"),
        "quality_validation_required": st.column_config.CheckboxColumn("Validation Qualité ?"),
    }
)

colA, colB = st.columns([1,3])
with colA:
    if st.button("💾 Enregistrer les modifications"):
        # On enregistre seulement les lignes qui ont changé
        # (simple : on compare dataframe)
        diff_mask = (edited != view).any(axis=1)
        changes = edited.loc[diff_mask].copy()
        if changes.empty:
            st.info("Aucune modification détectée.")
        else:
            update_actions_from_df(changes)
            st.success(f"Modifications enregistrées : {len(changes)} ligne(s).")
            st.rerun()

with colB:
    st.info("Règle Lean : si Statut = Bloqué → renseigne Blocage + Prochaine étape. Si Statut = Fait → ajoute une preuve (lien).")
