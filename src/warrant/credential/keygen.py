"""Interactive local Ed25519 key-pair generation without printing secret material."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from warrant.credential.keys import generate_key_pair, validate_key_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True, help="encrypted private PEM output")
    parser.add_argument("--public", type=Path, required=True, help="public PEM output")
    parser.add_argument("--key-id", required=True, help="stable identifier embedded as JWT kid")
    args = parser.parse_args()
    validate_key_id(args.key_id)
    passphrase = getpass.getpass("Private key passphrase: ")
    confirmation = getpass.getpass("Confirm passphrase: ")
    if passphrase != confirmation:
        parser.error("passphrases do not match")
    generate_key_pair(args.private, args.public, passphrase)
    print(f"Created Ed25519 key pair {args.key_id!r}; private key was not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
