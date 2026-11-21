
from pathlib import Path
import base64

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE = Path(__file__).resolve().parent


def gmail_service():
    creds = None

    token_path = BASE / 'token.json'
    client_path = BASE / 'credentials.json'

    if not client_path.exists():
        raise FileNotFoundError(
            'No se encontró credentials.json en la carpeta de la aplicación.'
        )

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            str(token_path), SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_path), SCOPES
            )

            creds = flow.run_local_server(
                host='127.0.0.1',
                port=0,
                open_browser=True,
                authorization_prompt_message=(
                    'Autoriza DADDS Monitor en el navegador que se abrirá.'
                ),
                success_message=(
                    'Autorización completada. Puedes regresar a DADDS Monitor.'
                ),
                timeout_seconds=120,
            )

        token_path.write_text(creds.to_json(), encoding='utf-8')

    return build('gmail', 'v1', credentials=creds)


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
                    attachment = service.users().messages().attachments().get(
                        userId='me',
                        messageId=msg_id,
                        id=attachment_id
                    ).execute()

                    data = attachment.get('data')

                if data:
                    file_bytes = base64.urlsafe_b64decode(
                        data.encode('UTF-8')
                    )

                    # Devuelve únicamente dos valores.
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

        found = inspect_parts(
            msg['id'],
            detail.get('payload', {}).get('parts')
        )

        if found:
            return found

    return None
