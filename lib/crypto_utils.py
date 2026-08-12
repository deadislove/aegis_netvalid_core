"""
At-rest encryption helpers (Fernet). Not wired into anything yet - scaffolding
for future secrets (e.g. a webhook token) that need to be persisted locally.
"""
import os
from cryptography.fernet import Fernet

DEFAULT_KEY_PATH = os.path.join("temp", "aegis.key")


def generate_key() -> bytes:
    """Generate a new Fernet symmetric key."""
    return Fernet.generate_key()


def load_or_create_key(key_path: str = DEFAULT_KEY_PATH) -> bytes:
    """Load a persisted local key, generating one (mode 0600) on first use."""
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
