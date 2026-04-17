import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Auditoría Móvil de Edificio version 2",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATA_DIR = Path(__file__).parent / "data"
MEDIA_DIR = DATA_DIR / "media"
DATA_DIR.mkdir(exist_ok=True)
MEDIA_DIR.mkdir(exist_ok=True)

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
            for question, _ in space["items"]:
                key = f"{space['space']}|{question}"
                st.session_state.responses[key] = {
                    "status": "Pendiente",
                    "observation": "",
                    "action": "Sin acción",
                    "media_saved": [],
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
                        "Evidencias": len(entry.get("media_saved", [])),
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


def build_media_payloads(key: str):
    payloads = []

    quick_photo = st.session_state.get(f"camera_{slugify(key)}")
    if quick_photo is not None:
        payloads.append(
            {
                "source": "camera",
                "name": quick_photo.name or "foto_capturada.jpg",
                "mime": quick_photo.type or "image/jpeg",
                "bytes": quick_photo.getbuffer().tobytes(),
            }
        )

    uploaded_media = st.session_state.get(f"media_{slugify(key)}") or []
    for media in uploaded_media:
        payloads.append(
            {
                "source": "uploader",
                "name": media.name,
                "mime": media.type,
                "bytes": media.getbuffer().tobytes(),
            }
        )

    return payloads



def persist_media_files(timestamp: str, key: str):
    payloads = build_media_payloads(key)
    saved_files = []

    if not payloads:
        return saved_files

    audit_media_dir = MEDIA_DIR / timestamp
    audit_media_dir.mkdir(parents=True, exist_ok=True)

    seen_signatures = set()
    key_slug = slugify(key)

    for idx, payload in enumerate(payloads, start=1):
        raw_bytes = payload["bytes"]
        signature = (payload["name"], len(raw_bytes), payload["mime"])
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        original_suffix = Path(payload["name"] or "archivo").suffix
        suffix = original_suffix or guess_extension(payload["mime"])
        file_name = f"{key_slug}_{idx}{suffix}"
        file_path = audit_media_dir / file_name
        file_path.write_bytes(raw_bytes)

        saved_files.append(
            {
                "name": file_name,
                "original_name": payload["name"],
                "source": payload["source"],
                "mime": payload["mime"],
                "path": str(file_path),
            }
        )

    return saved_files



def guess_extension(mime_type: str | None) -> str:
    mime_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/webm": ".webm",
    }
    return mime_map.get(mime_type or "", ".bin")



def save_audit():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    score, progress, issues, answered, total_questions = calculate_score()

    rows = []
    issues_with_media = []

    for space in CHECKLIST:
        for question, weight in space["items"]:
            key = f"{space['space']}|{question}"
            entry = st.session_state.responses[key]
            saved_media = persist_media_files(timestamp, key)
            entry["media_saved"] = saved_media
            st.session_state.responses[key] = entry

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
                "evidence_count": len(saved_media),
                "evidence_paths": json.dumps([item["path"] for item in saved_media], ensure_ascii=False),
                "score_total": score,
                "progress": progress,
            }
            rows.append(row)

            if entry["status"] in ["Necesita mantenimiento", "Mal estado"]:
                issues_with_media.append(
                    {
                        "Espacio": space["space"],
                        "Pregunta": question,
                        "Estado": entry["status"],
                        "Acción": entry["action"],
                        "Observación": entry["observation"],
                        "Peso": weight,
                        "Evidencias": saved_media,
                    }
                )

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
        "issues": issues_with_media,
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
                    <div class="muted">Checklist por espacios, fotos y videos por hallazgo, con score sobre 100.</div>
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



def render_evidence_preview(key: str):
    quick_photo = st.session_state.get(f"camera_{slugify(key)}")
    uploaded_media = st.session_state.get(f"media_{slugify(key)}") or []

    if quick_photo is not None:
        st.image(quick_photo, caption="Foto rápida capturada", use_container_width=True)

    if uploaded_media:
        st.caption(f"Evidencias seleccionadas: {len(uploaded_media)}")
        for media in uploaded_media:
            mime_type = media.type or ""
            if mime_type.startswith("image/"):
                st.image(media, caption=media.name, use_container_width=True)
            elif mime_type.startswith("video/"):
                st.video(media)
            else:
                st.info(f"Archivo adjunto: {media.name}")



def render_space(space):
    total_weight = sum(weight for _, weight in space["items"])
    with st.expander(f"{space['space']} · {total_weight} pts", expanded=False):
        st.markdown(
            f"<div class='space-title'>{space['space']}</div><div class='muted'>Marca el estado de cada punto. Si hay hallazgo, agrega fotos, video y observación.</div>",
            unsafe_allow_html=True,
        )
        for question, weight in space["items"]:
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
                entry["action"] = st.selectbox(
                    "Acción requerida",
                    ACTION_OPTIONS,
                    key=f"action_{slugify(key)}",
                    index=ACTION_OPTIONS.index(entry.get("action", "Sin acción")),
                )

                st.markdown("<div class='small-label'>Evidencia rápida</div>", unsafe_allow_html=True)
                st.camera_input(
                    "Tomar foto",
                    key=f"camera_{slugify(key)}",
                    label_visibility="collapsed",
                )

                st.markdown("<div class='small-label'>Fotos o video adicionales</div>", unsafe_allow_html=True)
                st.file_uploader(
                    "Subir evidencias",
                    type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "avi", "webm"],
                    accept_multiple_files=True,
                    key=f"media_{slugify(key)}",
                    label_visibility="collapsed",
                    help="Puedes seleccionar varias imágenes y también un video del hallazgo.",
                )

                render_evidence_preview(key)

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



def reset_responses():
    for space in CHECKLIST:
        for question, _ in space["items"]:
            key = f"{space['space']}|{question}"
            st.session_state.responses[key] = {
                "status": "Pendiente",
                "observation": "",
                "action": "Sin acción",
                "media_saved": [],
            }
            for widget_key in [
                f"status_{slugify(key)}",
                f"action_{slugify(key)}",
                f"obs_{slugify(key)}",
                f"camera_{slugify(key)}",
                f"media_{slugify(key)}",
            ]:
                if widget_key in st.session_state:
                    del st.session_state[widget_key]



def render_summary():
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Resumen final")
    st.write(
        "Revisa el score, los hallazgos y guarda la auditoría. Luego podrás usar esta base para crear seguimiento interno."
    )

    score, progress, issues, answered, total_questions = calculate_score()
    if issues:
        df = pd.DataFrame(issues)
        st.dataframe(
            df[["Espacio", "Pregunta", "Estado", "Acción", "Evidencias"]],
            hide_index=True,
            use_container_width=True,
        )
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
            reset_responses()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)



def architecture_view():
    with st.expander("Cómo se desarrollaría esta auditoría móvil"):
        st.markdown(
            """
            **Flujo recomendado**

            1. **Inicio móvil**: auditor selecciona edificio, sector y tipo de revisión.  
            2. **Checklist por espacios**: preguntas cortas, estados rápidos y evidencia multimedia cuando hay hallazgo.  
            3. **Score automático**: cálculo sobre 100 con resumen por espacio.  
            4. **Guardado**: cada auditoría queda persistida y lista para dashboard.  
            5. **Seguimiento**: los hallazgos pueden transformarse luego en tickets internos.

            **Arquitectura MVP**
            - Front móvil: Streamlit
            - Persistencia inicial: CSV / JSON local
            - Evidencia: fotos y videos capturados desde celular
            - Evolución futura: base de datos + dashboard + integración con tickets
            """
        )
        st.caption(
            "Nota: en Streamlit, la foto rápida sí se puede capturar directo. Para video, este MVP usa carga de archivo; en varios móviles eso permite grabar o elegir un video desde la cámara, pero depende del navegador."
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
