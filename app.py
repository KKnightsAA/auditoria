import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Auditoría Móvil de Edificio",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATA_DIR = Path(__file__).parent / "data"
PHOTOS_DIR = DATA_DIR / "photos"
DATA_DIR.mkdir(exist_ok=True)
PHOTOS_DIR.mkdir(exist_ok=True)

STATUS_OPTIONS = ["Pendiente", "Perfecto estado", "Necesita mantenimiento", "Mal estado", "No aplica"]
STATUS_FACTOR = {
    "Pendiente": None,
    "Perfecto estado": 1.0,
    "Necesita mantenimiento": 0.5,
    "Mal estado": 0.0,
    "No aplica": None,
}
ACTION_OPTIONS = [
    "Sin acción",
    "Programar mantención",
    "Escalar a proveedor",
    "Revisar urgente",
]

CHECKLIST = [
    {
        "space": "Accesos y control",
        "weight": 12,
        "items": [
            ("Limpieza y orden de accesos", 3),
            ("Pintura y terminaciones visibles", 2),
            ("Iluminación exterior y señalética", 3),
            ("Puertas / citófono / control de acceso", 4),
        ],
    },
    {
        "space": "Hall y recepción",
        "weight": 12,
        "items": [
            ("Imagen general limpia y cuidada", 3),
            ("Pintura de muros, cielos y zócalos", 3),
            ("Iluminación del hall y recepción", 2),
            ("Mobiliario, vidrios y mesón", 2),
            ("Circulación libre y señalización visible", 2),
        ],
    },
    {
        "space": "Pasillos y escaleras",
        "weight": 12,
        "items": [
            ("Pasillos limpios, secos y sin obstrucciones", 3),
            ("Pintura y terminaciones de muros y cielos", 3),
            ("Iluminación y señalización de circulación", 3),
            ("Barandas, pasamanos y puertas cortafuego", 3),
        ],
    },
    {
        "space": "Ascensores",
        "weight": 12,
        "items": [
            ("Limpieza interior de cabina", 2),
            ("Terminaciones visibles de cabina", 2),
            ("Botones, indicadores y alarma", 3),
            ("Puertas y funcionamiento general", 5),
        ],
    },
    {
        "space": "Áreas verdes y exteriores",
        "weight": 10,
        "items": [
            ("Limpieza, poda y orden general", 3),
            ("Mobiliario exterior y terminaciones", 2),
            ("Iluminación exterior cercana", 2),
            ("Ausencia de residuos o daños visibles", 3),
        ],
    },
    {
        "space": "Quinchos / terraza / eventos",
        "weight": 12,
        "items": [
            ("Limpieza del espacio y residuos", 3),
            ("Pintura, muros y terminaciones", 2),
            ("Parrillas, mesones o lavaplatos", 4),
            ("Iluminación y enchufes visibles", 3),
        ],
    },
    {
        "space": "Estacionamientos",
        "weight": 12,
        "items": [
            ("Limpieza general y ausencia de derrames", 3),
            ("Pintura y demarcación", 3),
            ("Iluminación del estacionamiento", 3),
            ("Portones / barreras / acceso vehicular", 3),
        ],
    },
    {
        "space": "Zona de basura y residuos",
        "weight": 8,
        "items": [
            ("Limpieza y ausencia de derrames", 3),
            ("Pintura, pisos y terminaciones", 1),
            ("Contenedores y cierre del espacio", 2),
            ("Ventilación, olores y orden general", 2),
        ],
    },
    {
        "space": "Sala técnica / equipos visibles",
        "weight": 10,
        "items": [
            ("Orden y limpieza del espacio técnico", 2),
            ("Pintura / pisos / terminaciones", 1),
            ("Sin filtraciones, alertas o ruidos anormales", 4),
            ("Señalización y acceso restringido", 3),
        ],
    },
]

assert sum(space["weight"] for space in CHECKLIST) == 100


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9áéíóúñü]+", "_", text)
    return text.strip("_")


def inject_css():
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 560px;
                padding-top: 1rem;
                padding-bottom: 4rem;
            }
            [data-testid="stMetricValue"] {
                font-size: 2rem;
            }
            .hero-card {
                background: linear-gradient(135deg, #f7fbff 0%, #eaf3ff 100%);
                border: 1px solid #d8e8ff;
                border-radius: 22px;
                padding: 18px 18px 14px 18px;
                margin-bottom: 12px;
            }
            .section-card {
                background: white;
                border: 1px solid #e6eef7;
                border-radius: 18px;
                padding: 12px 14px;
                margin-bottom: 14px;
                box-shadow: 0 6px 16px rgba(14, 49, 94, 0.04);
            }
            .item-card {
                background: #ffffff;
                border: 1px solid #edf2f8;
                border-radius: 16px;
                padding: 12px 12px 8px 12px;
                margin-bottom: 14px;
            }
            .muted {
                color: #64748b;
                font-size: 0.92rem;
            }
            .space-title {
                font-weight: 700;
                font-size: 1.05rem;
                color: #15314b;
            }
            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                background: #e9f2ff;
                color: #245fdd;
                font-size: 0.80rem;
                font-weight: 600;
            }
            .summary-good {
                color: #0f9d68;
                font-weight: 700;
            }
            .summary-alert {
                color: #d97706;
                font-weight: 700;
            }
            .summary-bad {
                color: #dc2626;
                font-weight: 700;
            }
            div[data-testid="stRadio"] > label {
                font-weight: 600;
            }
            .small-label {
                font-size: 0.9rem;
                font-weight: 600;
                color: #334155;
                margin-bottom: 0.2rem;
            }
            div[data-baseweb="select"] > div {
                border-radius: 12px;
                border-color: #d9e6f5;
                min-height: 48px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    if "audit_meta" not in st.session_state:
        st.session_state.audit_meta = {
            "building": "Edificio MQ Centro",
            "auditor": "",
            "audit_type": "Semanal",
            "sector": "General",
            "general_notes": "",
        }
    if "responses" not in st.session_state:
        st.session_state.responses = {}
        for space in CHECKLIST:
            for question, weight in space["items"]:
                key = f"{space['space']}|{question}"
                st.session_state.responses[key] = {
                    "status": "Pendiente",
                    "observation": "",
                    "action": "Sin acción",
                }
    if "saved_message" not in st.session_state:
        st.session_state.saved_message = ""


def calculate_score():
    obtained = 0.0
    applicable = 0.0
    answered = 0
    total_questions = 0
    issues = []

    for space in CHECKLIST:
        for question, weight in space["items"]:
            total_questions += 1
            key = f"{space['space']}|{question}"
            entry = st.session_state.responses[key]
            status = entry["status"]
            factor = STATUS_FACTOR.get(status)

            if status != "Pendiente":
                answered += 1
            if status == "No aplica":
                continue
            if factor is not None:
                applicable += weight
                obtained += weight * factor
            if status in ["Necesita mantenimiento", "Mal estado"]:
                issues.append(
                    {
                        "Espacio": space["space"],
                        "Pregunta": question,
                        "Estado": status,
                        "Acción": entry["action"],
                        "Observación": entry["observation"],
                        "Peso": weight,
                    }
                )

    score = round((obtained / applicable) * 100, 1) if applicable > 0 else 0.0
    progress = round((answered / total_questions) * 100, 1) if total_questions else 0.0
    return score, progress, issues, answered, total_questions


def score_label(score: float):
    if score >= 90:
        return "Estándar alto", "summary-good"
    if score >= 80:
        return "Buen estado general", "summary-good"
    if score >= 70:
        return "Aceptable con mejoras", "summary-alert"
    if score >= 60:
        return "Requiere plan de acción", "summary-alert"
    return "Brechas relevantes", "summary-bad"


def save_audit():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    score, progress, issues, answered, total_questions = calculate_score()

    rows = []
    for space in CHECKLIST:
        for question, weight in space["items"]:
            key = f"{space['space']}|{question}"
            entry = st.session_state.responses[key]
            row = {
                "timestamp": timestamp,
                "building": st.session_state.audit_meta["building"],
                "auditor": st.session_state.audit_meta["auditor"],
                "audit_type": st.session_state.audit_meta["audit_type"],
                "sector": st.session_state.audit_meta["sector"],
                "space": space["space"],
                "question": question,
                "weight": weight,
                "status": entry["status"],
                "action": entry["action"],
                "observation": entry["observation"],
                "score_total": score,
                "progress": progress,
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = DATA_DIR / "auditorias_detalle.csv"
    if csv_path.exists():
        old = pd.read_csv(csv_path)
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(csv_path, index=False)

    summary = {
        "timestamp": timestamp,
        "meta": st.session_state.audit_meta,
        "score": score,
        "progress": progress,
        "answered": answered,
        "total_questions": total_questions,
        "issues": issues,
        "general_notes": st.session_state.audit_meta["general_notes"],
    }
    json_path = DATA_DIR / f"auditoria_{timestamp}.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    st.session_state.saved_message = f"Auditoría guardada: {json_path.name}"


def header():
    st.markdown(
        """
        <div class="hero-card">
            <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                <div>
                    <div style="font-size:1.25rem; font-weight:800; color:#16324d;">Auditoría móvil del edificio</div>
                    <div class="muted">Checklist por espacios, foto por hallazgo y score sobre 100.</div>
                </div>
                <div class="badge">Móvil first</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_meta():
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Inicio de auditoría")
    b1, b2 = st.columns(2)
    with b1:
        st.session_state.audit_meta["building"] = st.selectbox(
            "Edificio",
            ["Edificio MQ Centro", "Edificio MQ Parque", "Edificio MQ Vista", "Edificio demo"],
            index=0,
        )
        st.session_state.audit_meta["audit_type"] = st.selectbox(
            "Tipo de auditoría", ["Semanal", "Mensual profunda"], index=0
        )
    with b2:
        st.session_state.audit_meta["auditor"] = st.text_input(
            "Auditor", value=st.session_state.audit_meta.get("auditor", "")
        )
        st.session_state.audit_meta["sector"] = st.text_input(
            "Sector / torre", value=st.session_state.audit_meta.get("sector", "General")
        )
    st.session_state.audit_meta["general_notes"] = st.text_area(
        "Observación general",
        value=st.session_state.audit_meta.get("general_notes", ""),
        placeholder="Ej. Se observó mayor desgaste en hall y dos luminarias apagadas en piso 4.",
        height=90,
    )
    st.markdown('</div>', unsafe_allow_html=True)


def render_dashboard():
    score, progress, issues, answered, total_questions = calculate_score()
    label, css = score_label(score)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Score edificio", f"{score}/100")
    with c2:
        st.metric("Progreso", f"{answered}/{total_questions}")
    st.progress(progress / 100)
    st.markdown(
        f"<div class='{css}' style='margin-top:6px; margin-bottom:8px;'>{label}</div>",
        unsafe_allow_html=True,
    )
    if issues:
        st.caption(f"Hallazgos activos: {len(issues)}")
    else:
        st.caption("Sin hallazgos activos todavía.")


def render_space(space):
    total_weight = sum(weight for _, weight in space["items"])
    with st.expander(f"{space['space']} · {total_weight} pts", expanded=False):
        st.markdown(
            f"<div class='space-title'>{space['space']}</div><div class='muted'>Marca el estado de cada punto. Si hay hallazgo, agrega foto y observación.</div>",
            unsafe_allow_html=True,
        )
        for idx, (question, weight) in enumerate(space["items"]):
            key = f"{space['space']}|{question}"
            entry = st.session_state.responses[key]
            st.markdown('<div class="item-card">', unsafe_allow_html=True)
            st.markdown(f"**{question}**  ")
            st.caption(f"Puntaje máximo: {weight}")

            entry["status"] = st.selectbox(
                "Estado",
                STATUS_OPTIONS,
                key=f"status_{slugify(key)}",
                index=STATUS_OPTIONS.index(entry["status"]),
                help="Selecciona el estado del ítem auditado.",
            )

            if entry["status"] in ["Necesita mantenimiento", "Mal estado"]:
                a1, a2 = st.columns([1, 1])
                with a1:
                    entry["action"] = st.selectbox(
                        "Acción requerida",
                        ACTION_OPTIONS,
                        key=f"action_{slugify(key)}",
                        index=ACTION_OPTIONS.index(entry.get("action", "Sin acción")),
                    )
                with a2:
                    st.markdown("<div class='small-label'>Foto de respaldo</div>", unsafe_allow_html=True)
                    uploaded = st.camera_input(
                        "Tomar foto",
                        key=f"camera_{slugify(key)}",
                        label_visibility="collapsed",
                    )
                    if uploaded:
                        st.success("Foto capturada")
                entry["observation"] = st.text_area(
                    "Observación",
                    key=f"obs_{slugify(key)}",
                    value=entry.get("observation", ""),
                    height=80,
                    placeholder="Describe brevemente el hallazgo y el contexto.",
                )
            else:
                entry["action"] = "Sin acción"
                entry["observation"] = entry.get("observation", "")
            st.markdown('</div>', unsafe_allow_html=True)
            st.session_state.responses[key] = entry


def render_summary():
    score, progress, issues, answered, total_questions = calculate_score()
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Resumen final")
    st.write(
        "Revisa el score, los hallazgos y guarda la auditoría. Luego podrás usar esta base para crear seguimiento interno."
    )

    if issues:
        df = pd.DataFrame(issues)
        st.dataframe(df[["Espacio", "Pregunta", "Estado", "Acción"]], hide_index=True, use_container_width=True)
    else:
        st.success("No se detectaron hallazgos en esta auditoría.")

    pending = []
    for space in CHECKLIST:
        for question, _ in space["items"]:
            key = f"{space['space']}|{question}"
            if st.session_state.responses[key]["status"] == "Pendiente":
                pending.append(key)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Guardar auditoría", use_container_width=True, type="primary"):
            if pending:
                st.error(f"Aún hay {len(pending)} preguntas pendientes por responder.")
            elif not st.session_state.audit_meta["auditor"].strip():
                st.error("Ingresa el nombre del auditor antes de guardar.")
            else:
                save_audit()
                st.success(st.session_state.saved_message)
    with col2:
        if st.button("Reiniciar respuestas", use_container_width=True):
            for key in st.session_state.responses.keys():
                st.session_state.responses[key] = {
                    "status": "Pendiente",
                    "observation": "",
                    "action": "Sin acción",
                }
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def architecture_view():
    with st.expander("Cómo se desarrollaría esta auditoría móvil"):
        st.markdown(
            """
            **Flujo recomendado**

            1. **Inicio móvil**: auditor selecciona edificio, sector y tipo de revisión.  
            2. **Checklist por espacios**: preguntas cortas, estados rápidos y foto solo cuando hay hallazgo.  
            3. **Score automático**: cálculo sobre 100 con resumen por espacio.  
            4. **Guardado**: cada auditoría queda persistida y lista para dashboard.  
            5. **Seguimiento**: los hallazgos pueden transformarse luego en tickets internos.

            **Arquitectura MVP**
            - Front móvil: Streamlit
            - Persistencia inicial: CSV / JSON local
            - Evidencia: fotos capturadas desde celular
            - Evolución futura: base de datos + dashboard + integración con tickets
            """
        )


def main():
    inject_css()
    init_state()
    header()
    render_meta()
    render_dashboard()
    architecture_view()
    st.markdown("### Checklist por espacios")
    for space in CHECKLIST:
        render_space(space)
    render_summary()


if __name__ == "__main__":
    main()
