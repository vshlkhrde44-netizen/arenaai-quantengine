"""
Antigravity QuantEngine - Secure Credential Vault & Operator Authorization
Enforces AES-256-GCM encryption with OS-level DPAPI protection on Windows
and strictly protected machine-bound keys.
Reports explicit VAULT_ERROR upon decryption failure/tampering (Section 40, 41).
Provides operator session authorization tokens (Section 44).
"""

import base64
import json
import os
import sys
import secrets
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from core.logging import get_logger

logger = get_logger("security.vault")

VAULT_SALT_FILE = Path("data/vault/vault.salt")
VAULT_KEY_FILE = Path("data/vault/vault.master")
VAULT_DATA_FILE = Path("data/vault/credentials.enc")
OPERATOR_TOKEN_FILE = Path("data/vault/operator.token")


class VaultError(Exception):
    """Raised when the credential vault is corrupted, tampered, or cannot be decrypted."""
    pass


class OperatorAuthManager:
    """Manages local operator session authorization tokens per Section 44."""

    _token: Optional[str] = None

    @classmethod
    def get_or_create_token(cls) -> str:
        if cls._token:
            return cls._token
        OPERATOR_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        if OPERATOR_TOKEN_FILE.exists():
            try:
                cls._token = OPERATOR_TOKEN_FILE.read_text(encoding="utf-8").strip()
                if len(cls._token) >= 32:
                    return cls._token
            except Exception:
                pass
        # Generate fresh secure 256-bit operator token
        cls._token = secrets.token_hex(32)
        try:
            OPERATOR_TOKEN_FILE.write_text(cls._token, encoding="utf-8")
            try:
                os.chmod(OPERATOR_TOKEN_FILE, 0o600)
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Could not persist operator token file: {e}")
        return cls._token

    @classmethod
    def validate_token(cls, token: Optional[str]) -> bool:
        if not token:
            return False
        expected = cls.get_or_create_token()
        return secrets.compare_digest(token.strip(), expected.strip())


class WindowsDPAPI:
    """Windows Data Protection API (DPAPI) integration via ctypes."""

    @staticmethod
    def is_windows() -> bool:
        return sys.platform == "win32"

    @classmethod
    def protect(cls, data: bytes) -> bytes:
        if not cls.is_windows():
            return data
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        pDataIn = DATA_BLOB()
        pDataIn.cbData = len(data)
        pDataIn.pbData = ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_byte))

        pDataOut = DATA_BLOB()
        CryptProtectData = ctypes.windll.crypt32.CryptProtectData
        CryptProtectData.argtypes = [
            ctypes.POINTER(DATA_BLOB), ctypes.c_wchar_p, ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)
        ]
        CryptProtectData.restype = wintypes.BOOL

        if not CryptProtectData(ctypes.byref(pDataIn), "QuantEngineVault", None, None, None, 0, ctypes.byref(pDataOut)):
            raise VaultError("Windows DPAPI CryptProtectData call failed.")

        try:
            buf = ctypes.create_string_buffer(pDataOut.cbData)
            ctypes.memmove(buf, pDataOut.pbData, pDataOut.cbData)
            return buf.raw
        finally:
            ctypes.windll.kernel32.LocalFree(pDataOut.pbData)

    @classmethod
    def unprotect(cls, cipher_bytes: bytes) -> bytes:
        if not cls.is_windows():
            return cipher_bytes
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        pDataIn = DATA_BLOB()
        pDataIn.cbData = len(cipher_bytes)
        pDataIn.pbData = ctypes.cast(ctypes.create_string_buffer(cipher_bytes, len(cipher_bytes)), ctypes.POINTER(ctypes.c_byte))

        pDataOut = DATA_BLOB()
        CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
        CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB), ctypes.POINTER(ctypes.c_wchar_p), ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)
        ]
        CryptUnprotectData.restype = wintypes.BOOL

        if not CryptUnprotectData(ctypes.byref(pDataIn), None, None, None, None, 0, ctypes.byref(pDataOut)):
            raise VaultError("Windows DPAPI CryptUnprotectData failed: invalid user keychain or corrupted DPAPI blob.")

        try:
            buf = ctypes.create_string_buffer(pDataOut.cbData)
            ctypes.memmove(buf, pDataOut.pbData, pDataOut.cbData)
            return buf.raw
        finally:
            ctypes.windll.kernel32.LocalFree(pDataOut.pbData)


class CredentialVault:
    """
    Secure encrypted storage for exchange API credentials.
    Enforces OS-level DPAPI protection and hard fail on tampering (P0-16, P0-17).
    """

    def __init__(
        self,
        data_file: Path = VAULT_DATA_FILE,
        salt_file: Path = VAULT_SALT_FILE,
        key_file: Path = VAULT_KEY_FILE
    ):
        self.data_file = Path(data_file)
        self.salt_file = Path(salt_file)
        self.key_file = Path(key_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self._vault_error_state: Optional[str] = None
        self._ensure_root_entropy()

    def _ensure_root_entropy(self) -> None:
        """Create or load the DPAPI/OS protected master key and salt."""
        if not self.salt_file.exists():
            salt = os.urandom(32)
            self.salt_file.write_bytes(salt)
            try:
                os.chmod(self.salt_file, 0o600)
            except Exception:
                pass

        if not self.key_file.exists():
            raw_master = os.urandom(32)
            # Protect using Windows DPAPI if on Windows
            protected_blob = WindowsDPAPI.protect(raw_master)
            self.key_file.write_bytes(protected_blob)
            try:
                os.chmod(self.key_file, 0o600)
            except Exception:
                pass

    def _derive_key(self) -> bytes:
        if not self.salt_file.exists() or not self.key_file.exists():
            self._ensure_root_entropy()

        salt = self.salt_file.read_bytes()
        protected_master = self.key_file.read_bytes()
        try:
            unprotected_master = WindowsDPAPI.unprotect(protected_master)
        except Exception as e:
            self._vault_error_state = "VAULT_ERROR: DPAPI_UNPROTECT_FAILED"
            raise VaultError(f"VAULT_ERROR: Unable to unprotect master root key: {e}")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200_000,
        )
        return kdf.derive(unprotected_master)

    def _encrypt(self, plaintext: str) -> Dict[str, str]:
        key = self._derive_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return {
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8")
        }

    def _decrypt(self, payload: Dict[str, str]) -> str:
        key = self._derive_key()
        aesgcm = AESGCM(key)
        try:
            nonce = base64.b64decode(payload["nonce"])
            ciphertext = base64.b64decode(payload["ciphertext"])
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode("utf-8")
        except Exception as e:
            self._vault_error_state = "VAULT_ERROR: DECRYPTION_FAILED_OR_TAMPERED"
            raise VaultError(f"VAULT_ERROR: Tampered or corrupted credential payload: {e}")

    def _load_all(self) -> Dict[str, Any]:
        """
        Load decrypted credentials.
        CRITICAL (P0-17): Never silently return {} on failure.
        Raise VaultError and report VAULT_ERROR.
        """
        if not self.data_file.exists():
            return {}
        try:
            raw = self.data_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            decrypted_str = self._decrypt(data)
            return json.loads(decrypted_str)
        except VaultError:
            raise
        except Exception as e:
            self._vault_error_state = f"VAULT_ERROR: {e}"
            logger.critical(f"FATAL VAULT INTEGRITY ERROR: {e}", exc_info=True)
            raise VaultError(f"VAULT_ERROR: Failed to open vault: {e}")

    def _save_all(self, vault_data: Dict[str, Any]) -> None:
        serialized = json.dumps(vault_data)
        encrypted_payload = self._encrypt(serialized)
        self.data_file.write_text(json.dumps(encrypted_payload), encoding="utf-8")
        try:
            os.chmod(self.data_file, 0o600)
        except Exception:
            pass

    def store_credentials(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        is_paper: bool = True
    ) -> None:
        """Store encrypted exchange paper credentials. Enforces paper-only."""
        if not is_paper:
            raise ValueError("FATAL SAFETY ERROR: Only paper/sandbox exchange credentials may be stored.")

        vault_data = self._load_all()
        vault_data[exchange.lower()] = {
            "api_key": api_key,
            "api_secret": api_secret,
            "passphrase": passphrase or "",
            "is_paper": is_paper,
            "updated_at": os.times()[4]
        }
        self._save_all(vault_data)
        logger.info(f"Stored encrypted paper credentials for venue: {exchange}")

    def get_credentials(self, exchange: str) -> Optional[Dict[str, str]]:
        """Retrieve decrypted credentials. Fails closed with VaultError on tampering."""
        vault_data = self._load_all()
        return vault_data.get(exchange.lower())

    def remove_credentials(self, exchange: str) -> bool:
        vault_data = self._load_all()
        if exchange.lower() in vault_data:
            del vault_data[exchange.lower()]
            self._save_all(vault_data)
            logger.info(f"Purged credentials for venue: {exchange}")
            return True
        return False

    def get_vault_health(self) -> Dict[str, Any]:
        """Expose vault health status including explicit VAULT_ERROR if corrupted."""
        if self._vault_error_state:
            return {"status": "VAULT_ERROR", "error": self._vault_error_state}
        try:
            self._load_all()
            return {"status": "HEALTHY", "error": None}
        except Exception as e:
            return {"status": "VAULT_ERROR", "error": str(e)}

    def get_status(self, exchange: str) -> Dict[str, Any]:
        """Safe UI-ready status with masked keys and zero secrets."""
        try:
            creds = self.get_credentials(exchange)
            if not creds:
                return {"configured": False, "exchange": exchange, "is_paper": True, "status": "HEALTHY"}
            raw_key = creds.get("api_key", "")
            masked = f"{raw_key[:4]}****{raw_key[-4:]}" if len(raw_key) > 8 else "****"
            return {
                "configured": True,
                "exchange": exchange,
                "masked_key": masked,
                "has_secret": bool(creds.get("api_secret")),
                "has_passphrase": bool(creds.get("passphrase")),
                "is_paper": creds.get("is_paper", True),
                "status": "HEALTHY"
            }
        except Exception as e:
            return {"configured": False, "exchange": exchange, "status": "VAULT_ERROR", "error": str(e)}

    def list_all_status(self) -> Dict[str, Any]:
        try:
            vault_data = self._load_all()
            result = {}
            for exchange, creds in vault_data.items():
                raw_key = creds.get("api_key", "")
                masked = f"{raw_key[:4]}****{raw_key[-4:]}" if len(raw_key) > 8 else "****"
                result[exchange] = {
                    "configured": True,
                    "exchange": exchange,
                    "masked_key": masked,
                    "has_secret": bool(creds.get("api_secret")),
                    "has_passphrase": bool(creds.get("passphrase")),
                    "is_paper": creds.get("is_paper", True)
                }
            return result
        except Exception as e:
            return {"error": "VAULT_ERROR", "detail": str(e)}


_VAULT_INSTANCE: Optional[CredentialVault] = None


def get_credential_vault() -> CredentialVault:
    global _VAULT_INSTANCE
    if _VAULT_INSTANCE is None:
        _VAULT_INSTANCE = CredentialVault()
    return _VAULT_INSTANCE
