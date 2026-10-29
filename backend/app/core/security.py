import base64
import hashlib
import hmac
import secrets
import string
import unicodedata

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings, get_settings


INVITATION_ALPHABET = string.ascii_uppercase + string.digits


def normalize_name(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def clean_display_name(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def generate_invitation_code() -> str:
    return "".join(secrets.choice(INVITATION_ALPHABET) for _ in range(9))


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def _secret(settings: Settings, field_name: str) -> bytes:
    value = getattr(settings, field_name)
    if len(value) < 32:
        raise RuntimeError(f"{field_name.upper()} must contain at least 32 characters")
    return value.encode("utf-8")


def digest_value(value: str, purpose: str, settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    key = _secret(active_settings, "auth_hmac_key")
    payload = f"{purpose}:{value}".encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def invitation_digest(code: str, settings: Settings | None = None) -> str:
    return digest_value(code.strip().upper(), "invitation", settings)


def session_digest(token: str, settings: Settings | None = None) -> str:
    return digest_value(token, "session", settings)


def csrf_token(token: str, settings: Settings | None = None) -> str:
    return digest_value(token, "csrf", settings)


def _fernet(settings: Settings) -> Fernet:
    secret = _secret(settings, "invitation_encryption_key")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_invitation(code: str, settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    return _fernet(active_settings).encrypt(code.encode("utf-8")).decode("ascii")


def decrypt_invitation(ciphertext: str, settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    try:
        return _fernet(active_settings).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("invitation ciphertext cannot be decrypted") from exc


def shared_password_matches(candidate: str, settings: Settings | None = None) -> bool:
    active_settings = settings or get_settings()
    configured = active_settings.shared_password
    if not configured:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), configured.encode("utf-8"))
