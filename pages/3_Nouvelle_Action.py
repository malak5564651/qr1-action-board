import streamlit as st
from datetime import date

from db import (
    next_action_id, create_action, validate_action_fields,
    get_list
)


st.title("Nouvelle action – Capture d’un irritant / problème")
st.caption("Objectif : 30 secondes pour créer une action actionnable (responsable + échéance + priorité).")

departments = get_list("departments")
types = get_list("types")
m6 = get_list("m6")
statuses = get_list("statuses")
priorities = get_list("priorities")
blockages = [""] + get_list("blockages")
kinds = [""] + get_list("action_kinds")

with st.form("new_action", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        created_by = st.text_input("Créé par (nom / service)", value="")
        dept_owner = st.selectbox("Département responsable *", departments, index=0)
        owner_name = st.text_input("Responsable *", value="")
    with c2:
        typ = st.selectbox("Type *", types, index=1 if "Qualité" in types else 0)
        m6_sel = st.selectbox("6M (optionnel)", [""] + m6, index=0)
        priority = st.selectbox("Priorité *", priorities, index=2 if "P3" in priorities else 0)
    with c3:
        status = st.selectbox("Statut *", statuses, index=0)
        due_date = st.date_input("Échéance *", value=date.today())
        support_needed = st.text_input("Support requis (optionnel)", value="")

    c4, c5, c6 = st.columns(3)
    with c4:
        zone = st.text_input("Zone (ex: Contrôle final, Kitting, Ligne 2…)", value="")
        line = st.text_input("Ligne (optionnel)", value="")
        machine = st.text_input("Poste/Machine (optionnel)", value="")
    with c5:
        impact = st.text_input("Impact (ex: 12 NOK/j, 25 min/shift…)", value="")
        action_kind = st.selectbox("Type d’action (optionnel)", kinds, index=0)
        quality_validation_required = st.checkbox("Validation Qualité requise ?", value=False)
    with c6:
        standard_updated = st.checkbox("Standard impacté / mis à jour ?", value=False)
        proof_link = st.text_input("Preuve (lien) (optionnel, utile à la clôture)", value="")
        blockage = st.selectbox("Blocage (si Bloqué)", blockages, index=0)

    problem = st.text_area("Problème (factuel) *", value="", height=90, placeholder="Ex: Rayure sur pièce lors du montage à l’étape X")
    containment = st.text_area("Containment immédiat (optionnel)", value="", height=70, placeholder="Ex: Trier 100% temporairement, isoler lot…")
    countermeasure = st.text_area("Action / Contre-mesure *", value="", height=90, placeholder="Ex: Ajouter protection mousse + standard manipulation")
    next_step = st.text_area("Prochaine étape (obligatoire si En cours/Bloqué)", value="", height=70)

    submitted = st.form_submit_button("✅ Créer l’action")

    if submitted:
        if not problem.strip():
            st.error("Le problème est obligatoire.")
            st.stop()
        if not countermeasure.strip():
            st.error("L’action / contre-mesure est obligatoire.")
            st.stop()

        ok, msg = validate_action_fields(
            status=status,
            owner_name=owner_name,
            dept_owner=dept_owner,
            due_date=due_date,
            next_step=next_step,
            blockage=blockage,
            proof_link=proof_link,
        )
        if not ok:
            st.error(msg)
            st.stop()

        payload = {
            "action_id": next_action_id(),
            "created_by": created_by.strip(),
            "zone": zone.strip(),
            "line": line.strip(),
            "machine": machine.strip(),
            "type": typ,
            "m6": m6_sel.strip(),
            "problem": problem.strip(),
            "impact": impact.strip(),
            "containment": containment.strip(),
            "countermeasure": countermeasure.strip(),
            "action_kind": action_kind.strip(),
            "dept_owner": dept_owner,
            "owner_name": owner_name.strip(),
            "support_needed": support_needed.strip(),
            "priority": priority,
            "due_date": due_date,
            "status": status,
            "blockage": blockage.strip(),
            "next_step": next_step.strip(),
            "proof_link": proof_link.strip(),
            "standard_updated": bool(standard_updated),
            "quality_validation_required": bool(quality_validation_required),
        }

        create_action(payload)
        st.success(f"Action créée : {payload['action_id']}")
        st.info("Va sur Dashboard QR1 pour la voir dans les priorités / blocages.")
