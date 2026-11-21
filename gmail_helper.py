
import base64
import streamlit as st

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_oauth_config():
    return {
        "web": {
            "client_id": st.secrets["google"]["client_id"],
            "client_secret": st.secrets["google"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                st.secrets["google"]["redirect_uri"]
            ],
        }
    }


def create_flow():
    flow = Flow.from_client_config(
        get_oauth_config(),
        scopes=SCOPES
    )

    flow.redirect_uri = st.secrets["google"]["redirect_uri"]

    return flow


def get_authorization_url():
    flow = create_flow()

    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )

    st.session_state["oauth_state"] = state

    return auth_url


def exchange_code(code, state):
    flow = create_flow()

    flow.fetch_token(
        code=code
    )

    creds = flow.credentials

    st.session_state["gmail_credentials"] = creds.to_json()

    return creds


def get_credentials():
    token_json = st.session_state.get("gmail_credentials")

    if not token_json:
        return None

    creds = Credentials.from_authorized_user_info(
        eval(token_json),
        SCOPES
    )

    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request

        creds.refresh(Request())

        st.session_state["gmail_credentials"] = creds.to_json()

    return creds


def gmail_service():
    creds = get_credentials()

    if not creds:
        return None

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


def find_latest_xlsx(query):
    service = gmail_service()

    if not service:
        raise RuntimeError(
            "Debes autorizar tu cuenta de Gmail primero."
        )

    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=15
    ).execute()

    messages = result.get("messages", [])

    if not messages:
        return None

    def inspect_parts(msg_id, parts):

        for part in parts or []:

            filename = part.get("filename", "")

            if filename.lower().endswith((".xlsx", ".xls")):

                body = part.get("body", {})
                data = body.get("data")
                attachment_id = body.get("attachmentId")

                if attachment_id:
                    attachment = (
                        service.users()
                        .messages()
                        .attachments()
                        .get(
                            userId="me",
                            messageId=msg_id,
                            id=attachment_id
                        )
                        .execute()
                    )

                    data = attachment.get("data")

                if data:
                    file_bytes = base64.urlsafe_b64decode(
                        data.encode("UTF-8")
                    )

                    return filename, file_bytes

            found = inspect_parts(
                msg_id,
                part.get("parts")
            )

            if found:
                return found

        return None

    for msg in messages:

        detail = service.users().messages().get(
            userId="me",
            id=msg["id"]
        ).execute()

        payload = detail.get("payload", {})

        parts = payload.get("parts")

        if not parts:
            parts = [payload]

        found = inspect_parts(
            msg["id"],
            parts
        )

        if found:
            return found

    return None

