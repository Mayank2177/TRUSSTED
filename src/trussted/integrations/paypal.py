"""PayPal Orders v2 (sandbox by default): create an order for the policy-approved cart, then
capture only after the buyer approved AND the order amount still equals what we approved.

Flow: OAuth client-credentials -> POST /v2/checkout/orders (intent CAPTURE) -> buyer approves at
the returned link -> GET order (status APPROVED, amount matches) -> POST .../capture.
Verify field names against developer.paypal.com for your account before production use.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from ..config import PayPalConfig
from ..errors import ConfigError, IntegrationError, PaymentError
from ..models.decision import Decision, DecisionResult
from ..models.money import Money
from ..models.results import RankedCandidate
from ..rank.scorer import total_cost
from .http import HttpTransport, UrllibTransport, send_json

_ORDER_ID = re.compile(r"^[A-Za-z0-9_-]{5,64}$")
_TOKEN_SAFETY_S = 60


@dataclass(frozen=True, slots=True)
class PayPalOrder:
    order_id: str
    status: str
    approve_url: str | None


@dataclass(frozen=True, slots=True)
class PayPalCapture:
    order_id: str
    status: str
    capture_id: str | None


def _err(status: int, data: Any, what: str) -> PaymentError:
    detail = ""
    if isinstance(data, dict):
        detail = f" {data.get('name', '')} {data.get('message', '')} debug_id={data.get('debug_id', '')}"
    return PaymentError(f"PayPal {what} failed (HTTP {status}){detail}".strip())


class PayPalClient:
    def __init__(
        self, config: PayPalConfig, *, client_id: str | None = None,
        client_secret: str | None = None, transport: HttpTransport | None = None,
        sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
    ) -> None:
        cid = client_id or os.environ.get(config.client_id_env, "")
        secret = client_secret or os.environ.get(config.client_secret_env, "")
        if not cid or not secret:
            raise ConfigError(f"PayPal credentials missing: set {config.client_id_env} / "
                              f"{config.client_secret_env}")
        self._cfg = config
        self._basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        self._transport = transport or UrllibTransport()
        self._sleep, self._clock = sleep, clock
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    # -- auth -------------------------------------------------------------------------------
    def _access_token(self) -> str:
        with self._lock:
            if self._token and self._clock() < self._expires_at:
                return self._token
            status, data = send_json(
                self._transport, "POST", f"{self._cfg.base_url}/v1/oauth2/token",
                headers={"Authorization": f"Basic {self._basic}",
                         "Content-Type": "application/x-www-form-urlencoded",
                         "Accept": "application/json"},
                raw_body=b"grant_type=client_credentials", timeout_s=self._cfg.timeout_s,
                retries=self._cfg.max_retries, backoff_s=self._cfg.retry_backoff_s, sleep=self._sleep,
            )
            if status != 200 or not isinstance(data, dict) or not data.get("access_token"):
                raise _err(status, data, "authentication")
            try:
                ttl = int(data.get("expires_in", 0))
            except (TypeError, ValueError):
                ttl = 0
            self._token = str(data["access_token"])
            self._expires_at = self._clock() + max(ttl - _TOKEN_SAFETY_S, 0)
            return self._token

    def _call(self, method: str, path: str, payload: Any | None, request_id: str | None) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {self._access_token()}",
                   "Content-Type": "application/json", "Accept": "application/json"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        return send_json(self._transport, method, f"{self._cfg.base_url}{path}", headers=headers,
                         payload=payload, timeout_s=self._cfg.timeout_s,
                         retries=self._cfg.max_retries, backoff_s=self._cfg.retry_backoff_s,
                         sleep=self._sleep)

    # -- orders -----------------------------------------------------------------------------
    def create_order(self, decision: Decision, candidate: RankedCandidate, quantity: int,
                     *, request_id: str | None = None) -> PayPalOrder:
        """Create an order only for an ALLOW decision and its exact approved cart."""
        if decision.result is not DecisionResult.ALLOW:
            raise PaymentError(f"refusing to create an order for a {decision.result} decision")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise PaymentError("quantity must be a positive integer")
        fact = candidate.fact
        if decision.winner_fact_id != fact.fact_id or decision.amount != candidate.total_cost:
            raise PaymentError("decision does not match the candidate cart")
        if candidate.total_cost != total_cost(fact, quantity):
            raise PaymentError("quantity does not match the approved candidate cart")
        if not self._cfg.return_url or not self._cfg.cancel_url:
            raise ConfigError("PayPalConfig.return_url and cancel_url are required")
        total, cur = candidate.total_cost, candidate.total_cost.currency

        breakdown: dict[str, Any] = {
            "item_total": {"currency_code": cur, "value": (fact.price * quantity).amount_str()}}
        if fact.shipping is not None:
            breakdown["shipping"] = {"currency_code": cur, "value": fact.shipping.amount_str()}
        if fact.additional_charges is not None:
            breakdown["handling"] = {"currency_code": cur, "value": fact.additional_charges.amount_str()}
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": fact.fact_id[:256],
                "amount": {"currency_code": cur, "value": total.amount_str(), "breakdown": breakdown},
                "items": [{"name": fact.name[:127], "quantity": str(quantity),
                           "unit_amount": {"currency_code": cur, "value": fact.price.amount_str()}}],
            }],
            "payment_source": {"paypal": {"experience_context": {
                "return_url": self._cfg.return_url, "cancel_url": self._cfg.cancel_url,
                "user_action": "PAY_NOW", "shipping_preference": "GET_FROM_FILE"}}},
        }
        rid = request_id or hashlib.sha256(
            f"{fact.fact_id}|{total.amount_minor}|{cur}|{quantity}".encode()).hexdigest()[:32]
        status, data = self._call("POST", "/v2/checkout/orders", payload, rid)
        if status not in (200, 201) or not isinstance(data, dict) or not data.get("id"):
            raise _err(status, data, "create order")
        links = data.get("links") if isinstance(data.get("links"), list) else []
        approve = next((l.get("href") for l in links if isinstance(l, dict)
                        and l.get("rel") in ("payer-action", "approve")), None)
        return PayPalOrder(str(data["id"]), str(data.get("status", "")), approve)

    def capture_order(self, order_id: str, expected: Money, *, request_id: str | None = None) -> PayPalCapture:
        """Capture only if the buyer approved and the amount still equals ``expected``."""
        if not _ORDER_ID.match(order_id):
            raise PaymentError("invalid order id")
        path = f"/v2/checkout/orders/{quote(order_id, safe='')}"
        status, order = self._call("GET", path, None, None)
        if status != 200 or not isinstance(order, dict):
            raise _err(status, order, "get order")
        if order.get("status") != "APPROVED":
            raise PaymentError(f"order is {order.get('status')!r}, not APPROVED")
        try:
            units = order["purchase_units"]
            amount = units[0]["amount"]
            paid = Decimal(str(amount["value"]))
            cur = amount["currency_code"]
        except (KeyError, IndexError, TypeError, InvalidOperation) as exc:
            raise PaymentError("order has no readable amount") from exc
        if len(units) != 1 or cur != expected.currency or paid != expected.to_decimal():
            raise PaymentError(f"order amount {paid} {cur} does not match approved {expected}")
        status, data = self._call("POST", f"{path}/capture", {}, request_id or f"cap-{order_id}"[:36])
        if status not in (200, 201) or not isinstance(data, dict):
            raise _err(status, data, "capture")
        if data.get("status") != "COMPLETED":
            raise PaymentError(f"capture status {data.get('status')!r}")
        capture_id = None
        try:
            capture_id = data["purchase_units"][0]["payments"]["captures"][0]["id"]
        except (KeyError, IndexError, TypeError):
            pass
        return PayPalCapture(order_id, "COMPLETED", capture_id)
