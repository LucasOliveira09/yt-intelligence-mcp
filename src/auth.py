import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config import ACCOUNTS_FILE, DATA_DIR

logger = logging.getLogger("yt_intelligence.auth")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def load_all_accounts() -> Dict[str, Any]:
    if not ACCOUNTS_FILE.exists():
        return {}
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading accounts: {e}")
        return {}


def save_account_data(alias: str, data: Dict[str, Any]) -> None:
    accounts = load_all_accounts()
    accounts[alias] = data
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)
    ACCOUNTS_FILE.chmod(0o600)


def remove_account(alias: str) -> bool:
    accounts = load_all_accounts()
    if alias in accounts:
        del accounts[alias]
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
        return True
    return False


def get_credentials(alias: str) -> Optional[Credentials]:
    accounts = load_all_accounts()
    acc = accounts.get(alias)
    if not acc:
        return None

    creds_dict = acc.get("credentials")
    if not creds_dict:
        return None

    creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            acc["credentials"] = json.loads(creds.to_json())
            save_account_data(alias, acc)
        except Exception as e:
            logger.error(f"Failed to refresh token for {alias}: {e}")
            return None

    return creds


def _create_flow(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    client_secrets_path: Optional[Path] = None,
) -> InstalledAppFlow:
    """Creates an InstalledAppFlow with zero file requirements if credentials are provided."""
    secret_file = client_secrets_path or (DATA_DIR / "client_secret.json")
    if secret_file.exists():
        return InstalledAppFlow.from_client_secrets_file(
            str(secret_file),
            scopes=SCOPES,
            redirect_uri="http://localhost:8080/",
        )

    cid = client_id or os.getenv("GOOGLE_CLIENT_ID")
    csecret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")

    if not cid or not csecret:
        raise ValueError(
            "OAuth requer Client ID e Client Secret. "
            "Passe via comando ou defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no ambiente."
        )

    client_config = {
        "installed": {
            "client_id": cid,
            "client_secret": csecret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/"],
        }
    }
    return InstalledAppFlow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri="http://localhost:8080/",
    )


def start_auth_flow(
    alias: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    client_secrets_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Initiates Google OAuth flow directly without requiring any file downloads.
    """
    try:
        flow = _create_flow(
            client_id=client_id,
            client_secret=client_secret,
            client_secrets_path=client_secrets_path,
        )
    except Exception as e:
        return {"error": "CONFIG_ERROR", "message": str(e)}

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    return {
        "status": "awaiting_code",
        "auth_url": auth_url,
        "redirect_uri": "http://localhost:8080/",
        "instructions": (
            "1. Abra a URL acima no navegador do celular ou PC.\n"
            "2. Faça login com a conta do seu canal do YouTube e autorize.\n"
            "3. O navegador redirecionará para http://localhost:8080/?code=...\n"
            "4. Copie a URL da barra de endereços (ou apenas o código) e cole aqui."
        ),
    }


def finish_auth_flow(
    alias: str,
    raw_response_or_code: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    client_secrets_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Completes the OAuth flow by exchanging code for refresh tokens.
    """
    try:
        flow = _create_flow(
            client_id=client_id,
            client_secret=client_secret,
            client_secrets_path=client_secrets_path,
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

    code = raw_response_or_code.strip()
    if "code=" in code:
        parsed = urlparse(code)
        params = parse_qs(parsed.query)
        code = params.get("code", [code])[0]

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        creds_json = json.loads(creds.to_json())

        from googleapiclient.discovery import build
        service = build("youtube", "v3", credentials=creds)
        res = service.channels().list(part="snippet", mine=True).execute()
        items = res.get("items", [])
        channel_title = items[0]["snippet"]["title"] if items else alias
        channel_id = items[0]["id"] if items else None

        account_info = {
            "alias": alias,
            "channel_title": channel_title,
            "channel_id": channel_id,
            "credentials": creds_json,
        }
        save_account_data(alias, account_info)

        return {
            "status": "success",
            "alias": alias,
            "channel_title": channel_title,
            "channel_id": channel_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Falha na troca de token: {e}",
        }
