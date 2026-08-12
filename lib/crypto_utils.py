"""
At-rest encryption helpers.

Nothing Aegis persists today is a secret: AWS auth flows entirely through
boto3's own credential chain (see README's "AWS Cloud Configuration"
section), and `temp/last_config.json` / IDS rule files only hold operational
settings (IPs, thresholds). This module exists so that when a future
integration needs to persist something sensitive locally (e.g. a webhook
token for an alerting integration, an API key for a third-party SIEM), there
is a ready, tested place to encrypt it rather than writing it to config in
plaintext.

Usage:
    from lib import crypto_utils

    key = crypto_utils.load_or_create_key()
    token = crypto_utils.encrypt_string("super-secret-value", key)
    ...
    plaintext = crypto_utils.decrypt_string(token, key)
"""
import os
from cryptography.fernet import Fernet

DEFAULT_KEY_PATH = os.path.join("temp", "aegis.key")


def generate_key() -> bytes:
    """Generate a new Fernet symmetric key."""
    return Fernet.generate_key()


def load_or_create_key(key_path: str = DEFAULT_KEY_PATH) -> bytes:
    """
    Load a persisted local key, generating and saving one on first use.
    The key file is created with owner-only permissions (0600) since anyone
    who can read it can decrypt everything encrypted with it.
    """
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read().strip()

    key = generate_key()
    key_dir = os.path.dirname(key_path)
    if key_dir:
        os.makedirs(key_dir, exist_ok=True)
    with open(key_path, "wb") as f:
        f.write(key)
    os.chmod(key_path, 0o600)
    return key


def encrypt_string(plaintext: str, key: bytes) -> str:
    """Encrypt a string, returning a URL-safe base64 token safe to store in JSON/YAML."""
    return Fernet(key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_string(token: str, key: bytes) -> str:
    """
    Decrypt a token produced by encrypt_string.
    Raises cryptography.fernet.InvalidToken if the key/token don't match.
    """
    return Fernet(key).decrypt(token.encode("utf-8")).decode("utf-8")
