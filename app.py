
import io
import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Auditoría Móvil de Edificio",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_DIR = Path(__file__).parent
APP_DATA_DIR = APP_DIR / "app_data"
APP_DATA_DIR.mkdir(exist_ok=True)
CONFIG_PATH = APP_DATA_DIR / "config.json"

STATUS_OPTIONS = ["Pendiente", "Perfecto estado", "Necesita mantenimiento", "Mal estado", "No aplica"]
STATUS_FACTOR = {"Pendiente": None, "Perfecto estado": 1.0, "Necesita mantenimiento": 0.5, "Mal estado": 0.0, "No aplica": None}
ACTION_OPTIONS = ["Sin acción", "Programar mantención", "Escalar a proveedor", "Revisar urgente"]
CASE_STATUS_OPTIONS = ["Abierto", "En revisión", "En gestión", "Esperando proveedor", "Resuelto pendiente validación", "Cerrado"]
PRIORITY_OPTIONS = ["Baja", "Media", "Alta", "Crítica"]
BUILDING_OPTIONS = ["Edificio MQ Centro", "Edificio MQ Parque", "Edificio MQ Vista", "Edificio demo"]

CHECKLIST = [
    {"space":"Accesos y control","items":[
        {"question":"Limpieza y orden de accesos","weight":3,"description":"Revisa si el acceso principal se encuentra limpio, sin basura, sin tierra acumulada y sin elementos que dificulten el ingreso o den mala imagen."},
        {"question":"Pintura y terminaciones visibles","weight":2,"description":"Observa muros, marcos, rejas o pilares del acceso. Busca pintura descascarada, golpes, humedad, óxido o terminaciones deterioradas."},
        {"question":"Iluminación exterior y señalética","weight":2,"description":"Confirma si las luces funcionan correctamente y si la señalética de acceso, numeración o indicaciones está visible y legible."},
        {"question":"Puertas / citófono / control de acceso","weight":3,"description":"Verifica apertura y cierre, estado de cerraduras, citófono, lector o control. Deben operar sin fallas ni riesgos evidentes."},
    ]},
    {"space":"Hall y recepción","items":[
        {"question":"Imagen general limpia y cuidada","weight":2,"description":"Evalúa la primera impresión del hall: limpieza, orden, aroma, ausencia de basura o elementos fuera de lugar."},
        {"question":"Pintura de muros, cielos y zócalos","weight":2,"description":"Busca manchas, rayados, grietas, humedad, pintura saltada o reparaciones visibles mal terminadas."},
        {"question":"Iluminación del hall y recepción","weight":2,"description":"Comprueba que todas las luminarias relevantes funcionen y que el espacio tenga visibilidad suficiente y homogénea."},
        {"question":"Mobiliario, vidrios y mesón","weight":2,"description":"Revisa limpieza y estado de muebles, vidrios, espejos, mesones y superficies de uso frecuente."},
        {"question":"Circulación libre y señalización visible","weight":2,"description":"Asegúrate de que no existan obstáculos, cajas, mobiliario mal ubicado o señalética ausente que complique la circulación."},
    ]},
    {"space":"Pasillos y escaleras","items":[
        {"question":"Pasillos limpios, secos y sin obstrucciones","weight":2,"description":"Revisa si el tránsito está despejado, si el piso está seco y si no hay suciedad, objetos almacenados o riesgos de tropiezo."},
        {"question":"Pintura y terminaciones de muros y cielos","weight":2,"description":"Observa desgaste visual, suciedad permanente, desprendimientos, grietas, manchas o intervenciones pendientes."},
        {"question":"Iluminación y señalización de circulación","weight":3,"description":"Valida que haya buena iluminación y que la señalización de circulación, emergencia o piso esté visible y correcta."},
        {"question":"Barandas, pasamanos y puertas cortafuego","weight":3,"description":"Comprueba estabilidad, limpieza, funcionamiento y ausencia de daños en elementos de seguridad y evacuación."},
    ]},
    {"space":"Ascensores","items":[
        {"question":"Limpieza interior de cabina","weight":2,"description":"Revisa piso, espejo, muros y botones del ascensor. Deben estar limpios y sin residuos visibles."},
        {"question":"Terminaciones visibles de cabina","weight":2,"description":"Busca golpes, rayas profundas, paneles sueltos, cielos dañados o desgaste importante en las terminaciones."},
        {"question":"Botones, indicadores y alarma","weight":3,"description":"Confirma que los botones respondan, los indicadores funcionen y los elementos de emergencia estén operativos o visibles."},
        {"question":"Puertas y funcionamiento general","weight":5,"description":"Evalúa apertura, cierre, nivelación, ruidos extraños, tiempos de espera y cualquier señal de falla en la operación general."},
    ]},
    {"space":"Áreas verdes y exteriores","items":[
        {"question":"Limpieza, poda y orden general","weight":2,"description":"Observa jardines, maceteros y espacios exteriores. Deben verse ordenados, mantenidos y sin residuos acumulados."},
        {"question":"Mobiliario exterior y terminaciones","weight":2,"description":"Revisa bancas, cierres, jardineras o elementos exteriores para detectar daños, óxido o desgaste excesivo."},
        {"question":"Iluminación exterior cercana","weight":2,"description":"Valida iluminación funcional en accesos, jardines, patios o senderos cercanos."},
        {"question":"Ausencia de residuos o daños visibles","weight":2,"description":"Busca basura, escombros, roturas, hundimientos, filtraciones o cualquier deterioro visible en el área exterior."},
    ]},
    {"space":"Quinchos / terraza / eventos","items":[
        {"question":"Limpieza del espacio y residuos","weight":2,"description":"Revisa si hay limpieza posterior al uso, ausencia de grasa, residuos, cenizas o basura acumulada."},
        {"question":"Pintura, muros y terminaciones","weight":2,"description":"Busca desgaste, manchas, humedad, desprendimientos o reparaciones pendientes en el espacio social."},
        {"question":"Parrillas, mesones o lavaplatos","weight":3,"description":"Valida limpieza, operatividad y estado físico de las superficies o artefactos de uso común."},
        {"question":"Iluminación y enchufes visibles","weight":3,"description":"Comprueba luces, enchufes y puntos eléctricos visibles, asegurando que no existan tapas rotas o riesgos evidentes."},
    ]},
    {"space":"Estacionamientos","items":[
        {"question":"Limpieza general y ausencia de derrames","weight":2,"description":"Revisa polvo excesivo, basura, líquidos, aceites u otros derrames que afecten seguridad o imagen."},
        {"question":"Pintura y demarcación","weight":2,"description":"Observa si la numeración, líneas, flechas o advertencias se mantienen visibles y en buen estado."},
        {"question":"Iluminación del estacionamiento","weight":3,"description":"Valida visibilidad suficiente, luminarias operativas y ausencia de sectores oscuros problemáticos."},
        {"question":"Portones / barreras / acceso vehicular","weight":3,"description":"Comprueba funcionamiento de portones, barreras, sensores, controles y seguridad del acceso vehicular."},
    ]},
    {"space":"Piscina","items":[
        {"question":"Limpieza del agua y superficie perimetral","weight":2,"description":"Revisa claridad del agua, presencia de hojas, suciedad, hongos o residuos en la piscina y su borde inmediato."},
        {"question":"Borde, pavimento y terminaciones cercanas","weight":2,"description":"Busca baldosas sueltas, fisuras, desniveles, superficies resbaladizas o terminaciones deterioradas alrededor de la piscina."},
        {"question":"Cierre, acceso y señalética de seguridad","weight":3,"description":"Confirma que existan barreras, puertas, cierres o señalética visible para normas de uso y seguridad."},
        {"question":"Mobiliario, duchas o equipamiento visible","weight":3,"description":"Evalúa reposeras, duchas, skimmers, rejillas u otros elementos visibles asociados al área de piscina."},
    ]},
    {"space":"Zona de basura y residuos","items":[
        {"question":"Limpieza y ausencia de derrames","weight":2,"description":"Revisa si hay líquidos, residuos fuera de contenedores o acumulación que genere suciedad persistente."},
        {"question":"Pintura, pisos y terminaciones","weight":2,"description":"Observa muros, piso, puertas y revestimientos; busca humedad, grietas, óxido o daño por uso intensivo."},
        {"question":"Contenedores y cierre del espacio","weight":2,"description":"Valida capacidad, estado y funcionamiento de contenedores, tapas, puertas o cerramientos del recinto."},
        {"question":"Ventilación, olores y orden general","weight":2,"description":"Evalúa si hay ventilación suficiente, olores anormales o desorden que amerite gestión."},
    ]},
    {"space":"Sala técnica / equipos visibles","items":[
        {"question":"Orden y limpieza del espacio técnico","weight":2,"description":"Verifica que el espacio no esté saturado, sucio o con elementos impropios que dificulten operación o seguridad."},
        {"question":"Pintura / pisos / terminaciones","weight":2,"description":"Busca deterioro visible, humedad, óxido o falta de mantención en superficies y terminaciones."},
        {"question":"Sin filtraciones, alertas o ruidos anormales","weight":4,"description":"Pon atención a fugas, goteos, alarmas, vibraciones o sonidos anormales en equipos o instalaciones visibles."},
        {"question":"Señalización y acceso restringido","weight":4,"description":"Confirma existencia de advertencias, identificación del área y control de acceso para evitar ingreso no autorizado."},
    ]},
]
assert sum(sum(item["weight"] for item in space["items"]) for space in CHECKLIST) == 100

MASTER_TABLES = [
    ("audits", "audits_summary.csv"),
    ("audits", "audit_items.csv"),
    ("audits", "audit_space_scores.csv"),
    ("audits", "audit_evidence.csv"),
    ("tracking", "cases_followup.csv"),
    ("tracking", "case_events.csv"),
]

def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")

def now_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

def html_escape(text: Any) -> str:
    text = "" if text is None else str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def default_storage_root() -> Path:
    return APP_DIR / "mq_auditorias_storage"

def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"storage_root": str(default_storage_root())}

def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

def get_storage_paths() -> dict[str, Path]:
    root = Path(st.session_state.app_config["storage_root"]).expanduser()
    paths = {
        "root": root,
        "audits": root / "01_auditorias",
        "media": root / "02_evidencias",
        "reports": root / "03_reportes",
        "tracking": root / "04_seguimiento",
        "exports": root / "05_exports",
        "drafts": root / "06_borradores",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths

def default_meta() -> dict[str, Any]:
    return {"building": BUILDING_OPTIONS[0], "auditor": "", "audit_type": "Semanal", "sector": "General", "general_notes": ""}

def blank_response() -> dict[str, Any]:
    return {"status": "Pendiente", "observation": "", "action": "Sin acción", "media_saved": []}

def build_blank_responses() -> dict[str, dict[str, Any]]:
    responses = {}
    for space in CHECKLIST:
        for item in space["items"]:
            responses[f"{space['space']}|{item['question']}"] = blank_response()
    return responses

def get_google_drive_config() -> dict[str, Any]:
    try:
        cfg = dict(st.secrets["google_oauth"])
    except Exception:
        return {"enabled": False, "reason": "No hay sección [google_oauth] en secrets."}
    enabled = bool(cfg.get("enabled", True))
    folder_id = str(cfg.get("folder_id", "")).strip()
    client_id = str(cfg.get("client_id", "")).strip()
    client_secret = str(cfg.get("client_secret", "")).strip()
    redirect_uri = str(cfg.get("redirect_uri", "")).strip()
    raw_scopes = cfg.get("scopes", ["https://www.googleapis.com/auth/drive.file"])
    scopes = [raw_scopes] if isinstance(raw_scopes, str) else [str(x) for x in raw_scopes]
    if not enabled:
        return {"enabled": False, "reason": "Google OAuth está desactivado."}
    if not folder_id or not client_id or not client_secret or not redirect_uri:
        return {"enabled": False, "reason": "Faltan folder_id / client_id / client_secret / redirect_uri."}
    return {"enabled": True, "folder_id": folder_id, "client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri, "scopes": scopes}

def drive_enabled() -> bool:
    return bool(get_google_drive_config().get("enabled", False))

def get_oauth_token_path() -> Path:
    return APP_DATA_DIR / "google_oauth_token.json"

def credentials_to_info(credentials) -> dict[str, Any]:
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

def load_saved_drive_credentials_info() -> dict[str, Any] | None:
    info = st.session_state.get("google_oauth_credentials_info")
    if info:
        return info
    token_path = get_oauth_token_path()
    if token_path.exists():
        try:
            info = json.loads(token_path.read_text(encoding="utf-8"))
            st.session_state.google_oauth_credentials_info = info
            return info
        except Exception:
            return None
    return None

def save_drive_credentials(credentials) -> None:
    info = credentials_to_info(credentials)
    st.session_state.google_oauth_credentials_info = info
    get_oauth_token_path().write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

def clear_drive_credentials() -> None:
    for key in ["google_oauth_credentials_info", "drive_folder_map", "drive_master_synced", "drive_init_error"]:
        st.session_state.pop(key, None)
    token_path = get_oauth_token_path()
    if token_path.exists():
        token_path.unlink()

def get_oauth_flow(state: str | None = None):
    from google_auth_oauthlib.flow import Flow
    cfg = get_google_drive_config()
    client_config = {"web": {"client_id": cfg["client_id"], "client_secret": cfg["client_secret"], "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}}
    flow = Flow.from_client_config(client_config, scopes=cfg["scopes"], state=state)
    flow.redirect_uri = cfg["redirect_uri"]
    return flow

def get_google_auth_url() -> str:
    flow = get_oauth_flow()
    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    st.session_state.google_oauth_state = state
    return auth_url

def handle_google_oauth_callback() -> None:
    if not drive_enabled():
        return
    try:
        qp = st.query_params
        code = qp.get("code")
        error = qp.get("error")
        state = qp.get("state")
    except Exception:
        return
    if error:
        st.session_state.drive_status_message = f"Google OAuth devolvió error: {error}"
        try: st.query_params.clear()
        except Exception: pass
        return
    if not code:
        return
    try:
        expected_state = st.session_state.get("google_oauth_state")
        flow = get_oauth_flow(state=state or expected_state)
        flow.fetch_token(code=code)
        save_drive_credentials(flow.credentials)
        st.session_state.drive_status_message = "Google Drive conectado correctamente."
        st.session_state.pop("drive_init_error", None)
    except Exception as exc:
        st.session_state.drive_init_error = str(exc)
        st.session_state.drive_status_message = f"No se pudo completar OAuth: {exc}"
    finally:
        try: st.query_params.clear()
        except Exception: pass

def get_drive_client():
    cfg = get_google_drive_config()
    if not cfg.get("enabled"):
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        info = load_saved_drive_credentials_info()
        if not info:
            return None
        credentials = Credentials.from_authorized_user_info(info, scopes=cfg["scopes"])
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            save_drive_credentials(credentials)
        if not credentials.valid:
            return None
        return build("drive", "v3", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        st.session_state.drive_init_error = str(exc)
        return None

def _record_drive_error(exc: Exception, prefix: str = "No se pudo usar Google Drive") -> None:
    st.session_state.drive_status_message = f"{prefix}: {exc}. Se mantuvo guardado local."

def _drive_query_escape(value: str) -> str:
    return value.replace("'", "\\'")

def ensure_drive_folder(service, parent_id: str, folder_name: str) -> dict[str, str]:
    query = f"name = '{_drive_query_escape(folder_name)}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed = false"
    try:
        response = service.files().list(q=query, fields="files(id, name, webViewLink)", pageSize=10, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = response.get("files", [])
        if files:
            folder = files[0]
            return {"id": folder["id"], "name": folder.get("name", folder_name), "webViewLink": folder.get("webViewLink", f"https://drive.google.com/drive/folders/{folder['id']}")}
        created = service.files().create(body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}, fields="id, name, webViewLink", supportsAllDrives=True).execute()
        return {"id": created["id"], "name": created.get("name", folder_name), "webViewLink": created.get("webViewLink", f"https://drive.google.com/drive/folders/{created['id']}")}
    except Exception as exc:
        _record_drive_error(exc)
        return {}

def get_drive_folder_map() -> dict[str, dict[str, str]]:
    if "drive_folder_map" in st.session_state:
        return st.session_state.drive_folder_map
    cfg = get_google_drive_config()
    service = get_drive_client()
    if not cfg.get("enabled") or service is None:
        return {}
    root_id = cfg["folder_id"]
    folder_map = {"root": {"id": root_id, "name": "root", "webViewLink": f"https://drive.google.com/drive/folders/{root_id}"}}
    for key, folder_name in [("audits", "01_auditorias"), ("media", "02_evidencias"), ("reports", "03_reportes"), ("tracking", "04_seguimiento"), ("exports", "05_exports")]:
        folder = ensure_drive_folder(service, root_id, folder_name)
        if not folder:
            return {}
        folder_map[key] = folder
    st.session_state.drive_folder_map = folder_map
    return folder_map

def find_drive_file(service, parent_id: str, file_name: str) -> dict[str, Any] | None:
    query = f"name = '{_drive_query_escape(file_name)}' and '{parent_id}' in parents and trashed = false"
    try:
        response = service.files().list(q=query, fields="files(id, name, mimeType, webViewLink, webContentLink)", pageSize=10, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = response.get("files", [])
        return files[0] if files else None
    except Exception as exc:
        _record_drive_error(exc)
        return None

def upload_file_to_drive(local_path: Path, parent_id: str, mime_type: str | None = None, overwrite: bool = True) -> dict[str, Any]:
    service = get_drive_client()
    if service is None:
        return {}
    from googleapiclient.http import MediaFileUpload
    try:
        existing = find_drive_file(service, parent_id, local_path.name) if overwrite else None
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=False)
        if existing:
            return service.files().update(fileId=existing["id"], media_body=media, fields="id, name, webViewLink, webContentLink", supportsAllDrives=True).execute()
        return service.files().create(body={"name": local_path.name, "parents": [parent_id]}, media_body=media, fields="id, name, webViewLink, webContentLink", supportsAllDrives=True).execute()
    except Exception as exc:
        _record_drive_error(exc, prefix="No se pudo subir a Google Drive")
        return {}

def download_drive_file_to_path(file_id: str, destination: Path) -> None:
    service = get_drive_client()
    if service is None:
        return
    from googleapiclient.http import MediaIoBaseDownload
    try:
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(fh.getvalue())
    except Exception as exc:
        _record_drive_error(exc, prefix="No se pudo descargar desde Google Drive")

def sync_master_tables_from_drive(force: bool = False) -> None:
    if not drive_enabled():
        return
    if st.session_state.get("drive_master_synced") and not force:
        return
    folder_map = get_drive_folder_map()
    service = get_drive_client()
    paths = get_storage_paths()
    if not folder_map or service is None:
        return
    try:
        for section, file_name in MASTER_TABLES:
            drive_file = find_drive_file(service, folder_map[section]["id"], file_name)
            if drive_file:
                download_drive_file_to_path(drive_file["id"], paths[section] / file_name)
        st.session_state.drive_master_synced = True
        st.session_state.drive_status_message = "Sincronización desde Google Drive completada."
    except Exception as exc:
        _record_drive_error(exc, prefix="No se pudo sincronizar desde Google Drive")

def sync_master_tables_to_drive() -> None:
    if not drive_enabled():
        return
    folder_map = get_drive_folder_map()
    if not folder_map:
        return
    paths = get_storage_paths()
    try:
        for section, file_name in MASTER_TABLES:
            local_path = paths[section] / file_name
            if local_path.exists():
                upload_file_to_drive(local_path, folder_map[section]["id"], mime_type="text/csv", overwrite=True)
    except Exception as exc:
        _record_drive_error(exc, prefix="No se pudo sincronizar hacia Google Drive")

def sync_artifact_to_drive(local_path: Path, section: str, mime_type: str) -> dict[str, Any]:
    if not drive_enabled() or not local_path.exists():
        return {}
    folder_map = get_drive_folder_map()
    if not folder_map:
        return {}
    return upload_file_to_drive(local_path, folder_map[section]["id"], mime_type=mime_type, overwrite=True)

def safe_read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=columns or [])

def append_dataframe(path: Path, df_new: pd.DataFrame) -> None:
    if path.exists():
        try: df_old = pd.read_csv(path)
        except Exception: df_old = pd.DataFrame()
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new.copy()
    df_all.to_csv(path, index=False)

def score_label(score: float) -> tuple[str, str]:
    if score >= 90: return "Estándar alto", "good"
    if score >= 80: return "Buen estado general", "good"
    if score >= 70: return "Aceptable con mejoras", "warn"
    if score >= 60: return "Requiere plan de acción", "warn"
    return "Brechas relevantes", "bad"

def priority_from_status(status: str) -> str:
    return "Alta" if status == "Mal estado" else "Media"

def guess_extension(mime_type: str | None) -> str:
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "video/mp4": ".mp4", "video/quicktime": ".mov", "video/x-msvideo": ".avi", "video/webm": ".webm"}.get(mime_type or "", ".bin")

def get_active_draft_path() -> Path:
    return get_storage_paths()["drafts"] / "active_draft.json"

def draft_payload() -> dict[str, Any]:
    return {"draft_id": st.session_state.get("draft_id", now_id("DRAFT")), "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "current_space_idx": st.session_state.get("current_space_idx", 0), "audit_meta": st.session_state.audit_meta, "responses": st.session_state.responses}

def save_draft_state() -> None:
    payload = draft_payload()
    st.session_state["draft_id"] = payload["draft_id"]
    get_active_draft_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    st.session_state.last_draft_saved_at = payload["saved_at"]

def load_draft_state() -> bool:
    draft_path = get_active_draft_path()
    if not draft_path.exists():
        return False
    try:
        payload = json.loads(draft_path.read_text(encoding="utf-8"))
        st.session_state["draft_id"] = payload.get("draft_id", now_id("DRAFT"))
        st.session_state.current_space_idx = int(payload.get("current_space_idx", 0))
        st.session_state.audit_meta = payload.get("audit_meta", deepcopy(default_meta()))
        responses = build_blank_responses()
        for key, value in payload.get("responses", {}).items():
            if key in responses and isinstance(value, dict):
                responses[key].update(value)
        st.session_state.responses = responses
        st.session_state.last_draft_saved_at = payload.get("saved_at", "")
        return True
    except Exception:
        return False

def clear_draft_state() -> None:
    draft_path = get_active_draft_path()
    if draft_path.exists():
        draft_path.unlink()
    st.session_state.pop("draft_id", None)
    st.session_state.pop("last_draft_saved_at", None)

def init_state() -> None:
    if "app_config" not in st.session_state:
        st.session_state.app_config = load_config()
    if "audit_meta" not in st.session_state:
        st.session_state.audit_meta = deepcopy(default_meta())
    if "responses" not in st.session_state:
        st.session_state.responses = build_blank_responses()
    if "current_space_idx" not in st.session_state:
        st.session_state.current_space_idx = 0
    if "draft_loaded_attempted" not in st.session_state:
        st.session_state.draft_loaded_attempted = True
        load_draft_state()
    if "saved_message" not in st.session_state:
        st.session_state.saved_message = ""
    if "last_save_result" not in st.session_state:
        st.session_state.last_save_result = {}
    if "drive_status_message" not in st.session_state:
        st.session_state.drive_status_message = ""

def calculate_score() -> tuple[float, float, list[dict[str, Any]], int, int]:
    obtained = 0.0
    applicable = 0.0
    answered = 0
    total_questions = 0
    issues = []
    for space in CHECKLIST:
        for item in space["items"]:
            total_questions += 1
            key = f"{space['space']}|{item['question']}"
            entry = st.session_state.responses[key]
            status = entry["status"]
            factor = STATUS_FACTOR.get(status)
            if status != "Pendiente":
                answered += 1
            if status == "No aplica":
                continue
            if factor is not None:
                applicable += item["weight"]
                obtained += item["weight"] * factor
            if status in ["Necesita mantenimiento", "Mal estado"]:
                issues.append({"Espacio": space["space"], "Pregunta": item["question"], "Estado": status, "Acción": entry["action"], "Observación": entry["observation"], "Peso": item["weight"], "Prioridad": priority_from_status(status), "Evidencias": len(entry.get("media_saved", []))})
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
        rows.append({"space": space["space"], "space_score": round((obtained / applicable) * 100, 1) if applicable else 0.0, "answered_items": answered_items, "total_items": total_items, "active_issues": active_issues})
    return pd.DataFrame(rows)

def current_space() -> dict[str, Any]:
    return CHECKLIST[st.session_state.current_space_idx]

def persist_runtime_uploads_for_key(key: str, target_root: Path) -> list[dict[str, Any]]:
    uploaded_media = st.session_state.get(f"media_{slugify(key)}") or []
    existing = st.session_state.responses[key].get("media_saved", []) or []
    saved_files = [m for m in existing if Path(m.get("path", "")).exists()]
    seen = {(m.get("original_name"), m.get("mime"), Path(m.get("path", "")).name) for m in saved_files}
    target_root.mkdir(parents=True, exist_ok=True)
    idx_start = len(saved_files)
    for offset, media in enumerate(uploaded_media, start=1):
        suffix = Path(media.name or "archivo").suffix or guess_extension(getattr(media, "type", None))
        file_name = f"{slugify(key)}_{idx_start + offset}{suffix}"
        sig = (media.name, getattr(media, "type", None), file_name)
        if sig in seen:
            continue
        file_path = target_root / file_name
        file_path.write_bytes(media.getbuffer().tobytes())
        saved_files.append({"name": file_name, "original_name": media.name, "source": "uploader", "mime": getattr(media, "type", None), "path": str(file_path.resolve())})
        seen.add(sig)
    st.session_state.responses[key]["media_saved"] = saved_files
    return saved_files

def persist_visible_section_uploads_to_draft() -> None:
    paths = get_storage_paths()
    draft_id = st.session_state.get("draft_id", now_id("DRAFT"))
    st.session_state["draft_id"] = draft_id
    space = current_space()
    for item in space["items"]:
        key = f"{space['space']}|{item['question']}"
        persist_runtime_uploads_for_key(key, paths["drafts"] / draft_id / slugify(key))

def render_evidence_preview(key: str) -> None:
    saved_media = st.session_state.responses[key].get("media_saved", []) or []
    current_uploads = st.session_state.get(f"media_{slugify(key)}") or []
    if saved_media:
        st.caption(f"Evidencias guardadas en borrador: {len(saved_media)}")
    if current_uploads:
        st.caption(f"Archivos seleccionados actualmente: {len(current_uploads)}")

def generate_report_html(audit_id: str, meta: dict[str, Any], score: float, progress: float, issues_df: pd.DataFrame, spaces_df: pd.DataFrame, cases_created: int, cases_updated: int) -> Path:
    report_path = get_storage_paths()["reports"] / f"reporte_{audit_id}.html"
    issue_rows = "".join([
        "<tr>" +
        f"<td>{html_escape(r.get('Espacio'))}</td><td>{html_escape(r.get('Pregunta'))}</td><td>{html_escape(r.get('Estado'))}</td><td>{html_escape(r.get('Acción'))}</td><td>{html_escape(r.get('Prioridad'))}</td>" +
        "</tr>"
        for _, r in issues_df.iterrows()
    ]) if not issues_df.empty else "<tr><td colspan='5'>Sin hallazgos activos.</td></tr>"
    space_rows = "".join([
        "<tr>" +
        f"<td>{html_escape(r['space'])}</td><td>{r['space_score']}</td><td>{r['answered_items']}/{r['total_items']}</td><td>{r['active_issues']}</td>" +
        "</tr>"
        for _, r in spaces_df.iterrows()
    ])
    html = f"""<html><head><meta charset='utf-8'><style>
    body {{font-family:Arial,sans-serif; margin:24px; color:#17324d;}}
    .hero {{background:#f5f9ff; border:1px solid #d7e6fb; border-radius:18px; padding:16px; margin-bottom:16px;}}
    .score {{float:right; background:#16324d; color:white; padding:10px 14px; border-radius:12px; font-weight:bold;}}
    table {{width:100%; border-collapse:collapse; margin-top:8px;}}
    th,td {{border:1px solid #e2e8f0; padding:8px; text-align:left; font-size:13px;}}
    th {{background:#f8fbff;}}</style></head><body>
    <div class='hero'><div class='score'>{score}/100</div>
    <h1>Informe de auditoría</h1>
    <p><b>Edificio:</b> {html_escape(meta['building'])}<br><b>Auditor:</b> {html_escape(meta['auditor'])}<br><b>Fecha:</b> {html_escape(meta['timestamp_human'])}<br><b>Tipo:</b> {html_escape(meta['audit_type'])} · <b>Sector:</b> {html_escape(meta['sector'])}</p>
    <p><b>Progreso:</b> {progress}% · <b>Casos creados:</b> {cases_created} · <b>Casos actualizados:</b> {cases_updated}</p>
    <p><b>Notas generales:</b> {html_escape(meta.get('general_notes','')) or 'Sin observaciones.'}</p></div>
    <h2>Puntaje por espacio</h2><table><thead><tr><th>Espacio</th><th>Score</th><th>Respondido</th><th>Hallazgos</th></tr></thead><tbody>{space_rows}</tbody></table>
    <h2>Hallazgos</h2><table><thead><tr><th>Espacio</th><th>Pregunta</th><th>Estado</th><th>Acción</th><th>Prioridad</th></tr></thead><tbody>{issue_rows}</tbody></table>
    </body></html>"""
    report_path.write_text(html, encoding="utf-8")
    return report_path

def generate_report_json(audit_id: str, meta: dict[str, Any], score: float, progress: float, issues_df: pd.DataFrame, spaces_df: pd.DataFrame, items_df: pd.DataFrame, cases_created: int, cases_updated: int) -> Path:
    json_path = get_storage_paths()["audits"] / f"auditoria_{audit_id}.json"
    payload = {"audit_id": audit_id, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "meta": meta, "score": score, "progress": progress, "summary_label": score_label(score)[0], "issue_count": int(len(issues_df)), "cases_created": int(cases_created), "cases_updated": int(cases_updated), "space_scores": spaces_df.to_dict(orient="records"), "issues": issues_df.to_dict(orient="records"), "items": items_df.to_dict(orient="records"), "general_notes": meta.get("general_notes", "")}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path

def upsert_followup_cases(audit_id: str, items_df: pd.DataFrame) -> tuple[int, int]:
    paths = get_storage_paths()
    cases_path = paths["tracking"] / "cases_followup.csv"
    events_path = paths["tracking"] / "case_events.csv"
    case_columns = ["case_id","building","sector","space","question","description","priority","case_status","responsible","created_at","due_date","closed_at","last_review_at","latest_audit_id","latest_audit_timestamp","latest_audit_status","latest_action","latest_observation","timeline_note","evidence_count","last_report_path"]
    event_columns = ["event_id","case_id","event_at","event_type","note","audit_id"]
    cases_df = safe_read_csv(cases_path, case_columns)
    events_df = safe_read_csv(events_path, event_columns)
    issue_items = items_df[items_df["status"].isin(["Necesita mantenimiento", "Mal estado"])].copy()
    if issue_items.empty:
        if not cases_path.exists(): cases_df.to_csv(cases_path, index=False)
        if not events_path.exists(): events_df.to_csv(events_path, index=False)
        return 0, 0
    created = 0
    updated = 0
    event_rows = []
    for _, row in issue_items.iterrows():
        mask = ((cases_df.get("building", pd.Series(dtype=str)) == row["building"]) & (cases_df.get("sector", pd.Series(dtype=str)) == row["sector"]) & (cases_df.get("space", pd.Series(dtype=str)) == row["space"]) & (cases_df.get("question", pd.Series(dtype=str)) == row["question"]) & (cases_df.get("case_status", pd.Series(dtype=str)) != "Cerrado"))
        if not cases_df.empty and mask.any():
            idx = cases_df[mask].index[0]
            for field, value in [("priority", row["priority"]), ("last_review_at", row["timestamp_human"]), ("latest_audit_id", audit_id), ("latest_audit_timestamp", row["timestamp_human"]), ("latest_audit_status", row["status"]), ("latest_action", row["action"]), ("latest_observation", row["observation"]), ("timeline_note", f"Actualizado por auditoría {audit_id}."), ("evidence_count", row["evidence_count"])]:
                cases_df.loc[idx, field] = value
            updated += 1
            event_rows.append({"event_id": now_id("EVT"), "case_id": cases_df.loc[idx, "case_id"], "event_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "event_type": "Actualización por auditoría", "note": f"Se actualiza hallazgo: {row['status']} · {row['action']}", "audit_id": audit_id})
        else:
            case_id = now_id("CASO")
            new_row = {"case_id": case_id, "building": row["building"], "sector": row["sector"], "space": row["space"], "question": row["question"], "description": row["description"], "priority": row["priority"], "case_status": "Abierto", "responsible": "", "created_at": row["timestamp_human"], "due_date": "", "closed_at": "", "last_review_at": row["timestamp_human"], "latest_audit_id": audit_id, "latest_audit_timestamp": row["timestamp_human"], "latest_audit_status": row["status"], "latest_action": row["action"], "latest_observation": row["observation"], "timeline_note": "Caso creado desde auditoría.", "evidence_count": row["evidence_count"], "last_report_path": row["report_path"]}
            cases_df = pd.concat([cases_df, pd.DataFrame([new_row])], ignore_index=True)
            created += 1
            event_rows.append({"event_id": now_id("EVT"), "case_id": case_id, "event_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "event_type": "Creación por auditoría", "note": f"Se crea caso con prioridad {row['priority']} y acción {row['action']}.", "audit_id": audit_id})
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
    append_dataframe(events_path, pd.DataFrame([{"event_id": now_id("EVT"), "case_id": case_id, "event_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "event_type": "Seguimiento manual", "note": note, "audit_id": ""}]))
    sync_master_tables_to_drive()

def build_items_dataframe(audit_id: str, timestamp_human: str, score: float, progress: float, report_path: str) -> pd.DataFrame:
    item_rows = []
    audit_media_root = get_storage_paths()["media"] / audit_id
    for space in CHECKLIST:
        for item in space["items"]:
            key = f"{space['space']}|{item['question']}"
            entry = st.session_state.responses[key]
            final_saved = persist_runtime_uploads_for_key(key, audit_media_root / slugify(key))
            if drive_enabled() and final_saved:
                folder_map = get_drive_folder_map()
                service = get_drive_client()
                if folder_map and service is not None:
                    audit_folder = ensure_drive_folder(service, folder_map["media"]["id"], audit_id)
                    item_folder = ensure_drive_folder(service, audit_folder["id"], slugify(key)) if audit_folder else {}
                    enriched = []
                    for media in final_saved:
                        uploaded = upload_file_to_drive(Path(media["path"]), item_folder.get("id", ""), mime_type=media.get("mime"), overwrite=True) if item_folder else {}
                        enriched.append({**media, "drive_file_id": uploaded.get("id", ""), "drive_web_view_link": uploaded.get("webViewLink", ""), "drive_web_content_link": uploaded.get("webContentLink", "")})
                    final_saved = enriched
                    entry["media_saved"] = final_saved
                    st.session_state.responses[key] = entry
            item_rows.append({
                "audit_id": audit_id, "timestamp_human": timestamp_human, "building": st.session_state.audit_meta["building"], "auditor": st.session_state.audit_meta["auditor"], "audit_type": st.session_state.audit_meta["audit_type"], "sector": st.session_state.audit_meta["sector"], "space": space["space"], "question": item["question"], "description": item["description"], "weight": item["weight"], "status": entry["status"], "action": entry["action"], "observation": entry["observation"], "priority": priority_from_status(entry["status"]) if entry["status"] in ["Necesita mantenimiento", "Mal estado"] else "", "evidence_count": len(final_saved), "evidence_paths": [m["path"] for m in final_saved], "evidence_drive_links": [m.get("drive_web_view_link", "") for m in final_saved], "evidence_drive_ids": [m.get("drive_file_id", "") for m in final_saved], "score_total": score, "progress": progress, "report_path": report_path,
            })
    return pd.DataFrame(item_rows)

def save_audit() -> None:
    audit_id = now_id("AUD")
    timestamp_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    score, progress, issues, answered, total_questions = calculate_score()
    space_scores_df = calculate_space_scores()
    provisional_report_path = get_storage_paths()["reports"] / f"reporte_{audit_id}.html"
    items_df = build_items_dataframe(audit_id, timestamp_human, score, progress, str(provisional_report_path.resolve()))
    cases_created, cases_updated = upsert_followup_cases(audit_id, items_df)
    meta = {**st.session_state.audit_meta, "timestamp_human": timestamp_human}
    report_path = generate_report_html(audit_id, meta, score, progress, pd.DataFrame(issues), space_scores_df, cases_created, cases_updated)
    json_report_path = generate_report_json(audit_id, meta, score, progress, pd.DataFrame(issues), space_scores_df, items_df, cases_created, cases_updated)
    items_df["report_path"] = str(report_path.resolve())
    report_drive = sync_artifact_to_drive(report_path, "reports", "text/html")
    json_drive = sync_artifact_to_drive(json_report_path, "audits", "application/json")
    paths = get_storage_paths()
    audits_summary_df = pd.DataFrame([{"audit_id": audit_id, "timestamp_human": timestamp_human, "building": st.session_state.audit_meta["building"], "auditor": st.session_state.audit_meta["auditor"], "audit_type": st.session_state.audit_meta["audit_type"], "sector": st.session_state.audit_meta["sector"], "general_notes": st.session_state.audit_meta["general_notes"], "score_total": score, "score_label": score_label(score)[0], "progress": progress, "answered": answered, "total_questions": total_questions, "issue_count": len(issues), "cases_created": cases_created, "cases_updated": cases_updated, "report_path": str(report_path.resolve()), "json_path": str(json_report_path.resolve()), "report_drive_link": report_drive.get("webViewLink", ""), "json_drive_link": json_drive.get("webViewLink", ""), "evidence_dir": str((paths["media"] / audit_id).resolve())}])
    space_scores_df = space_scores_df.copy()
    space_scores_df.insert(0, "audit_id", audit_id)
    space_scores_df.insert(1, "timestamp_human", timestamp_human)
    evidence_rows = []
    for _, row in items_df.iterrows():
        for idx, p in enumerate(row["evidence_paths"]):
            evidence_rows.append({"audit_id": audit_id, "timestamp_human": timestamp_human, "building": row["building"], "sector": row["sector"], "space": row["space"], "question": row["question"], "path": p, "drive_web_view_link": row["evidence_drive_links"][idx] if idx < len(row["evidence_drive_links"]) else ""})
    evidence_df = pd.DataFrame(evidence_rows)
    append_dataframe(paths["audits"] / "audits_summary.csv", audits_summary_df)
    append_dataframe(paths["audits"] / "audit_items.csv", items_df)
    append_dataframe(paths["audits"] / "audit_space_scores.csv", space_scores_df)
    if not evidence_df.empty:
        append_dataframe(paths["audits"] / "audit_evidence.csv", evidence_df)
    export_path = paths["exports"] / f"auditoria_{audit_id}_detalle.csv"
    items_df.to_csv(export_path, index=False)
    export_drive = sync_artifact_to_drive(export_path, "exports", "text/csv")
    sync_master_tables_to_drive()
    st.session_state.saved_message = f"Auditoría guardada: {audit_id}"
    st.session_state.last_save_result = {"audit_id": audit_id, "report_path": str(report_path.resolve()), "json_path": str(json_report_path.resolve()), "export_path": str(export_path.resolve()), "cases_created": cases_created, "cases_updated": cases_updated, "report_drive_link": report_drive.get("webViewLink", ""), "json_drive_link": json_drive.get("webViewLink", ""), "export_drive_link": export_drive.get("webViewLink", "")}
    clear_draft_state()

def inject_css() -> None:
    st.markdown("""
    <style>
    .block-container {max-width:760px; padding-top:0.8rem; padding-bottom:4rem;}
    .hero-card {background:linear-gradient(135deg,#f7fbff 0%,#eaf3ff 100%); border:1px solid #d8e8ff; border-radius:22px; padding:18px; margin-bottom:12px;}
    .section-card {background:white; border:1px solid #e6eef7; border-radius:18px; padding:12px 14px; margin-bottom:14px; box-shadow:0 6px 16px rgba(14,49,94,.04);}
    .item-card {background:#fff; border:1px solid #edf2f8; border-radius:16px; padding:12px; margin-bottom:14px;}
    .muted {color:#64748b; font-size:.92rem;}
    .space-title {font-weight:700; font-size:1.05rem; color:#15314b;}
    .badge {display:inline-block; padding:4px 10px; border-radius:999px; background:#e9f2ff; color:#245fdd; font-size:.8rem; font-weight:600;}
    .small-hint {font-size:.85rem; color:#64748b; margin-bottom:4px;}
    div[data-baseweb="select"] > div, textarea, input {border-radius:12px !important;}
    </style>
    """, unsafe_allow_html=True)

def header() -> None:
    st.markdown("""
    <div class="hero-card">
      <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
        <div>
          <div style="font-size:1.3rem; font-weight:800; color:#16324d;">Auditoría móvil del edificio</div>
          <div class="muted">Versión estable para móvil · por secciones · sin cámara embebida · con borrador.</div>
        </div>
        <div class="badge">Móvil estable</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_storage_config() -> None:
    with st.expander("Configuración de almacenamiento y nube"):
        drive_ok = drive_enabled() and get_drive_client() is not None
        if drive_ok:
            st.success("Google Drive conectado. En esta versión la sincronización ocurre solo al guardar o de forma manual.")
            folder_map = get_drive_folder_map()
            if folder_map.get("root", {}).get("webViewLink"):
                st.link_button("Abrir carpeta raíz en Drive", folder_map["root"]["webViewLink"])
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("Volver a autorizar con Google", get_google_auth_url())
            with c2:
                if st.button("Desconectar Google Drive", key="oauth_disconnect"):
                    clear_drive_credentials()
                    st.success("Conexión eliminada.")
        else:
            reason = get_google_drive_config().get("reason", st.session_state.get("drive_init_error", "No se pudo inicializar Google Drive."))
            st.warning(f"Google Drive no está activo todavía. Motivo: {reason}")
            if drive_enabled():
                st.link_button("Conectar con Google Drive", get_google_auth_url())
        if st.session_state.get("drive_status_message"):
            st.info(st.session_state["drive_status_message"])
        storage_root = st.text_input("Carpeta local temporal / fallback", value=st.session_state.app_config.get("storage_root", str(default_storage_root())))
        if st.button("Guardar configuración local", key="save_local_config"):
            st.session_state.app_config["storage_root"] = storage_root.strip() or str(default_storage_root())
            save_config(st.session_state.app_config)
            get_storage_paths()
            st.success("Configuración local guardada.")
        st.code(str(get_storage_paths()["root"]))
        st.caption("Durante la auditoría no se sincroniza con Drive. La subida ocurre al guardar o con botones manuales.")

def render_meta() -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Inicio de auditoría")
    c1, c2 = st.columns(2)
    with c1:
        idx = BUILDING_OPTIONS.index(st.session_state.audit_meta.get("building", BUILDING_OPTIONS[0]))
        st.session_state.audit_meta["building"] = st.selectbox("Edificio", BUILDING_OPTIONS, index=idx)
        options = ["Semanal", "Mensual profunda", "Validación de cierre", "Extraordinaria"]
        current = st.session_state.audit_meta.get("audit_type", "Semanal")
        st.session_state.audit_meta["audit_type"] = st.selectbox("Tipo de auditoría", options, index=options.index(current) if current in options else 0)
    with c2:
        st.session_state.audit_meta["auditor"] = st.text_input("Auditor", value=st.session_state.audit_meta.get("auditor", ""))
        st.session_state.audit_meta["sector"] = st.text_input("Sector / torre", value=st.session_state.audit_meta.get("sector", "General"))
    st.session_state.audit_meta["general_notes"] = st.text_area("Observación general", value=st.session_state.audit_meta.get("general_notes", ""), height=90)
    st.markdown('</div>', unsafe_allow_html=True)

def render_dashboard() -> None:
    score, _, issues, answered, total_questions = calculate_score()
    label, _ = score_label(score)
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Score", f"{score}/100")
    with c2: st.metric("Respondidas", f"{answered}/{total_questions}")
    with c3: st.metric("Hallazgos", len(issues))
    st.caption(label)
    if st.session_state.get("last_draft_saved_at"):
        st.caption(f"Borrador guardado: {st.session_state['last_draft_saved_at']}")

def set_current_space(idx: int) -> None:
    persist_visible_section_uploads_to_draft()
    save_draft_state()
    st.session_state.current_space_idx = idx

def render_space_selector() -> None:
    names = [s["space"] for s in CHECKLIST]
    current_idx = st.session_state.current_space_idx
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Sección actual")
    st.session_state.current_space_idx = st.selectbox("Espacio a revisar", list(range(len(names))), index=current_idx, format_func=lambda i: f"{i+1}. {names[i]}")
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("← Anterior", use_container_width=True, disabled=st.session_state.current_space_idx == 0):
            set_current_space(st.session_state.current_space_idx - 1)
            st.rerun()
    with c2:
        if st.button("Siguiente →", use_container_width=True, disabled=st.session_state.current_space_idx == len(names)-1):
            set_current_space(st.session_state.current_space_idx + 1)
            st.rerun()
    with c3:
        st.progress((st.session_state.current_space_idx + 1) / len(names))
        st.caption(f"Sección {st.session_state.current_space_idx + 1} de {len(names)}")
    st.markdown('</div>', unsafe_allow_html=True)

def render_evidence_preview(key: str) -> None:
    saved_media = st.session_state.responses[key].get("media_saved", []) or []
    current_uploads = st.session_state.get(f"media_{slugify(key)}") or []
    if saved_media:
        st.caption(f"Evidencias guardadas en borrador: {len(saved_media)}")
    if current_uploads:
        st.caption(f"Archivos seleccionados actualmente: {len(current_uploads)}")

def render_current_space() -> None:
    space = CHECKLIST[st.session_state.current_space_idx]
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f"<div class='space-title'>{space['space']}</div><div class='muted'>Solo se carga esta sección para que la app sea más estable en iPhone.</div>", unsafe_allow_html=True)
    for item in space["items"]:
        key = f"{space['space']}|{item['question']}"
        entry = st.session_state.responses[key]
        st.markdown('<div class="item-card">', unsafe_allow_html=True)
        st.markdown(f"**{item['question']}**")
        st.caption(f"Puntaje máximo: {item['weight']}")
        entry["status"] = st.selectbox("Estado", STATUS_OPTIONS, index=STATUS_OPTIONS.index(entry["status"]), key=f"status_{slugify(key)}", help=item["description"])
        if entry["status"] in ["Necesita mantenimiento", "Mal estado"]:
            entry["action"] = st.selectbox("Acción requerida", ACTION_OPTIONS, index=ACTION_OPTIONS.index(entry.get("action", "Sin acción")), key=f"action_{slugify(key)}")
            st.markdown("<div class='small-hint'>Fotos o video</div>", unsafe_allow_html=True)
            st.file_uploader("Subir evidencias", type=["jpg","jpeg","png","webp","mp4","mov","avi","webm"], accept_multiple_files=True, key=f"media_{slugify(key)}", label_visibility="collapsed", help="Puedes seleccionar imágenes o un video desde tu teléfono.")
            entry["observation"] = st.text_area("Observación", key=f"obs_{slugify(key)}", value=entry.get("observation", ""), height=80)
        else:
            entry["action"] = "Sin acción"
        st.session_state.responses[key] = entry
        render_evidence_preview(key)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def persist_visible_section_uploads_to_draft() -> None:
    paths = get_storage_paths()
    draft_id = st.session_state.get("draft_id", now_id("DRAFT"))
    st.session_state["draft_id"] = draft_id
    space = CHECKLIST[st.session_state.current_space_idx]
    for item in space["items"]:
        key = f"{space['space']}|{item['question']}"
        persist_runtime_uploads_for_key(key, paths["drafts"] / draft_id / slugify(key))

def reset_responses() -> None:
    st.session_state.audit_meta = deepcopy(default_meta())
    st.session_state.responses = build_blank_responses()
    st.session_state.current_space_idx = 0
    for key in list(st.session_state.keys()):
        if key.startswith(("status_", "action_", "obs_", "media_")):
            del st.session_state[key]
    clear_draft_state()

def render_summary() -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Guardado")
    score, _, issues, _, _ = calculate_score()
    st.write("Esta versión guarda el avance localmente primero y solo sube a Drive al final.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Guardar avance", use_container_width=True):
            persist_visible_section_uploads_to_draft()
            save_draft_state()
            st.success("Avance guardado.")
    with c2:
        if st.button("Restaurar borrador", use_container_width=True):
            if load_draft_state():
                st.success("Borrador restaurado.")
                st.rerun()
            else:
                st.warning("No se encontró borrador.")
    with c3:
        if st.button("Reiniciar", use_container_width=True):
            reset_responses()
            st.success("Formulario reiniciado.")
            st.rerun()
    if st.button("Guardar auditoría final", type="primary", use_container_width=True):
        if not st.session_state.audit_meta["auditor"].strip():
            st.error("Ingresa el nombre del auditor antes de guardar.")
        else:
            persist_visible_section_uploads_to_draft()
            save_draft_state()
            save_audit()
            st.success(st.session_state.saved_message)
            result = st.session_state.last_save_result
            st.info(f"Reporte: {result.get('report_path','-')} · JSON: {result.get('json_path','-')} · Casos creados: {result.get('cases_created',0)} · actualizados: {result.get('cases_updated',0)}")
            if result.get("report_drive_link"): st.link_button("Abrir reporte en Google Drive", result["report_drive_link"])
            if result.get("json_drive_link"): st.link_button("Abrir JSON en Google Drive", result["json_drive_link"])
    if issues:
        st.dataframe(pd.DataFrame(issues)[["Espacio","Pregunta","Estado","Acción","Prioridad"]], hide_index=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_history_tab() -> None:
    st.markdown("### Historial, reportes y evidencias")
    if st.button("Sincronizar historial con Google Drive", key="sync_history"):
        sync_master_tables_from_drive(force=True)
    paths = get_storage_paths()
    audits_df = safe_read_csv(paths["audits"] / "audits_summary.csv")
    if audits_df.empty:
        st.info("Todavía no hay auditorías guardadas.")
        return
    audits_df = audits_df.sort_values("timestamp_human", ascending=False)
    labels = [f"{row.audit_id} · {row.timestamp_human} · {row.building}" for row in audits_df.itertuples()]
    selected_label = st.selectbox("Selecciona una auditoría", labels, key="hist_select")
    selected = audits_df.iloc[labels.index(selected_label)]
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Score", f"{selected['score_total']}/100")
    with c2: st.metric("Hallazgos", int(selected["issue_count"]))
    with c3: st.metric("Casos actualizados", int(selected.get("cases_updated", 0)))
    st.write(f"**Edificio:** {selected['building']}")
    st.write(f"**Auditor:** {selected['auditor']}")
    st.write(f"**Fecha:** {selected['timestamp_human']}")
    if selected.get("report_drive_link"): st.link_button("Abrir reporte en Drive", selected["report_drive_link"])
    if selected.get("json_drive_link"): st.link_button("Abrir JSON en Drive", selected["json_drive_link"])
    items_df = safe_read_csv(paths["audits"] / "audit_items.csv")
    if not items_df.empty:
        subset = items_df[items_df["audit_id"] == selected["audit_id"]]
        st.dataframe(subset[["space","question","status","action","evidence_count"]], hide_index=True, use_container_width=True)

def render_cases_tab() -> None:
    st.markdown("### Casos y seguimiento")
    if st.button("Sincronizar casos con Google Drive", key="sync_cases"):
        sync_master_tables_from_drive(force=True)
    paths = get_storage_paths()
    cases_df = safe_read_csv(paths["tracking"] / "cases_followup.csv")
    events_df = safe_read_csv(paths["tracking"] / "case_events.csv")
    if cases_df.empty:
        st.info("Todavía no hay casos creados.")
        return
    cases_df = cases_df.sort_values(["case_status", "last_review_at"], ascending=[True, False])
    labels = [f"{row.case_id} · {row.space} · {row.question}" for row in cases_df.itertuples()]
    selected_label = st.selectbox("Selecciona un caso", labels, key="case_select")
    selected_case_id = cases_df.iloc[labels.index(selected_label)]["case_id"]
    case_row = cases_df[cases_df["case_id"] == selected_case_id].iloc[0]
    st.write(f"**Estado:** {case_row['case_status']} · **Prioridad:** {case_row['priority']}")
    st.write(f"**Última auditoría:** {case_row['latest_audit_id']}")
    responsible = st.text_input("Responsable", value=str(case_row.get("responsible", "")), key=f"resp_{selected_case_id}")
    priority = st.selectbox("Prioridad", PRIORITY_OPTIONS, index=PRIORITY_OPTIONS.index(case_row["priority"]) if case_row["priority"] in PRIORITY_OPTIONS else 1, key=f"prio_{selected_case_id}")
    case_status = st.selectbox("Estado del caso", CASE_STATUS_OPTIONS, index=CASE_STATUS_OPTIONS.index(case_row["case_status"]) if case_row["case_status"] in CASE_STATUS_OPTIONS else 0, key=f"status_case_{selected_case_id}")
    due_date_raw = case_row.get("due_date", "")
    due_date_value = pd.to_datetime(due_date_raw).date() if isinstance(due_date_raw, str) and due_date_raw else None
    due_date_value = st.date_input("Fecha compromiso", value=due_date_value, key=f"due_{selected_case_id}")
    followup_note = st.text_area("Nota de seguimiento", key=f"note_{selected_case_id}", height=100)
    if st.button("Guardar seguimiento del caso", type="primary"):
        updates = {"responsible": responsible, "priority": priority, "case_status": case_status, "due_date": due_date_value.isoformat() if due_date_value else ""}
        note = followup_note.strip() or f"Caso actualizado a estado {case_status}."
        update_case_record(selected_case_id, updates, note)
        st.success("Seguimiento guardado.")
        st.rerun()
    if not events_df.empty:
        case_events = events_df[events_df["case_id"] == selected_case_id].sort_values("event_at", ascending=False)
        if not case_events.empty:
            st.markdown("#### Timeline")
            st.dataframe(case_events[["event_at", "event_type", "note", "audit_id"]], hide_index=True, use_container_width=True)

def render_audit_tab() -> None:
    render_storage_config()
    render_meta()
    render_dashboard()
    render_space_selector()
    render_current_space()
    render_summary()
    persist_visible_section_uploads_to_draft()
    save_draft_state()

def main() -> None:
    inject_css()
    init_state()
    handle_google_oauth_callback()
    header()
    if st.session_state.get("drive_init_error"):
        st.warning(f"Google Drive no pudo inicializarse: {st.session_state['drive_init_error']}")
    tab1, tab2, tab3 = st.tabs(["Auditoría", "Historial y evidencias", "Casos y seguimiento"])
    with tab1:
        render_audit_tab()
    with tab2:
        render_history_tab()
    with tab3:
        render_cases_tab()

if __name__ == "__main__":
    main()
