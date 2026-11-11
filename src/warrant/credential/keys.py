"""Ed25519 key loading and local key-pair generation for the prototype."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class KeyConfigurationError(ValueError):
    """Raised for an unusable key or key identifier without exposing key material."""


def validate_key_id(key_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", key_id) is None:
        raise KeyConfigurationError("key id must be 1–64 URL-safe ASCII characters")
    return key_id


@dataclass(frozen=True, slots=True)
class SigningKey:
    key_id: str
    private_key: Ed25519PrivateKey

    def __post_init__(self) -> None:
        validate_key_id(self.key_id)


@dataclass(frozen=True, slots=True)
class VerificationKey:
    key_id: str
    public_key: Ed25519PublicKey

    def __post_init__(self) -> None:
        validate_key_id(self.key_id)


class KeyRing:
    """Verification key set indexed by kid; retain old public keys during rotation."""

    def __init__(self, keys: tuple[VerificationKey, ...]) -> None:
        indexed = {key.key_id: key.public_key for key in keys}
        if len(indexed) != len(keys):
            raise KeyConfigurationError("duplicate verification key id")
        self._keys = indexed

    def get(self, key_id: str) -> Ed25519PublicKey | None:
        return self._keys.get(key_id)


def load_signing_key(path: Path, passphrase: str, key_id: str) -> SigningKey:
    if not passphrase:
        raise KeyConfigurationError("a non-empty signing-key passphrase is required")
    try:
        key = serialization.load_pem_private_key(
            path.read_bytes(), password=passphrase.encode("utf-8")
        )
    except (OSError, ValueError, TypeError) as exc:
        raise KeyConfigurationError("unable to load the configured signing key") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise KeyConfigurationError("configured signing key is not Ed25519")
    return SigningKey(key_id, key)


def load_verification_key(path: Path, key_id: str) -> VerificationKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise KeyConfigurationError("unable to load the configured verification key") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise KeyConfigurationError("configured verification key is not Ed25519")
    return VerificationKey(key_id, key)


def generate_key_pair(private_path: Path, public_path: Path, passphrase: str) -> None:
    """Create encrypted PKCS#8 private PEM and public PEM; refuse to overwrite either file."""
    if len(passphrase) < 12:
        raise KeyConfigurationError("passphrase must contain at least 12 characters")
    if private_path.resolve() == public_path.resolve():
        raise KeyConfigurationError("private and public key paths must differ")
    if private_path.exists() or public_path.exists():
        raise KeyConfigurationError("refusing to overwrite an existing key output")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase.encode("utf-8")),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # Exclusive creation prevents accidental rotation/overwrite of an in-use key.
    try:
        with public_path.open("xb") as stream:
            stream.write(public_bytes)
        # Create the private file last: a partial failure can leave a public orphan, not a secret.
        if os.name != "nt":
            private_fd = os.open(
                private_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(private_fd, "wb") as stream:
                stream.write(private_bytes)
        else:
            # Windows uses the destination directory's inherited ACL; Python's POSIX mode
            # argument does not provide an equivalent per-file DACL guarantee.
            with private_path.open("xb") as stream:
                stream.write(private_bytes)
    except OSError:
        # Never delete a file here: it may predate this operation or be another process's key.
        raise KeyConfigurationError("key output already exists or cannot be created") from None
    if os.name != "nt":
        # chmod after writing leaves a window where the secret inherits a permissive umask.
        # Reapply defensively for filesystems that do not honor mode bits on creation.
        private_path.chmod(0o600)
