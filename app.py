import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Auditoría Móvil de Edificio · v2",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_DIR = Path(__file__).parent
APP_DATA_DIR = APP_DIR / "app_data"
APP_DATA_DIR.mkdir(exist_ok=True)
CONFIG_PATH = APP_DATA_DIR / "config.json"

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
CASE_STATUS_OPTIONS = [
    "Abierto",
    "En revisión",
    "En gestión",
    "Esperando proveedor",
    "Resuelto pendiente validación",
    "Cerrado",
]
PRIORITY_OPTIONS = ["Baja", "Media", "Alta", "Crítica"]
BUILDING_OPTIONS = ["Edificio MQ Centro", "Edificio MQ Parque", "Edificio MQ Vista", "Edificio demo"]

CHECKLIST = [
    {
        "space": "Accesos y control",
        "items": [
            {
                "question": "Limpieza y orden de accesos",
                "weight": 3,
                "description": "Revisa si el acceso principal se encuentra limpio, sin basura, sin tierra acumulada y sin elementos que dificulten el ingreso o den mala imagen.",
            },
            {
                "question": "Pintura y terminaciones visibles",
                "weight": 2,
                "description": "Observa muros, marcos, rejas o pilares del acceso. Busca pintura descascarada, golpes, humedad, óxido o terminaciones deterioradas.",
            },
            {
                "question": "Iluminación exterior y señalética",
                "weight": 2,
                "description": "Confirma si las luces funcionan correctamente y si la señalética de acceso, numeración o indicaciones está visible y legible.",
            },
            {
                "question": "Puertas / citófono / control de acceso",
                "weight": 3,
                "description": "Verifica apertura y cierre, estado de cerraduras, citófono, lector o control. Deben operar sin fallas ni riesgos evidentes.",
            },
        ],
    },
    {
        "space": "Hall y recepción",
        "items": [
            {
                "question": "Imagen general limpia y cuidada",
                "weight": 2,
                "description": "Evalúa la primera impresión del hall: limpieza, orden, aroma, ausencia de basura o elementos fuera de lugar.",
            },
            {
                "question": "Pintura de muros, cielos y zócalos",
                "weight": 2,
                "description": "Busca manchas, rayados, grietas, humedad, pintura saltada o reparaciones visibles mal terminadas.",
            },
            {
                "question": "Iluminación del hall y recepción",
                "weight": 2,
                "description": "Comprueba que todas las luminarias relevantes funcionen y que el espacio tenga visibilidad suficiente y homogénea.",
            },
            {
                "question": "Mobiliario, vidrios y mesón",
                "weight": 2,
                "description": "Revisa limpieza y estado de muebles, vidrios, espejos, mesones y superficies de uso frecuente.",
            },
            {
                "question": "Circulación libre y señalización visible",
                "weight": 2,
                "description": "Asegúrate de que no existan obstáculos, cajas, mobiliario mal ubicado o señalética ausente que complique la circulación.",
            },
        ],
    },
    {
        "space": "Pasillos y escaleras",
        "items": [
            {
                "question": "Pasillos limpios, secos y sin obstrucciones",
                "weight": 2,
                "description": "Revisa si el tránsito está despejado, si el piso está seco y si no hay suciedad, objetos almacenados o riesgos de tropiezo.",
            },
            {
                "question": "Pintura y terminaciones de muros y cielos",
                "weight": 2,
                "description": "Observa desgaste visual, suciedad permanente, desprendimientos, grietas, manchas o intervenciones pendientes.",
            },
            {
                "question": "Iluminación y señalización de circulación",
                "weight": 3,
                "description": "Valida que haya buena iluminación y que la señalización de circulación, emergencia o piso esté visible y correcta.",
            },
            {
                "question": "Barandas, pasamanos y puertas cortafuego",
                "weight": 3,
                "description": "Comprueba estabilidad, limpieza, funcionamiento y ausencia de daños en elementos de seguridad y evacuación.",
            },
        ],
    },
    {
        "space": "Ascensores",
        "items": [
            {
                "question": "Limpieza interior de cabina",
                "weight": 2,
                "description": "Revisa piso, espejo, muros y botones del ascensor. Deben estar limpios y sin residuos visibles.",
            },
            {
                "question": "Terminaciones visibles de cabina",
                "weight": 2,
                "description": "Busca golpes, rayas profundas, paneles sueltos, cielos dañados o desgaste importante en las terminaciones.",
            },
            {
                "question": "Botones, indicadores y alarma",
                "weight": 3,
                "description": "Confirma que los botones respondan, los indicadores funcionen y los elementos de emergencia estén operativos o visibles.",
            },
            {
                "question": "Puertas y funcionamiento general",
                "weight": 5,
                "description": "Evalúa apertura, cierre, nivelación, ruidos extraños, tiempos de espera y cualquier señal de falla en la operación general.",
            },
        ],
    },
    {
        "space": "Áreas verdes y exteriores",
        "items": [
            {
                "question": "Limpieza, poda y orden general",
                "weight": 2,
                "description": "Observa jardines, maceteros y espacios exteriores. Deben verse ordenados, mantenidos y sin residuos acumulados.",
            },
            {
                "question": "Mobiliario exterior y terminaciones",
                "weight": 2,
                "description": "Revisa bancas, cierres, jardineras o elementos exteriores para detectar daños, óxido o desgaste excesivo.",
            },
            {
                "question": "Iluminación exterior cercana",
                "weight": 2,
                "description": "Valida iluminación funcional en accesos, jardines, patios o senderos cercanos.",
            },
            {
                "question": "Ausencia de residuos o daños visibles",
                "weight": 2,
                "description": "Busca basura, escombros, roturas, hundimientos, filtraciones o cualquier deterioro visible en el área exterior.",
            },
        ],
    },
    {
        "space": "Quinchos / terraza / eventos",
        "items": [
            {
                "question": "Limpieza del espacio y residuos",
                "weight": 2,
                "description": "Revisa si hay limpieza posterior al uso, ausencia de grasa, residuos, cenizas o basura acumulada.",
            },
            {
                "question": "Pintura, muros y terminaciones",
                "weight": 2,
                "description": "Busca desgaste, manchas, humedad, desprendimientos o reparaciones pendientes en el espacio social.",
            },
            {
                "question": "Parrillas, mesones o lavaplatos",
                "weight": 3,
                "description": "Valida limpieza, operatividad y estado físico de las superficies o artefactos de uso común.",
            },
            {
                "question": "Iluminación y enchufes visibles",
                "weight": 3,
                "description": "Comprueba luces, enchufes y puntos eléctricos visibles, asegurando que no existan tapas rotas o riesgos evidentes.",
            },
        ],
    },
    {
        "space": "Estacionamientos",
        "items": [
            {
                "question": "Limpieza general y ausencia de derrames",
                "weight": 2,
                "description": "Revisa polvo excesivo, basura, líquidos, aceites u otros derrames que afecten seguridad o imagen.",
            },
            {
                "question": "Pintura y demarcación",
                "weight": 2,
                "description": "Observa si la numeración, líneas, flechas o advertencias se mantienen visibles y en buen estado.",
            },
            {
                "question": "Iluminación del estacionamiento",
                "weight": 3,
                "description": "Valida visibilidad suficiente, luminarias operativas y ausencia de sectores oscuros problemáticos.",
            },
            {
                "question": "Portones / barreras / acceso vehicular",
                "weight": 3,
                "description": "Comprueba funcionamiento de portones, barreras, sensores, controles y seguridad del acceso vehicular.",
            },
        ],
    },
    {
        "space": "Piscina",
        "items": [
            {
                "question": "Limpieza del agua y superficie perimetral",
                "weight": 2,
                "description": "Revisa claridad del agua, presencia de hojas, suciedad, hongos o residuos en la piscina y su borde inmediato.",
            },
            {
                "question": "Borde, pavimento y terminaciones cercanas",
                "weight": 2,
                "description": "Busca baldosas sueltas, fisuras, desniveles, superficies resbaladizas o terminaciones deterioradas alrededor de la piscina.",
            },
            {
                "question": "Cierre, acceso y señalética de seguridad",
                "weight": 3,
                "description": "Confirma que existan barreras, puertas, cierres o señalética visible para normas de uso y seguridad.",
            },
            {
                "question": "Mobiliario, duchas o equipamiento visible",
                "weight": 3,
                "description": "Evalúa reposeras, duchas, skimmers, rejillas u otros elementos visibles asociados al área de piscina.",
            },
        ],
    },
    {
        "space": "Zona de basura y residuos",
        "items": [
            {
                "question": "Limpieza y ausencia de derrames",
                "weight": 2,
                "description": "Revisa si hay líquidos, residuos fuera de contenedores o acumulación que genere suciedad persistente.",
            },
            {
                "question": "Pintura, pisos y terminaciones",
                "weight": 2,
                "description": "Observa muros, piso, puertas y revestimientos; busca humedad, grietas, óxido o daño por uso intensivo.",
            },
            {
                "question": "Contenedores y cierre del espacio",
                "weight": 2,
                "description": "Valida capacidad, estado y funcionamiento de contenedores, tapas, puertas o cerramientos del recinto.",
            },
            {
                "question": "Ventilación, olores y orden general",
                "weight": 2,
                "description": "Evalúa si hay ventilación suficiente, olores anormales o desorden que amerite gestión.",
            },
        ],
    },
    {
        "space": "Sala técnica / equipos visibles",
        "items": [
            {
                "question": "Orden y limpieza del espacio técnico",
                "weight": 2,
                "description": "Verifica que el espacio no esté saturado, sucio o con elementos impropios que dificulten operación o seguridad.",
            },
            {
                "question": "Pintura / pisos / terminaciones",
                "weight": 2,
                "description": "Busca deterioro visible, humedad, óxido o falta de mantención en superficies y terminaciones.",
            },
            {
                "question": "Sin filtraciones, alertas o ruidos anormales",
                "weight": 4,
                "description": "Pon atención a fugas, goteos, alarmas, vibraciones o sonidos anormales en equipos o instalaciones visibles.",
            },
            {
                "question": "Señalización y acceso restringido",
                "weight": 4,
                "description": "Confirma existencia de advertencias, identificación del área y control de acceso para evitar ingreso no autorizado.",
            },
        ],
    },
]

assert sum(sum(item["weight"] for item in space["items"]) for space in CHECKLIST) == 100


# -----------------------------
# Helpers de configuración
# -----------------------------

def default_storage_root() -> Path:
    return APP_DIR / "mq_auditorias_storage"


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "storage_root": str(default_storage_root()),
        "storage_hint": "Si quieres nube simple, apunta esta carpeta a una ruta sincronizada con Google Drive u OneDrive.",
    }


def save_config(config: dict[str, Any]) -> None:
    APP_DATA_DIR.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def get_storage_paths() -> dict[str, Path]:
    root = Path(st.session_state.app_config["storage_root"]).expanduser()
    audits_dir = root / "01_auditorias"
    media_dir = root / "02_evidencias"
    reports_dir = root / "03_reportes"
    tracking_dir = root / "04_seguimiento"
    exports_dir = root / "05_exports"
    for folder in [root, audits_dir, media_dir, reports_dir, tracking_dir, exports_dir]:
        folder.mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "audits": audits_dir,
        "media": media_dir,
        "reports": reports_dir,
        "tracking": tracking_dir,
        "exports": exports_dir,
    }


# -----------------------------
# Helpers generales
# -----------------------------

def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def now_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def safe_read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=columns or [])


def append_dataframe(path: Path, df_new: pd.DataFrame) -> None:
    if path.exists():
        df_old = pd.read_csv(path)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new.copy()
    df_all.to_csv(path, index=False)


def html_escape(text: Any) -> str:
    text = "" if text is None else str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def score_label(score: float) -> tuple[str, str]:
    if score >= 90:
        return "Estándar alto", "summary-good"
    if score >= 80:
        return "Buen estado general", "summary-good"
    if score >= 70:
        return "Aceptable con mejoras", "summary-alert"
    if score >= 60:
        return "Requiere plan de acción", "summary-alert"
    return "Brechas relevantes", "summary-bad"


def priority_from_status(status: str) -> str:
    return "Alta" if status == "Mal estado" else "Media"


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


def parse_optional_date(raw_value: Any) -> str:
    if raw_value in [None, "", "NaT"]:
        return ""
    if isinstance(raw_value, pd.Timestamp):
        return raw_value.date().isoformat()
    if isinstance(raw_value, datetime):
        return raw_value.date().isoformat()
    if isinstance(raw_value, date):
        return raw_value.isoformat()
    return str(raw_value)


# -----------------------------
# Estado de la app
# -----------------------------

def init_state() -> None:
    if "app_config" not in st.session_state:
        st.session_state.app_config = load_config()
    if "audit_meta" not in st.session_state:
        st.session_state.audit_meta = {
            "building": BUILDING_OPTIONS[0],
            "auditor": "",
            "audit_type": "Semanal",
            "sector": "General",
            "general_notes": "",
        }
    if "responses" not in st.session_state:
        st.session_state.responses = {}

    for space in CHECKLIST:
        for item in space["items"]:
            key = f"{space['space']}|{item['question']}"
            if key not in st.session_state.responses:
                st.session_state.responses[key] = {
                    "status": "Pendiente",
                    "observation": "",
                    "action": "Sin acción",
                    "media_saved": [],
                }

    if "saved_message" not in st.session_state:
        st.session_state.saved_message = ""
    if "last_save_result" not in st.session_state:
        st.session_state.last_save_result = {}


# -----------------------------
# Cálculo de scores
# -----------------------------

def calculate_score() -> tuple[float, float, list[dict[str, Any]], int, int]:
    obtained = 0.0
    applicable = 0.0
    answered = 0
    total_questions = 0
    issues: list[dict[str, Any]] = []

    for space in CHECKLIST:
        for item in space["items"]:
            question = item["question"]
            weight = item["weight"]
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
                        "Prioridad": priority_from_status(status),
                        "Evidencias": len(entry.get("media_saved", [])),
                    }
                )

    score = round((obtained / applicable) * 100, 1) if applicable > 0 else 0.0
    progress = round((answered / total_questions) * 100, 1) if total_questions else 0.0
    return score, progress, issues, answered, total_questions


def calculate_space_scores() -> pd.DataFrame:
    rows = []
    for space in CHECKLIST:
        obtained = 0.0
        applicable = 0.0
        total_items = 0
        answered_items = 0
        active_issues = 0
        for item in space["items"]:
            total_items += 1
            key = f"{space['space']}|{item['question']}"
            entry = st.session_state.responses[key]
            status = entry["status"]
            factor = STATUS_FACTOR.get(status)
            if status != "Pendiente":
                answered_items += 1
            if status == "No aplica":
                continue
            if factor is not None:
                applicable += item["weight"]
                obtained += item["weight"] * factor
            if status in ["Necesita mantenimiento", "Mal estado"]:
                active_issues += 1

        score = round((obtained / applicable) * 100, 1) if applicable else 0.0
        rows.append(
            {
                "space": space["space"],
                "space_score": score,
                "answered_items": answered_items,
                "total_items": total_items,
                "active_issues": active_issues,
            }
        )
    return pd.DataFrame(rows)


# -----------------------------
# Evidencias
# -----------------------------

def build_media_payloads(key: str) -> list[dict[str, Any]]:
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


def persist_media_files(audit_id: str, key: str) -> list[dict[str, Any]]:
    payloads = build_media_payloads(key)
    saved_files = []

    if not payloads:
        return saved_files

    paths = get_storage_paths()
    audit_media_dir = paths["media"] / audit_id / slugify(key)
    audit_media_dir.mkdir(parents=True, exist_ok=True)

    seen_signatures = set()
    for idx, payload in enumerate(payloads, start=1):
        raw_bytes = payload["bytes"]
        signature = (payload["name"], len(raw_bytes), payload["mime"])
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        suffix = Path(payload["name"] or "archivo").suffix or guess_extension(payload["mime"])
        file_name = f"{slugify(key)}_{idx}{suffix}"
        file_path = audit_media_dir / file_name
        file_path.write_bytes(raw_bytes)

        saved_files.append(
            {
                "name": file_name,
                "original_name": payload["name"],
                "source": payload["source"],
                "mime": payload["mime"],
                "path": str(file_path.resolve()),
            }
        )
    return saved_files


def render_evidence_preview(key: str) -> None:
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


# -----------------------------
# Reporte HTML
# -----------------------------

def build_executive_summary(score: float, issues_df: pd.DataFrame, spaces_df: pd.DataFrame) -> str:
    if issues_df.empty:
        return (
            "La auditoría no detectó hallazgos activos. El edificio presenta un nivel general consistente con el estándar esperado "
            "para este recorrido, aunque siempre conviene mantener monitoreo periódico de los espacios comunes."
        )

    worst_spaces = spaces_df.sort_values(["space_score", "active_issues"], ascending=[True, False]).head(3)
    worst_labels = ", ".join(worst_spaces["space"].tolist()) if not worst_spaces.empty else "espacios sin definir"
    critical = int((issues_df["Estado"] == "Mal estado").sum())
    maintenance = int((issues_df["Estado"] == "Necesita mantenimiento").sum())
    return (
        f"La auditoría cerró con un score general de {score}/100 y detectó {len(issues_df)} hallazgos activos. "
        f"De ellos, {critical} corresponden a condiciones de mal estado y {maintenance} requieren mantenimiento programado. "
        f"Los espacios con mayor atención sugerida en esta revisión fueron: {worst_labels}."
    )


def generate_report_html(
    audit_id: str,
    meta: dict[str, Any],
    score: float,
    progress: float,
    issues_df: pd.DataFrame,
    spaces_df: pd.DataFrame,
    items_df: pd.DataFrame,
    cases_created: int,
    cases_updated: int,
) -> Path:
    paths = get_storage_paths()
    label, _ = score_label(score)
    report_path = paths["reports"] / f"reporte_{audit_id}.html"

    issues_rows = []
    for _, row in issues_df.iterrows():
        issues_rows.append(
            "<tr>"
            f"<td>{html_escape(row.get('Espacio'))}</td>"
            f"<td>{html_escape(row.get('Pregunta'))}</td>"
            f"<td>{html_escape(row.get('Estado'))}</td>"
            f"<td>{html_escape(row.get('Acción'))}</td>"
            f"<td>{html_escape(row.get('Prioridad'))}</td>"
            f"<td>{html_escape(row.get('Observación'))}</td>"
            "</tr>"
        )
    issues_table_html = "\n".join(issues_rows) if issues_rows else "<tr><td colspan='6'>Sin hallazgos activos.</td></tr>"

    spaces_rows = []
    for _, row in spaces_df.iterrows():
        spaces_rows.append(
            "<tr>"
            f"<td>{html_escape(row['space'])}</td>"
            f"<td>{html_escape(row['space_score'])}</td>"
            f"<td>{html_escape(row['answered_items'])}/{html_escape(row['total_items'])}</td>"
            f"<td>{html_escape(row['active_issues'])}</td>"
            "</tr>"
        )
    spaces_table_html = "\n".join(spaces_rows)

    evidence_rows = []
    items_with_evidence = items_df[items_df["evidence_count"] > 0].copy()
    for _, row in items_with_evidence.iterrows():
        links = []
        try:
            file_paths = json.loads(row.get("evidence_paths", "[]"))
        except json.JSONDecodeError:
            file_paths = []
        for path_str in file_paths:
            p = Path(path_str)
            href = p.resolve().as_uri() if p.exists() else html_escape(path_str)
            links.append(f"<a href='{href}' target='_blank'>{html_escape(p.name)}</a>")
        evidence_rows.append(
            "<tr>"
            f"<td>{html_escape(row['space'])}</td>"
            f"<td>{html_escape(row['question'])}</td>"
            f"<td>{'<br>'.join(links) if links else '-'}</td>"
            "</tr>"
        )
    evidence_table_html = "\n".join(evidence_rows) if evidence_rows else "<tr><td colspan='3'>Sin evidencias adjuntas.</td></tr>"

    executive_summary = build_executive_summary(score, issues_df, spaces_df)
    generated_at = datetime.now().strftime("%d-%m-%Y %H:%M")

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>Reporte {html_escape(audit_id)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #17324d; }}
.card {{ border: 1px solid #dce7f4; border-radius: 16px; padding: 16px; margin-bottom: 16px; }}
.kpi {{ display: inline-block; min-width: 160px; margin-right: 12px; margin-bottom: 10px; background: #f5f9ff; border: 1px solid #d7e6fb; border-radius: 14px; padding: 12px; }}
.kpi-title {{ color: #54708d; font-size: 12px; text-transform: uppercase; }}
.kpi-value {{ font-size: 24px; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
th, td {{ border: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; font-size: 13px; }}
th {{ background: #f8fbff; }}
h1, h2, h3 {{ margin-bottom: 8px; }}
.small {{ color: #64748b; font-size: 12px; }}
</style>
</head>
<body>
<h1>Informe de auditoría de edificio</h1>
<div class="small">Generado el {generated_at}</div>

<div class="card">
    <h2>Identificación</h2>
    <p><strong>Auditoría:</strong> {html_escape(audit_id)}</p>
    <p><strong>Edificio:</strong> {html_escape(meta['building'])}</p>
    <p><strong>Sector:</strong> {html_escape(meta['sector'])}</p>
    <p><strong>Auditor:</strong> {html_escape(meta['auditor'])}</p>
    <p><strong>Tipo:</strong> {html_escape(meta['audit_type'])}</p>
    <p><strong>Fecha:</strong> {html_escape(meta['timestamp_human'])}</p>
</div>

<div class="card">
    <h2>Resumen ejecutivo</h2>
    <div class="kpi"><div class="kpi-title">Score general</div><div class="kpi-value">{score}/100</div></div>
    <div class="kpi"><div class="kpi-title">Estado general</div><div class="kpi-value">{html_escape(label)}</div></div>
    <div class="kpi"><div class="kpi-title">Progreso</div><div class="kpi-value">{progress}%</div></div>
    <div class="kpi"><div class="kpi-title">Hallazgos</div><div class="kpi-value">{len(issues_df)}</div></div>
    <div class="kpi"><div class="kpi-title">Casos creados</div><div class="kpi-value">{cases_created}</div></div>
    <div class="kpi"><div class="kpi-title">Casos actualizados</div><div class="kpi-value">{cases_updated}</div></div>
    <p>{html_escape(executive_summary)}</p>
    <p><strong>Observación general del auditor:</strong> {html_escape(meta['general_notes']) or 'Sin observación general.'}</p>
</div>

<div class="card">
    <h2>Puntaje por espacio</h2>
    <table>
        <thead>
            <tr><th>Espacio</th><th>Score</th><th>Respondido</th><th>Hallazgos</th></tr>
        </thead>
        <tbody>
            {spaces_table_html}
        </tbody>
    </table>
</div>

<div class="card">
    <h2>Hallazgos y gestiones sugeridas</h2>
    <table>
        <thead>
            <tr><th>Espacio</th><th>Pregunta</th><th>Estado</th><th>Acción</th><th>Prioridad</th><th>Observación</th></tr>
        </thead>
        <tbody>
            {issues_table_html}
        </tbody>
    </table>
</div>

<div class="card">
    <h2>Evidencias asociadas</h2>
    <table>
        <thead>
            <tr><th>Espacio</th><th>Pregunta</th><th>Archivos</th></tr>
        </thead>
        <tbody>
            {evidence_table_html}
        </tbody>
    </table>
</div>
</body>
</html>
"""
    report_path.write_text(html, encoding="utf-8")
    return report_path


def generate_report_json(
    audit_id: str,
    meta: dict[str, Any],
    score: float,
    progress: float,
    issues_df: pd.DataFrame,
    spaces_df: pd.DataFrame,
    items_df: pd.DataFrame,
    cases_created: int,
    cases_updated: int,
) -> Path:
    paths = get_storage_paths()
    json_path = paths["audits"] / f"auditoria_{audit_id}.json"

    def parse_paths(raw: Any) -> list[str]:
        if raw in [None, "", []]:
            return []
        if isinstance(raw, list):
            return [str(x) for x in raw]
        try:
            return json.loads(raw)
        except Exception:
            return [str(raw)]

    payload = {
        "audit_id": audit_id,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "meta": meta,
        "score": score,
        "progress": progress,
        "summary_label": score_label(score)[0],
        "issue_count": int(len(issues_df)),
        "cases_created": int(cases_created),
        "cases_updated": int(cases_updated),
        "space_scores": spaces_df.to_dict(orient="records"),
        "issues": issues_df.to_dict(orient="records"),
        "items": [
            {
                **row,
                "evidence_paths": parse_paths(row.get("evidence_paths", [])),
            }
            for row in items_df.to_dict(orient="records")
        ],
        "general_notes": meta.get("general_notes", ""),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path


# -----------------------------
# Casos de seguimiento
# -----------------------------

def upsert_followup_cases(audit_id: str, items_df: pd.DataFrame) -> tuple[int, int]:
    paths = get_storage_paths()
    cases_path = paths["tracking"] / "cases_followup.csv"
    events_path = paths["tracking"] / "case_events.csv"

    case_columns = [
        "case_id", "building", "sector", "space", "question", "description", "priority", "case_status",
        "responsible", "created_at", "due_date", "closed_at", "last_review_at", "latest_audit_id",
        "latest_audit_timestamp", "latest_audit_status", "latest_action", "latest_observation",
        "timeline_note", "evidence_count", "last_report_path",
    ]
    event_columns = ["event_id", "case_id", "event_at", "event_type", "note", "audit_id"]

    cases_df = safe_read_csv(cases_path, case_columns)
    events_df = safe_read_csv(events_path, event_columns)

    issue_items = items_df[items_df["status"].isin(["Necesita mantenimiento", "Mal estado"])].copy()
    if issue_items.empty:
        if not cases_path.exists():
            cases_df.to_csv(cases_path, index=False)
        if not events_path.exists():
            events_df.to_csv(events_path, index=False)
        return 0, 0

    created = 0
    updated = 0
    event_rows = []

    for _, row in issue_items.iterrows():
        mask = (
            (cases_df.get("building", pd.Series(dtype=str)) == row["building"]) &
            (cases_df.get("sector", pd.Series(dtype=str)) == row["sector"]) &
            (cases_df.get("space", pd.Series(dtype=str)) == row["space"]) &
            (cases_df.get("question", pd.Series(dtype=str)) == row["question"]) &
            (cases_df.get("case_status", pd.Series(dtype=str)) != "Cerrado")
        )

        if not cases_df.empty and mask.any():
            idx = cases_df[mask].index[0]
            cases_df.loc[idx, "priority"] = row["priority"]
            cases_df.loc[idx, "last_review_at"] = row["timestamp_human"]
            cases_df.loc[idx, "latest_audit_id"] = audit_id
            cases_df.loc[idx, "latest_audit_timestamp"] = row["timestamp_human"]
            cases_df.loc[idx, "latest_audit_status"] = row["status"]
            cases_df.loc[idx, "latest_action"] = row["action"]
            cases_df.loc[idx, "latest_observation"] = row["observation"]
            cases_df.loc[idx, "timeline_note"] = f"Actualizado por auditoría {audit_id}."
            cases_df.loc[idx, "evidence_count"] = row["evidence_count"]
            updated += 1
            event_rows.append(
                {
                    "event_id": now_id("EVT"),
                    "case_id": cases_df.loc[idx, "case_id"],
                    "event_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "event_type": "Actualización por auditoría",
                    "note": f"Se actualiza hallazgo: {row['status']} · {row['action']}",
                    "audit_id": audit_id,
                }
            )
        else:
            case_id = now_id("CASO")
            new_row = {
                "case_id": case_id,
                "building": row["building"],
                "sector": row["sector"],
                "space": row["space"],
                "question": row["question"],
                "description": row["description"],
                "priority": row["priority"],
                "case_status": "Abierto",
                "responsible": "",
                "created_at": row["timestamp_human"],
                "due_date": "",
                "closed_at": "",
                "last_review_at": row["timestamp_human"],
                "latest_audit_id": audit_id,
                "latest_audit_timestamp": row["timestamp_human"],
                "latest_audit_status": row["status"],
                "latest_action": row["action"],
                "latest_observation": row["observation"],
                "timeline_note": "Caso creado desde auditoría.",
                "evidence_count": row["evidence_count"],
                "last_report_path": row["report_path"],
            }
            cases_df = pd.concat([cases_df, pd.DataFrame([new_row])], ignore_index=True)
            created += 1
            event_rows.append(
                {
                    "event_id": now_id("EVT"),
                    "case_id": case_id,
                    "event_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "event_type": "Creación por auditoría",
                    "note": f"Se crea caso con prioridad {row['priority']} y acción {row['action']}.",
                    "audit_id": audit_id,
                }
            )

    cases_df.to_csv(cases_path, index=False)
    if event_rows:
        append_dataframe(events_path, pd.DataFrame(event_rows))
    elif not events_path.exists():
        pd.DataFrame(columns=event_columns).to_csv(events_path, index=False)
    return created, updated


def update_case_record(case_id: str, updates: dict[str, Any], note: str) -> None:
    paths = get_storage_paths()
    cases_path = paths["tracking"] / "cases_followup.csv"
    events_path = paths["tracking"] / "case_events.csv"
    cases_df = safe_read_csv(cases_path)
    if cases_df.empty or case_id not in cases_df["case_id"].astype(str).tolist():
        return

    idx = cases_df[cases_df["case_id"].astype(str) == str(case_id)].index[0]
    for field, value in updates.items():
        cases_df.loc[idx, field] = value
    if updates.get("case_status") == "Cerrado" and not cases_df.loc[idx, "closed_at"]:
        cases_df.loc[idx, "closed_at"] = datetime.now().strftime("%Y-%m-%d")
    if updates.get("case_status") != "Cerrado":
        cases_df.loc[idx, "closed_at"] = ""
    cases_df.loc[idx, "last_review_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cases_df.to_csv(cases_path, index=False)

    event_row = pd.DataFrame(
        [
            {
                "event_id": now_id("EVT"),
                "case_id": case_id,
                "event_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": "Seguimiento manual",
                "note": note,
                "audit_id": "",
            }
        ]
    )
    append_dataframe(events_path, event_row)


# -----------------------------
# Guardado de auditoría
# -----------------------------

def save_audit() -> None:
    audit_id = now_id("AUD")
    timestamp_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    score, progress, issues, answered, total_questions = calculate_score()
    space_scores_df = calculate_space_scores()
    paths = get_storage_paths()
    label, _ = score_label(score)

    item_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []

    for space in CHECKLIST:
        for item in space["items"]:
            question = item["question"]
            key = f"{space['space']}|{question}"
            entry = st.session_state.responses[key]
            saved_media = persist_media_files(audit_id, key)
            entry["media_saved"] = saved_media
            st.session_state.responses[key] = entry

            evidence_paths = [media["path"] for media in saved_media]
            row = {
                "audit_id": audit_id,
                "timestamp_human": timestamp_human,
                "building": st.session_state.audit_meta["building"],
                "auditor": st.session_state.audit_meta["auditor"],
                "audit_type": st.session_state.audit_meta["audit_type"],
                "sector": st.session_state.audit_meta["sector"],
                "space": space["space"],
                "question": question,
                "description": item["description"],
                "weight": item["weight"],
                "status": entry["status"],
                "action": entry["action"],
                "observation": entry["observation"],
                "priority": priority_from_status(entry["status"]) if entry["status"] in ["Necesita mantenimiento", "Mal estado"] else "",
                "evidence_count": len(saved_media),
                "evidence_paths": json.dumps(evidence_paths, ensure_ascii=False),
                "score_total": score,
                "progress": progress,
                "report_path": "",
            }
            item_rows.append(row)

            for media in saved_media:
                evidence_rows.append(
                    {
                        "audit_id": audit_id,
                        "timestamp_human": timestamp_human,
                        "building": st.session_state.audit_meta["building"],
                        "sector": st.session_state.audit_meta["sector"],
                        "space": space["space"],
                        "question": question,
                        "mime": media["mime"],
                        "file_name": media["name"],
                        "original_name": media["original_name"],
                        "path": media["path"],
                        "source": media["source"],
                    }
                )

    items_df = pd.DataFrame(item_rows)

    report_path = generate_report_html(
        audit_id=audit_id,
        meta={
            **st.session_state.audit_meta,
            "timestamp_human": timestamp_human,
        },
        score=score,
        progress=progress,
        issues_df=pd.DataFrame(issues),
        spaces_df=space_scores_df,
        items_df=items_df,
        cases_created=0,
        cases_updated=0,
    )
    items_df["report_path"] = str(report_path.resolve())

    cases_created, cases_updated = upsert_followup_cases(audit_id, items_df)
    report_path = generate_report_html(
        audit_id=audit_id,
        meta={
            **st.session_state.audit_meta,
            "timestamp_human": timestamp_human,
        },
        score=score,
        progress=progress,
        issues_df=pd.DataFrame(issues),
        spaces_df=space_scores_df,
        items_df=items_df,
        cases_created=cases_created,
        cases_updated=cases_updated,
    )
    json_report_path = generate_report_json(
        audit_id=audit_id,
        meta={
            **st.session_state.audit_meta,
            "timestamp_human": timestamp_human,
        },
        score=score,
        progress=progress,
        issues_df=pd.DataFrame(issues),
        spaces_df=space_scores_df,
        items_df=items_df,
        cases_created=cases_created,
        cases_updated=cases_updated,
    )
    items_df["report_path"] = str(report_path.resolve())

    audits_summary_df = pd.DataFrame(
        [
            {
                "audit_id": audit_id,
                "timestamp_human": timestamp_human,
                "building": st.session_state.audit_meta["building"],
                "auditor": st.session_state.audit_meta["auditor"],
                "audit_type": st.session_state.audit_meta["audit_type"],
                "sector": st.session_state.audit_meta["sector"],
                "general_notes": st.session_state.audit_meta["general_notes"],
                "score_total": score,
                "score_label": label,
                "progress": progress,
                "answered": answered,
                "total_questions": total_questions,
                "issue_count": len(issues),
                "cases_created": cases_created,
                "cases_updated": cases_updated,
                "report_path": str(report_path.resolve()),
                "json_path": str(json_report_path.resolve()),
                "evidence_dir": str((paths["media"] / audit_id).resolve()),
            }
        ]
    )

    space_scores_df = space_scores_df.copy()
    space_scores_df.insert(0, "audit_id", audit_id)
    space_scores_df.insert(1, "timestamp_human", timestamp_human)
    evidence_df = pd.DataFrame(evidence_rows)

    append_dataframe(paths["audits"] / "audits_summary.csv", audits_summary_df)
    append_dataframe(paths["audits"] / "audit_items.csv", items_df)
    append_dataframe(paths["audits"] / "audit_space_scores.csv", space_scores_df)
    if not evidence_df.empty:
        append_dataframe(paths["audits"] / "audit_evidence.csv", evidence_df)

    export_path = paths["exports"] / f"auditoria_{audit_id}_detalle.csv"
    items_df.to_csv(export_path, index=False)

    st.session_state.saved_message = f"Auditoría guardada: {audit_id}"
    st.session_state.last_save_result = {
        "audit_id": audit_id,
        "report_path": str(report_path.resolve()),
        "json_path": str(json_report_path.resolve()),
        "export_path": str(export_path.resolve()),
        "cases_created": cases_created,
        "cases_updated": cases_updated,
        "evidence_dir": str((paths["media"] / audit_id).resolve()),
    }


# -----------------------------
# UI
# -----------------------------

def inject_css() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 700px;
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
            .small-label {
                font-size: 0.9rem;
                font-weight: 600;
                color: #334155;
                margin-bottom: 0.2rem;
            }
            div[data-baseweb="select"] > div, textarea, input {
                border-radius: 12px !important;
            }
            .hint-box {
                background: #f8fbff;
                border: 1px dashed #cfe1f8;
                border-radius: 14px;
                padding: 10px 12px;
                margin-top: 8px;
                margin-bottom: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def header() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                <div>
                    <div style="font-size:1.3rem; font-weight:800; color:#16324d;">Auditoría móvil del edificio · v2</div>
                    <div class="muted">Checklist guiado, evidencias, reporte HTML + JSON y seguimiento de casos.</div>
                </div>
                <div class="badge">Drive-ready</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_storage_config() -> None:
    with st.expander("Configuración de almacenamiento y nube"):
        storage_root = st.text_input(
            "Carpeta raíz de almacenamiento",
            value=st.session_state.app_config.get("storage_root", str(default_storage_root())),
            help="Puedes apuntar esto a una carpeta sincronizada con Google Drive para Desktop o OneDrive.",
        )
        st.caption(
            "Ejemplo: una carpeta dentro de Google Drive en tu computador. La app guardará auditorías, evidencias, reportes y seguimiento dentro de esa ruta."
        )
        if st.button("Guardar configuración de carpeta"):
            st.session_state.app_config["storage_root"] = storage_root.strip() or str(default_storage_root())
            save_config(st.session_state.app_config)
            get_storage_paths()
            st.success("Configuración guardada.")
        current = get_storage_paths()
        st.code(str(current["root"]))
        st.markdown(
            "**Estructura creada automáticamente**\n\n"
            "- `01_auditorias/` resumen, detalle y puntajes por espacio  \n"
            "- `02_evidencias/` fotos y videos  \n"
            "- `03_reportes/` informes HTML  \n"
            "- `04_seguimiento/` casos y timeline  \n"
            "- `05_exports/` CSV por auditoría"
        )


def render_meta() -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Inicio de auditoría")
    c1, c2 = st.columns(2)
    with c1:
        building_index = BUILDING_OPTIONS.index(st.session_state.audit_meta.get("building", BUILDING_OPTIONS[0]))
        st.session_state.audit_meta["building"] = st.selectbox("Edificio", BUILDING_OPTIONS, index=building_index)
        st.session_state.audit_meta["audit_type"] = st.selectbox(
            "Tipo de auditoría",
            ["Semanal", "Mensual profunda", "Validación de cierre", "Extraordinaria"],
            index=["Semanal", "Mensual profunda", "Validación de cierre", "Extraordinaria"].index(
                st.session_state.audit_meta.get("audit_type", "Semanal")
            ) if st.session_state.audit_meta.get("audit_type", "Semanal") in ["Semanal", "Mensual profunda", "Validación de cierre", "Extraordinaria"] else 0,
        )
    with c2:
        st.session_state.audit_meta["auditor"] = st.text_input("Auditor", value=st.session_state.audit_meta.get("auditor", ""))
        st.session_state.audit_meta["sector"] = st.text_input("Sector / torre", value=st.session_state.audit_meta.get("sector", "General"))
    st.session_state.audit_meta["general_notes"] = st.text_area(
        "Observación general",
        value=st.session_state.audit_meta.get("general_notes", ""),
        placeholder="Ej. Se detectó mayor desgaste en acceso y piscina, con dos casos que requieren proveedor.",
        height=90,
    )
    st.markdown('</div>', unsafe_allow_html=True)


def render_dashboard() -> None:
    score, _, issues, answered, total_questions = calculate_score()
    label, css = score_label(score)
    spaces_df = calculate_space_scores()
    low_spaces = int((spaces_df["space_score"] < 80).sum()) if not spaces_df.empty else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Score general", f"{score}/100")
    with c2:
        st.metric("Respondidas", f"{answered}/{total_questions}")
    with c3:
        st.metric("Hallazgos", len(issues))
    st.markdown(f"<div class='{css}' style='margin-top:4px; margin-bottom:8px;'>{label}</div>", unsafe_allow_html=True)
    st.caption(f"Espacios bajo 80 puntos: {low_spaces}")



def render_space(space: dict[str, Any]) -> None:
    total_weight = sum(item["weight"] for item in space["items"])
    with st.expander(f"{space['space']} · {total_weight} pts", expanded=False):
        st.markdown(
            f"<div class='space-title'>{space['space']}</div><div class='muted'>Marca el estado de cada punto. Si hay hallazgo, agrega evidencia y observación.</div>",
            unsafe_allow_html=True,
        )
        for item in space["items"]:
            key = f"{space['space']}|{item['question']}"
            entry = st.session_state.responses[key]

            st.markdown('<div class="item-card">', unsafe_allow_html=True)
            st.markdown(f"**{item['question']}**")
            st.caption(f"Puntaje máximo: {item['weight']}")

            entry["status"] = st.selectbox(
                "Estado",
                STATUS_OPTIONS,
                key=f"status_{slugify(key)}",
                index=STATUS_OPTIONS.index(entry["status"]),
                help=item["description"],
            )

            if entry["status"] in ["Necesita mantenimiento", "Mal estado"]:
                entry["action"] = st.selectbox(
                    "Acción requerida",
                    ACTION_OPTIONS,
                    key=f"action_{slugify(key)}",
                    index=ACTION_OPTIONS.index(entry.get("action", "Sin acción")),
                )

                st.markdown("<div class='small-label'>Foto rápida</div>", unsafe_allow_html=True)
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
                    placeholder="Describe brevemente el hallazgo, impacto y contexto.",
                )
            else:
                entry["action"] = "Sin acción"
                entry["observation"] = entry.get("observation", "")
            st.markdown('</div>', unsafe_allow_html=True)
            st.session_state.responses[key] = entry


def reset_responses() -> None:
    for space in CHECKLIST:
        for item in space["items"]:
            key = f"{space['space']}|{item['question']}"
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


def render_summary() -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Cierre de auditoría")
    score, _, issues, _, _ = calculate_score()
    label, _ = score_label(score)
    st.write(
        "Al guardar, la app creará el registro estructurado, almacenará las evidencias, generará un informe HTML, un JSON y abrirá o actualizará casos de seguimiento."
    )

    if issues:
        df = pd.DataFrame(issues)
        st.dataframe(
            df[["Espacio", "Pregunta", "Estado", "Acción", "Prioridad"]],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("No se detectaron hallazgos en esta auditoría.")

    pending = []
    for space in CHECKLIST:
        for item in space["items"]:
            key = f"{space['space']}|{item['question']}"
            if st.session_state.responses[key]["status"] == "Pendiente":
                pending.append(key)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Guardar auditoría", use_container_width=True, type="primary"):
            if pending:
                st.error(f"Aún hay {len(pending)} preguntas pendientes por responder.")
            elif not st.session_state.audit_meta["auditor"].strip():
                st.error("Ingresa el nombre del auditor antes de guardar.")
            else:
                save_audit()
                st.success(st.session_state.saved_message)
                result = st.session_state.last_save_result
                st.info(
                    f"Reporte: {result.get('report_path', '-')} · JSON: {result.get('json_path', '-')} · Casos creados: {result.get('cases_created', 0)} · actualizados: {result.get('cases_updated', 0)}"
                )
    with c2:
        if st.button("Reiniciar respuestas", use_container_width=True):
            reset_responses()
            st.rerun()

    st.caption(f"Estado actual del edificio: {label}")
    st.markdown('</div>', unsafe_allow_html=True)


def render_history_tab() -> None:
    st.markdown("### Historial, reportes y evidencias")
    paths = get_storage_paths()
    audits_path = paths["audits"] / "audits_summary.csv"
    items_path = paths["audits"] / "audit_items.csv"
    evidence_path = paths["audits"] / "audit_evidence.csv"

    audits_df = safe_read_csv(audits_path)
    if audits_df.empty:
        st.info("Todavía no hay auditorías guardadas.")
        return

    audits_df = audits_df.sort_values("timestamp_human", ascending=False)
    labels = [f"{row.audit_id} · {row.timestamp_human} · {row.building}" for row in audits_df.itertuples()]
    selected_label = st.selectbox("Selecciona una auditoría", labels)
    selected_idx = labels.index(selected_label)
    selected = audits_df.iloc[selected_idx]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Score", f"{selected['score_total']}/100")
    with c2:
        st.metric("Hallazgos", int(selected["issue_count"]))
    with c3:
        st.metric("Casos creados", int(selected.get("cases_created", 0)))

    st.markdown('<div class="hint-box">', unsafe_allow_html=True)
    st.write(f"**Edificio:** {selected['building']}")
    st.write(f"**Auditor:** {selected['auditor']}")
    st.write(f"**Sector:** {selected['sector']}")
    st.write(f"**Tipo:** {selected['audit_type']}")
    st.write(f"**Reporte HTML:** `{selected['report_path']}`")
    if 'json_path' in selected.index and pd.notna(selected.get('json_path', '')):
        st.write(f"**JSON:** `{selected['json_path']}`")
    st.write(f"**Carpeta evidencias:** `{selected['evidence_dir']}`")
    st.markdown('</div>', unsafe_allow_html=True)

    d1, d2 = st.columns(2)
    report_path = Path(selected["report_path"])
    if report_path.exists():
        with d1:
            st.download_button(
                "Descargar reporte HTML",
                data=report_path.read_text(encoding="utf-8"),
                file_name=report_path.name,
                mime="text/html",
            )
    json_path_value = selected.get("json_path", "") if hasattr(selected, 'get') else ""
    if pd.notna(json_path_value) and str(json_path_value).strip():
        json_path = Path(str(json_path_value))
        if json_path.exists():
            with d2:
                st.download_button(
                    "Descargar JSON",
                    data=json_path.read_text(encoding="utf-8"),
                    file_name=json_path.name,
                    mime="application/json",
                )

    items_df = safe_read_csv(items_path)
    items_filtered = items_df[items_df["audit_id"] == selected["audit_id"]].copy()
    if not items_filtered.empty:
        st.markdown("#### Hallazgos de la auditoría")
        issues_df = items_filtered[items_filtered["status"].isin(["Necesita mantenimiento", "Mal estado"])].copy()
        if not issues_df.empty:
            st.dataframe(
                issues_df[["space", "question", "status", "action", "priority", "observation"]],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.success("Esta auditoría no dejó hallazgos activos.")

    evidence_df = safe_read_csv(evidence_path)
    evidence_filtered = evidence_df[evidence_df["audit_id"] == selected["audit_id"]].copy()
    st.markdown("#### Evidencias")
    if evidence_filtered.empty:
        st.info("No hay evidencias guardadas en esta auditoría.")
        return

    for _, row in evidence_filtered.iterrows():
        st.markdown(f"**{row['space']} · {row['question']}**")
        p = Path(row["path"])
        if p.exists():
            mime = str(row.get("mime", ""))
            if mime.startswith("image/"):
                st.image(str(p), caption=p.name, use_container_width=True)
            elif mime.startswith("video/"):
                st.video(str(p))
            else:
                st.write(p.name)
        st.caption(str(p))


def render_cases_tab() -> None:
    st.markdown("### Seguimiento de casos")
    paths = get_storage_paths()
    cases_path = paths["tracking"] / "cases_followup.csv"
    events_path = paths["tracking"] / "case_events.csv"
    cases_df = safe_read_csv(cases_path)
    events_df = safe_read_csv(events_path)

    if cases_df.empty:
        st.info("Aún no hay casos de seguimiento. Se crean automáticamente cuando un ítem queda en mantenimiento o mal estado.")
        return

    status_filter = st.selectbox("Filtrar casos", ["Todos", "Abiertos", "No cerrados", "Cerrados"], index=2)
    filtered = cases_df.copy()
    if status_filter == "Abiertos":
        filtered = filtered[filtered["case_status"] == "Abierto"]
    elif status_filter == "No cerrados":
        filtered = filtered[filtered["case_status"] != "Cerrado"]
    elif status_filter == "Cerrados":
        filtered = filtered[filtered["case_status"] == "Cerrado"]

    st.dataframe(
        filtered[["case_id", "building", "space", "question", "priority", "case_status", "responsible", "due_date"]],
        hide_index=True,
        use_container_width=True,
    )
    if filtered.empty:
        st.info("No hay casos para el filtro seleccionado.")
        return

    case_labels = [f"{row.case_id} · {row.space} · {row.question}" for row in filtered.itertuples()]
    selected_label = st.selectbox("Selecciona un caso", case_labels)
    selected_case_id = selected_label.split(" · ")[0]
    case_row = filtered[filtered["case_id"] == selected_case_id].iloc[0]

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.write(f"**Caso:** {case_row['case_id']}")
    st.write(f"**Edificio:** {case_row['building']} · **Sector:** {case_row['sector']}")
    st.write(f"**Espacio:** {case_row['space']}")
    st.write(f"**Pregunta:** {case_row['question']}")
    st.write(f"**Qué revisar:** {case_row.get('description', '')}")
    st.write(f"**Último estado observado:** {case_row['latest_audit_status']}")
    st.write(f"**Última acción sugerida:** {case_row['latest_action']}")
    st.write(f"**Última observación:** {case_row['latest_observation']}")
    st.markdown('</div>', unsafe_allow_html=True)

    current_status = case_row["case_status"] if case_row["case_status"] in CASE_STATUS_OPTIONS else CASE_STATUS_OPTIONS[0]
    current_priority = case_row["priority"] if case_row["priority"] in PRIORITY_OPTIONS else PRIORITY_OPTIONS[1]
    responsible = st.text_input("Responsable", value=str(case_row.get("responsible", "")), key=f"resp_{selected_case_id}")
    priority = st.selectbox("Prioridad", PRIORITY_OPTIONS, index=PRIORITY_OPTIONS.index(current_priority), key=f"prio_{selected_case_id}")
    case_status = st.selectbox("Estado del caso", CASE_STATUS_OPTIONS, index=CASE_STATUS_OPTIONS.index(current_status), key=f"status_case_{selected_case_id}")
    due_default = None
    due_raw = parse_optional_date(case_row.get("due_date", ""))
    if due_raw:
        try:
            due_default = date.fromisoformat(due_raw)
        except ValueError:
            due_default = None
    due_date_value = st.date_input("Fecha compromiso", value=due_default, key=f"due_{selected_case_id}")
    followup_note = st.text_area(
        "Comentario de seguimiento / cierre",
        value="",
        key=f"note_{selected_case_id}",
        placeholder="Ej. Se coordinó proveedor para el jueves. Pendiente validación del cierre.",
        height=110,
    )
    if st.button("Guardar seguimiento del caso", type="primary"):
        updates = {
            "responsible": responsible,
            "priority": priority,
            "case_status": case_status,
            "due_date": due_date_value.isoformat() if due_date_value else "",
        }
        note = followup_note.strip() or f"Caso actualizado a estado {case_status}."
        update_case_record(selected_case_id, updates, note)
        st.success("Seguimiento guardado.")
        st.rerun()

    if not events_df.empty:
        case_events = events_df[events_df["case_id"] == selected_case_id].sort_values("event_at", ascending=False)
        if not case_events.empty:
            st.markdown("#### Timeline")
            st.dataframe(case_events[["event_at", "event_type", "note", "audit_id"]], hide_index=True, use_container_width=True)


def architecture_view() -> None:
    with st.expander("Cómo aterrizar Google Drive y el flujo completo"):
        st.markdown(
            """
**Forma simple de llevarlo a la nube**

1. Instala Google Drive para Desktop en el computador que ejecuta la app.  
2. Crea una carpeta como `Google Drive/MQ Auditorías`.  
3. En la app, pega esa ruta en **Carpeta raíz de almacenamiento**.  
4. Desde ese momento, las auditorías, evidencias y reportes se guardarán en la carpeta sincronizada.  

**Qué produce esta versión**
- Registro por auditoría.
- Detalle por pregunta.
- Evidencias por hallazgo.
- Informe HTML descargable.
- Casos automáticos de seguimiento.
- Timeline manual para cierre de casos.

**Siguiente evolución recomendada**
- Base de datos para multiusuario.
- Integración directa con Google Drive API.
- Dashboard histórico y semáforo de vencimientos.
            """
        )


def render_audit_tab() -> None:
    render_storage_config()
    render_meta()
    render_dashboard()
    architecture_view()
    st.markdown("### Checklist por espacios")
    for space in CHECKLIST:
        render_space(space)
    render_summary()


def main() -> None:
    inject_css()
    init_state()
    header()
    tab1, tab2, tab3 = st.tabs(["Auditoría", "Historial y evidencias", "Casos y seguimiento"])
    with tab1:
        render_audit_tab()
    with tab2:
        render_history_tab()
    with tab3:
        render_cases_tab()


if __name__ == "__main__":
    main()
