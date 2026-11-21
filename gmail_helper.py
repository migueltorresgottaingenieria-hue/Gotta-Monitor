
from pathlib import Path
import base64
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE = Path(__file__).resolve().parent


# Carpeta de datos del usuario en Windows
APPDATA = Path(os.getenv("APPDATA", str(Path.home())))
TOKEN_DIR = APPDATA / "GottaMonitor"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = TOKEN_DIR / "token.json"
CLIENT_PATH = BASE / "credentials.json"


def gmail_service():
    creds = None

    if not CLIENT_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró credentials.json en: {CLIENT_PATH}"
        )

    # Cargar token existente
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(TOKEN_PATH), SCOPES
            )
        except Exception:
            creds = None

    # Renovar o volver a autorizar
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_PATH), SCOPES
            )

            creds = flow.run_local_server(
                host='127.0.0.1',
                port=0,
                open_browser=True,
                authorization_prompt_message=(
                    'Autoriza Gotta Monitor en el navegador.'
                ),
                success_message=(
                    'Autorización completada. '
                    'Puedes regresar a Gotta Monitor.'
                ),
                timeout_seconds=120,
            )

        # Guardar token en AppData
        TOKEN_PATH.write_text(
            creds.to_json(),
            encoding='utf-8'
        )

    return build(
        'gmail',
        'v1',
        credentials=creds
    )


def find_latest_xlsx(query):
    service = gmail_service()

    result = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=15
    ).execute()

    messages = result.get('messages', [])

    if not messages:
        return None

    def inspect_parts(msg_id, parts):

        for part in parts or []:

            filename = part.get('filename', '')

            if filename.lower().endswith(('.xlsx', '.xls')):

                body = part.get('body', {})
                data = body.get('data')
                attachment_id = body.get('attachmentId')

                if attachment_id:
                    attachment = (
                        service.users()
                        .messages()
                        .attachments()
                        .get(
                            userId='me',
                            messageId=msg_id,
                            id=attachment_id
                        )
                        .execute()
                    )

                    data = attachment.get('data')

                if data:
                    file_bytes = base64.urlsafe_b64decode(
                        data.encode('UTF-8')
                    )

                    return filename, file_bytes

            found = inspect_parts(
                msg_id,
                part.get('parts')
            )

            if found:
                return found

        return None

    for msg in messages:

        detail = service.users().messages().get(
            userId='me',
            id=msg['id']
        ).execute()

        payload = detail.get('payload', {})

        # Permite revisar también el payload principal
        parts = payload.get('parts')

        if not parts:
            parts = [payload]

        found = inspect_parts(
            msg['id'],
            parts
        )

        if found:
            return found

    return None


