"""Validated simulated-token storage data; cryptographic checks remain upstream."""

from pydantic import AwareDatetime

from warrant.db.contracts import Currency, FrozenModel, Hash, Id, Money
from warrant.db.contracts.receipts import NonemptyText


class CredentialInput(FrozenModel):
    """A newly issued credential cannot arrive already redeemed."""

    id: Id
    run_id: Id
    cart_hash: Hash
    merchant_id: Id
    amount_minor: Money
    currency: Currency
    nonce: Id
    expires_at: AwareDatetime
    redeemed_at: None = None
    signature: NonemptyText
    approval_hash: Hash
