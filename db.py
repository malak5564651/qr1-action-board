from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, DateTime, Boolean, Text,
    select, func, delete, update
)
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = "sqlite:///qr1_actions.db"

engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


# -------------------- MODELS --------------------
class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String(20), unique=True, index=True)  # A-0001...
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), default="")

    zone = Column(String(100), default="")
    line = Column(String(100), default="")
    machine = Column(String(100), default="")

    type = Column(String(50), default="")        # Qualité/Performance/Flux/5S/Sécurité
    m6 = Column(String(30), default="")          # Machine/Méthode/...

    problem = Column(Text, default="")
    impact = Column(String(200), default="")

    containment = Column(Text, default="")
    root_cause = Column(Text, default="")
    countermeasure = Column(Text, default="")
    action_kind = Column(String(50), default="")  # Containment/Corrective/Préventive/Standardisation

    dept_owner = Column(String(50), default="")   # ASSY/Lean/Maintenance/Engi/Qualité
    owner_name = Column(String(100), default="")
    support_needed = Column(String(200), default="")

    priority = Column(String(10), default="P3")   # P1/P2/P3
    due_date = Column(Date, nullable=True)

    status = Column(String(20), default="À faire")  # À faire/En cours/Bloqué/Fait/Annulé
    blockage = Column(String(200), default="")
    next_step = Column(Text, default="")

    closed_at = Column(Date, nullable=True)
    proof_link = Column(String(300), default="")
    standard_updated = Column(Boolean, default=False)
    quality_validation_required = Column(Boolean, default=False)


class ListValue(Base):
    __tablename__ = "list_values"
    id = Column(Integer, primary_key=True, autoincrement=True)
    list_name = Column(String(50), index=True)  # departments, types, statuses...
    value = Column(String(200), index=True)


# -------------------- INIT / SEED --------------------
DEFAULT_LISTS: Dict[str, List[str]] = {
    "departments": ["ASSY", "Lean", "Maintenance", "Engi", "Qualité"],
    "types": ["Sécurité", "Qualité", "Performance", "Flux", "5S / Ergonomie"],
    "m6": ["Machine", "Méthode", "Main d’œuvre", "Matière", "Milieu", "Mesure"],
    "statuses": ["À faire", "En cours", "Bloqué", "Fait", "Annulé"],
    "priorities": ["P1", "P2", "P3"],
    "blockages": [
        "Attente diagnostic",
        "Attente pièce / spare",
        "Attente validation Qualité",
        "Attente fenêtre arrêt machine",
        "Attente décision Engi",
        "Attente formation / doc",
        "Autre",
    ],
    "action_kinds": ["Containment", "Corrective", "Préventive", "Standardisation"],
}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_default_lists()


def seed_default_lists() -> None:
    with SessionLocal() as s:
        existing = s.execute(select(func.count(ListValue.id))).scalar_one()
        if existing and existing > 0:
            return
        for list_name, vals in DEFAULT_LISTS.items():
            for v in vals:
                s.add(ListValue(list_name=list_name, value=v))
        s.commit()


def get_list(list_name: str) -> List[str]:
    with SessionLocal() as s:
        rows = s.execute(
            select(ListValue.value).where(ListValue.list_name == list_name).order_by(ListValue.value)
        ).all()
    return [r[0] for r in rows]


def add_list_value(list_name: str, value: str) -> None:
    value = value.strip()
    if not value:
        return
    with SessionLocal() as s:
        exists = s.execute(
            select(ListValue.id).where(ListValue.list_name == list_name, ListValue.value == value)
        ).first()
        if exists:
            return
        s.add(ListValue(list_name=list_name, value=value))
        s.commit()


def delete_list_value(list_name: str, value: str) -> None:
    with SessionLocal() as s:
        s.execute(delete(ListValue).where(ListValue.list_name == list_name, ListValue.value == value))
        s.commit()


# -------------------- ACTION ID --------------------
def next_action_id() -> str:
    with SessionLocal() as s:
        last = s.execute(select(func.max(Action.id))).scalar_one()
    n = (last or 0) + 1
    return f"A-{n:04d}"


# -------------------- VALIDATION RULES (LEAN) --------------------
def validate_action_fields(
    status: str,
    owner_name: str,
    dept_owner: str,
    due_date: Optional[date],
    next_step: str,
    blockage: str,
    proof_link: str,
) -> Tuple[bool, str]:
    if not owner_name.strip():
        return False, "Responsable obligatoire."
    if not dept_owner.strip():
        return False, "Département responsable obligatoire."
    if due_date is None:
        return False, "Échéance obligatoire."

    if status in ["En cours", "Bloqué"] and not next_step.strip():
        return False, "Prochaine étape obligatoire si Statut = En cours / Bloqué."

    if status == "Bloqué" and not blockage.strip():
        return False, "Blocage obligatoire si Statut = Bloqué."

    if status == "Fait" and not proof_link.strip():
        return False, "Preuve (lien) recommandée pour clôturer (Statut = Fait)."

    return True, ""


# -------------------- CRUD --------------------
def create_action(payload: Dict[str, Any]) -> None:
    with SessionLocal() as s:
        s.add(Action(**payload))
        s.commit()


def list_actions(filters: Dict[str, Any] | None = None) -> pd.DataFrame:
    filters = filters or {}
    stmt = select(Action)

    # Filters
    if filters.get("dept_owner") and filters["dept_owner"] != "Tous":
        stmt = stmt.where(Action.dept_owner == filters["dept_owner"])
    if filters.get("type") and filters["type"] != "Tous":
        stmt = stmt.where(Action.type == filters["type"])
    if filters.get("status") and filters["status"] != "Tous":
        stmt = stmt.where(Action.status == filters["status"])
    if filters.get("priority") and filters["priority"] != "Tous":
        stmt = stmt.where(Action.priority == filters["priority"])
    if filters.get("only_open"):
        stmt = stmt.where(Action.status.notin_(["Fait", "Annulé"]))

    # Search (problem/countermeasure)
    q = (filters.get("search") or "").strip()
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Action.problem.like(like)) | (Action.countermeasure.like(like)))

    stmt = stmt.order_by(Action.priority.asc(), Action.due_date.asc().nullslast(), Action.id.desc())

    with SessionLocal() as s:
        rows = s.execute(stmt).scalars().all()

    data = []
    for a in rows:
        data.append({
            "action_id": a.action_id,
            "created_at": a.created_at,
            "created_by": a.created_by,
            "zone": a.zone,
            "line": a.line,
            "machine": a.machine,
            "type": a.type,
            "m6": a.m6,
            "problem": a.problem,
            "impact": a.impact,
            "containment": a.containment,
            "root_cause": a.root_cause,
            "countermeasure": a.countermeasure,
            "action_kind": a.action_kind,
            "dept_owner": a.dept_owner,
            "owner_name": a.owner_name,
            "support_needed": a.support_needed,
            "priority": a.priority,
            "due_date": a.due_date,
            "status": a.status,
            "blockage": a.blockage,
            "next_step": a.next_step,
            "closed_at": a.closed_at,
            "proof_link": a.proof_link,
            "standard_updated": bool(a.standard_updated),
            "quality_validation_required": bool(a.quality_validation_required),
        })

    df = pd.DataFrame(data)
    if df.empty:
        return df

    today = date.today()
    df["is_late"] = df.apply(
        lambda r: (r["status"] not in ["Fait", "Annulé"]) and pd.notna(r["due_date"]) and (r["due_date"] < today),
        axis=1,
    )
    df["age_days"] = (pd.to_datetime(today) - pd.to_datetime(df["created_at"]).dt.normalize()).dt.days
    return df


def update_actions_from_df(df_updates: pd.DataFrame) -> None:
    """
    df_updates must include 'action_id' and fields to update.
    """
    if df_updates.empty:
        return

    with SessionLocal() as s:
        for _, r in df_updates.iterrows():
            a = s.execute(select(Action).where(Action.action_id == r["action_id"])).scalar_one_or_none()
            if not a:
                continue

            # Apply updates (only keys we expect)
            for k in [
                "dept_owner", "owner_name", "support_needed", "priority", "due_date",
                "status", "blockage", "next_step", "proof_link",
                "standard_updated", "quality_validation_required",
            ]:
                if k in r:
                    setattr(a, k, r[k])

            # Auto close date when "Fait"
            if a.status == "Fait" and a.closed_at is None:
                a.closed_at = date.today()
            if a.status != "Fait":
                a.closed_at = None

        s.commit()


# -------------------- DASHBOARD QUERIES --------------------
def kpis() -> Dict[str, Any]:
    today = date.today()
    last7 = today - timedelta(days=7)

    with SessionLocal() as s:
        total_open = s.execute(
            select(func.count(Action.id)).where(Action.status.notin_(["Fait", "Annulé"]))
        ).scalar_one()

        total_late = s.execute(
            select(func.count(Action.id)).where(
                Action.status.notin_(["Fait", "Annulé"]),
                Action.due_date.isnot(None),
                Action.due_date < today
            )
        ).scalar_one()

        total_blocked = s.execute(
            select(func.count(Action.id)).where(Action.status == "Bloqué")
        ).scalar_one()

        closed_7d = s.execute(
            select(func.count(Action.id)).where(
                Action.status == "Fait",
                Action.closed_at.isnot(None),
                Action.closed_at >= last7
            )
        ).scalar_one()

    return {
        "open": int(total_open or 0),
        "late": int(total_late or 0),
        "blocked": int(total_blocked or 0),
        "closed_7d": int(closed_7d or 0),
    }
