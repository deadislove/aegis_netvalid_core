import os
import pytest
from cryptography.fernet import InvalidToken
from lib import crypto_utils


def test_encrypt_decrypt_roundtrip():
    key = crypto_utils.generate_key()
    token = crypto_utils.encrypt_string("super-secret-value", key)
    assert token != "super-secret-value"
    assert crypto_utils.decrypt_string(token, key) == "super-secret-value"


def test_decrypt_with_wrong_key_fails():
    key_a = crypto_utils.generate_key()
    key_b = crypto_utils.generate_key()
    token = crypto_utils.encrypt_string("classified", key_a)
    with pytest.raises(InvalidToken):
        crypto_utils.decrypt_string(token, key_b)


def test_load_or_create_key_persists_and_reuses(tmp_path):
    key_path = str(tmp_path / "aegis.key")
    assert not os.path.exists(key_path)

    key1 = crypto_utils.load_or_create_key(key_path)
    assert os.path.exists(key_path)

    key2 = crypto_utils.load_or_create_key(key_path)
    assert key1 == key2


def test_load_or_create_key_sets_owner_only_permissions(tmp_path):
    key_path = str(tmp_path / "nested" / "aegis.key")
    crypto_utils.load_or_create_key(key_path)

    mode = os.stat(key_path).st_mode & 0o777
    assert mode == 0o600
