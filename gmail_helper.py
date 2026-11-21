import base64
import json
from email.utils import parsedate_to_datetime

import streamlit as st
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_KEY = "gmail_credentials_json"
STATE_KEY = "gmail_oauth_state"


def _google_config():
    """Lee la configuración desde Streamlit Secrets."""
    try:
        cfg = st.secrets["google"]
        client_id = str(cfg["client_id"]).strip()
        client_secret = str(cfg["client_secret"]).strip()
        redirect_uri = str(cfg["redirect_uri"]).strip()
    except Exception as exc:
        raise RuntimeError(
            "Falta configurar [google] en Streamlit Secrets. "
            "Se requieren client_id, client_secret y redirect_uri."
        ) from exc

    if not all([client_id, client_secret, redirect_uri]):
        raise RuntimeError(
            "client_id, client_secret y redirect_uri no pueden estar vacíos."
        )

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }, redirect_uri


def _new_flow(state=None):
    client_config, redirect_uri = _google_config()
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
    )
    flow.redirect_uri = redirect_uri
    return flow


def get_authorization_url():
    """Genera URL OAuth y guarda el state en la sesión actual."""
    flow = _new_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    st.session_state[STATE_KEY] = state
    return auth_url


def exchange_code(code, returned_state):
    """Valida state y canjea el código en la sesión del usuario."""
    expected_state = st.session_state.get(STATE_KEY)
    if not expected_state or not returned_state or returned_state != expected_state:
        raise RuntimeError(
            "La validación de seguridad OAuth falló o la sesión expiró. "
            "Vuelve a iniciar la autorización de Gmail."
        )

    flow = _new_flow(state=expected_state)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise RuntimeError(
            "Google no pudo completar la autorización. Verifica el redirect URI "
            "y las credenciales OAuth configuradas."
        ) from exc

    credentials = flow.credentials
    st.session_state[TOKEN_KEY] = credentials.to_json()
    st.session_state.pop(STATE_KEY, None)
    return True


def is_authorized():
    return bool(st.session_state.get(TOKEN_KEY))


def disconnect_gmail():
    st.session_state.pop(TOKEN_KEY, None)
    st.session_state.pop(STATE_KEY, None)


def _get_credentials():
    token_json = st.session_state.get(TOKEN_KEY)
    if not token_json:
        raise RuntimeError("Primero debes autorizar tu cuenta de Gmail.")

    creds = Credentials.from_authorized_user_info(
        json.loads(token_json),
        SCOPES,
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            st.session_state[TOKEN_KEY] = creds.to_json()
        except Exception as exc:
            disconnect_gmail()
            raise RuntimeError(
                "La autorización de Gmail venció o fue revocada. "
                "Autoriza nuevamente tu cuenta."
            ) from exc

    if not creds.valid:
        disconnect_gmail()
        raise RuntimeError("La autorización de Gmail no es válida. Autoriza nuevamente.")

    return creds


def gmail_service():
    return build(
        "gmail",
        "v1",
        credentials=_get_credentials(),
        cache_discovery=False,
    )


def _decode_attachment(service, message_id, part):
    body = part.get("body", {}) or {}
    data = body.get("data")
    attachment_id = body.get("attachmentId")

    if attachment_id:
        attachment = service.users().messages().attachments().get(
            userId="me",
            messageId=message_id,
            id=attachment_id,
        ).execute()
        data = attachment.get("data")

    if not data:
        return None

    return base64.urlsafe_b64decode(data.encode("ascii"))


def _find_excel_part(service, message_id, parts):
    for part in parts or []:
        filename = (part.get("filename") or "").strip()
        mime_type = (part.get("mimeType") or "").lower()

        if filename.lower().endswith((".xlsx", ".xls")):
            file_bytes = _decode_attachment(service, message_id, part)
            if file_bytes:
                return filename, file_bytes

        nested = _find_excel_part(
            service,
            message_id,
            part.get("parts", []),
        )
        if nested:
            return nested

    return None


def find_latest_xlsx(query="has:attachment filename:xlsx"):
    """
    Busca en el Gmail autorizado en ESTA sesión el Excel adjunto más reciente.
    Devuelve (nombre_archivo, bytes) o None.
    """
    service = gmail_service()

    response = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=25,
    ).execute()

    messages = response.get("messages", [])
    if not messages:
        return None

    candidates = []
    for message in messages:
        detail = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full",
        ).execute()

        internal_date = int(detail.get("internalDate", 0))
        candidates.append((internal_date, message["id"], detail))

    candidates.sort(key=lambda item: item[0], reverse=True)

    for _, message_id, detail in candidates:
        payload = detail.get("payload", {}) or {}
        found = _find_excel_part(
            service,
            message_id,
            payload.get("parts", []),
        )
        if found:
            return found

    return None

