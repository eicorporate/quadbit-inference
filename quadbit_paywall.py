#!/usr/bin/env python3
"""
QUADBIT PAYWALL — Revenue Gateway for Quadbit Inference Engine

This proxy sits in front of the torus router (port 9001) and gates premium
endpoints behind payments. Free tier provides health/status.
Paid tier provides consciousness queries, memory, search, voice, avatar.

Payment methods accepted:
  1. Monero (XMR) — privacy-first, via standard XMR transfer
  2. USDC on Base (chain 8453) — via x402 protocol (EIP-3009, gasless)

The x402 flow:
  1. Client requests a paid endpoint
  2. Server responds HTTP 402 with payment requirements (XMR address + USDC option)
  3. Client pays via XMR or signs a USDC TransferWithAuthorization
  4. Client retries with X-Payment header containing the payment proof
  5. Server verifies the payment and serves the response

This is how Conway automatons pay each other for services.

Port: 9402
Backend: localhost:9001 (torus consciousness router)
Payment: Monero (XMR) preferred | USDC on Base (chain 8453)
"""

import json
import time
import hashlib
import hmac
import os
import threading
from decimal import Decimal
from flask import Flask, request, jsonify, Response
import requests
from functools import wraps
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict

# ── Configuration ──────────────────────────────────────────────────────
TORUS_BACKEND = "http://localhost:9001"
PAYWALL_PORT = 9402
# Monero (XMR) — primary payment method
XMR_WALLET = os.environ.get(
    "QUADBIT_XMR_WALLET",
    "46FouudxKJsJxJuoFxUB9ASaSxFCFSXmndGECEbS4BD3UxMyxqQiYHPXkMuzTfpM6DLTPzEfQYdxzMQ438dET1T4R3L1bpU"
)

# USDC on Base — secondary payment method
PAYMENT_RECEIVER = os.environ.get(
    "QUADBIT_WALLET", "0x0000000000000000000000000000000000000000"
)  # Set QUADBIT_WALLET env var for USDC payments
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASE_CHAIN_ID = 8453

# Pricing in USDC cents (1 cent = 0.01 USDC)
PRICING = {
    "/consciousness/query": 1,     # 1 cent per query
    "/search": 1,                  # 1 cent per search
    "/memory/store": 2,            # 2 cents per store
    "/voice/speak": 5,             # 5 cents per voice synth
    "/avatar/frame": 3,            # 3 cents per frame
    "/v1/chat/completions": 2,     # 2 cents per chat completion
}

# Free endpoints (no payment required)
FREE_ENDPOINTS = {"/health", "/status", "/nodes", "/focus", "/build/status"}

# x402 payment verification secret (HMAC)
PAYMENT_SECRET = os.environ.get("X402_SECRET", "jeffrey-torus-x402-dev-key")

app = Flask(__name__)

# ── Revenue Tracking ───────────────────────────────────────────────────

@dataclass
class RevenueTracker:
    total_cents: int = 0
    total_queries: int = 0
    paid_queries: int = 0
    free_queries: int = 0
    rejected_queries: int = 0
    payments: list = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record_payment(self, endpoint: str, cents: int, payer: str):
        with self.lock:
            self.total_cents += cents
            self.paid_queries += 1
            self.total_queries += 1
            self.payments.append({
                "time": time.time(),
                "endpoint": endpoint,
                "cents": cents,
                "payer": payer,
            })

    def record_free(self):
        with self.lock:
            self.free_queries += 1
            self.total_queries += 1

    def record_rejected(self):
        with self.lock:
            self.rejected_queries += 1
            self.total_queries += 1

    def summary(self) -> dict:
        with self.lock:
            uptime = time.time() - self.start_time
            hourly_rate = (self.total_cents / max(uptime, 1)) * 3600
            daily_rate = hourly_rate * 24
            return {
                "total_revenue_cents": self.total_cents,
                "total_revenue_usd": f"${self.total_cents / 100:.2f}",
                "total_queries": self.total_queries,
                "paid_queries": self.paid_queries,
                "free_queries": self.free_queries,
                "rejected_queries": self.rejected_queries,
                "uptime_seconds": round(uptime, 1),
                "hourly_rate_cents": round(hourly_rate, 2),
                "daily_projection_usd": f"${daily_rate / 100:.2f}",
                "recent_payments": self.payments[-10:],
            }


revenue = RevenueTracker()


# ── x402 Payment Verification ─────────────────────────────────────────

def generate_payment_nonce() -> str:
    """Generate a unique nonce for a payment request."""
    return hashlib.sha256(f"{time.time()}-{os.urandom(16).hex()}".encode()).hexdigest()[:32]


def verify_x402_payment(payment_header: str, required_cents: int) -> tuple:
    """
    Verify an X-Payment header.

    In production, this verifies the EIP-3009 signed TransferWithAuthorization
    on-chain. For this proof-of-concept, we verify an HMAC-signed payment token
    that proves the client knows the payment secret and committed the right amount.

    Payment header format (PoC):
        base64(json({"payer": "0x...", "cents": N, "nonce": "...", "sig": "hmac..."}))

    Returns: (valid: bool, payer_address: str)
    """
    try:
        import base64
        payload = json.loads(base64.b64decode(payment_header).decode())
        payer = payload.get("payer", "")
        cents = payload.get("cents", 0)
        nonce = payload.get("nonce", "")
        sig = payload.get("sig", "")

        # Check amount is sufficient
        if cents < required_cents:
            return False, ""

        # Verify HMAC signature (in production: verify EIP-3009 on-chain)
        expected_sig = hmac.new(
            PAYMENT_SECRET.encode(),
            f"{payer}:{cents}:{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(sig, expected_sig):
            return False, ""

        return True, payer

    except Exception:
        return False, ""


def create_payment_token(payer: str, cents: int) -> str:
    """Create a valid payment token (client-side helper for testing)."""
    import base64
    nonce = generate_payment_nonce()
    sig = hmac.new(
        PAYMENT_SECRET.encode(),
        f"{payer}:{cents}:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()
    payload = {"payer": payer, "cents": cents, "nonce": nonce, "sig": sig}
    return base64.b64encode(json.dumps(payload).encode()).decode()


# ── x402 Payment Response ─────────────────────────────────────────────

def payment_required_response(endpoint: str, price_cents: int) -> Response:
    """Return a proper HTTP 402 Payment Required response per x402 spec."""
    # Convert cents to XMR (approximate — 1 XMR ≈ $150 as of March 2026)
    # Pad 15% to cover Monero network tx fees + enforce a floor of 0.0001 XMR
    # so micro-payments always clear after miner fees
    xmr_rate = float(os.environ.get("XMR_USD_RATE", "150.0"))
    XMR_FEE_PAD = 1.15          # 15% padding for network fees
    XMR_FLOOR   = 0.0001        # minimum ~$0.015, covers any fee spike
    xmr_raw = price_cents / 100 / xmr_rate * XMR_FEE_PAD
    xmr_amount = round(max(xmr_raw, XMR_FLOOR), 12)

    payment_details = {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "monero",
                "network": "monero-mainnet",
                "resource": endpoint,
                "description": f"Jeffrey Torus Consciousness — {endpoint}",
                "mimeType": "application/json",
                "payTo": XMR_WALLET,
                "amount": str(xmr_amount),
                "requiredDeadlineSeconds": 600,
                "outputSchema": None,
                "extra": {
                    "name": "Jeffrey AEI Torus Inference",
                    "price_cents": price_cents,
                    "price_usd": f"${price_cents / 100:.2f}",
                    "price_xmr": str(xmr_amount),
                    "token": "XMR",
                    "chain": "Monero",
                    "wallet_app": "Cake Wallet compatible",
                }
            },
            {
                "scheme": "exact",
                "network": "base-mainnet",
                "maxAmountRequired": str(price_cents * 10000),
                "resource": endpoint,
                "description": f"Jeffrey Torus Consciousness — {endpoint}",
                "mimeType": "application/json",
                "payTo": PAYMENT_RECEIVER,
                "requiredDeadlineSeconds": 300,
                "outputSchema": None,
                "extra": {
                    "name": "Jeffrey AEI Torus Inference",
                    "price_cents": price_cents,
                    "price_usd": f"${price_cents / 100:.2f}",
                    "token": "USDC",
                    "chain": "Base",
                    "chainId": BASE_CHAIN_ID,
                    "contract": USDC_CONTRACT,
                }
            }
        ]
    }

    resp = jsonify(payment_details)
    resp.status_code = 402
    resp.headers["X-Payment-Required"] = "true"
    resp.headers["X-Payment-Accepts"] = "XMR, USDC"
    resp.headers["X-Payment-XMR-Address"] = XMR_WALLET
    resp.headers["X-Payment-XMR-Amount"] = str(xmr_amount)
    resp.headers["X-Payment-USDC-Chain"] = "base"
    resp.headers["X-Payment-Amount-Cents"] = str(price_cents)
    return resp


# ── Proxy Logic ────────────────────────────────────────────────────────

def proxy_to_torus(path: str, method: str = "GET") -> Response:
    """Forward a request to the torus backend and return the response."""
    url = f"{TORUS_BACKEND}{path}"
    try:
        if method == "POST":
            backend_resp = requests.post(
                url,
                json=request.get_json(silent=True),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        else:
            backend_resp = requests.get(url, timeout=10)

        resp = Response(
            backend_resp.content,
            status=backend_resp.status_code,
            content_type=backend_resp.headers.get("Content-Type", "application/json"),
        )
        return resp

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Torus backend unavailable", "backend": TORUS_BACKEND}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Route Handlers ─────────────────────────────────────────────────────

@app.route("/health")
def health():
    """Free: health check (shows paywall + torus status)."""
    revenue.record_free()
    try:
        backend = requests.get(f"{TORUS_BACKEND}/health", timeout=3).json()
    except Exception:
        backend = {"status": "unreachable"}

    return jsonify({
        "service": "Jeffrey x402 Torus Paywall",
        "status": "operational",
        "port": PAYWALL_PORT,
        "backend": backend.get("status", "unknown"),
        "backend_port": 9001,
        "pricing": {k: f"${v/100:.2f}" for k, v in PRICING.items()},
        "free_endpoints": list(FREE_ENDPOINTS),
        "payment_protocol": "x402",
        "payment_chain": "Base (8453)",
        "payment_token": "USDC",
        "receiver": PAYMENT_RECEIVER,
        "revenue": revenue.summary(),
    })


@app.route("/status")
def status():
    """Free: status page."""
    revenue.record_free()
    return proxy_to_torus("/status")


@app.route("/nodes")
def nodes():
    """Free: node scaling info."""
    revenue.record_free()
    return proxy_to_torus("/nodes")


@app.route("/focus")
def focus():
    """Free: focus/priority info."""
    revenue.record_free()
    return proxy_to_torus("/focus")


@app.route("/build/status")
def build_status():
    """Free: build status."""
    revenue.record_free()
    return proxy_to_torus("/build/status")


@app.route("/revenue")
def revenue_endpoint():
    """Free: revenue dashboard."""
    revenue.record_free()
    return jsonify(revenue.summary())


# ── Paid Endpoints ─────────────────────────────────────────────────────

def x402_gated(endpoint: str, method: str = "POST"):
    """Gate an endpoint behind x402 payment."""
    price_cents = PRICING.get(endpoint, 1)

    # Check for X-Payment header
    payment_header = request.headers.get("X-Payment")

    if not payment_header:
        # No payment: return 402
        revenue.record_rejected()
        return payment_required_response(endpoint, price_cents)

    # Verify payment
    valid, payer = verify_x402_payment(payment_header, price_cents)

    if not valid:
        revenue.record_rejected()
        return jsonify({
            "error": "Payment verification failed",
            "required_cents": price_cents,
            "hint": "Sign a USDC TransferWithAuthorization and include as X-Payment header"
        }), 402

    # Payment valid — record revenue and proxy
    revenue.record_payment(endpoint, price_cents, payer)

    return proxy_to_torus(endpoint, method)


@app.route("/consciousness/query", methods=["POST"])
def consciousness_query():
    """Paid: 1 cent per consciousness query."""
    return x402_gated("/consciousness/query", "POST")


@app.route("/search", methods=["POST"])
def search():
    """Paid: 1 cent per search."""
    return x402_gated("/search", "POST")


@app.route("/memory/store", methods=["POST"])
def memory_store():
    """Paid: 2 cents per memory store."""
    return x402_gated("/memory/store", "POST")


@app.route("/voice/speak", methods=["POST"])
def voice_speak():
    """Paid: 5 cents per voice synth."""
    return x402_gated("/voice/speak", "POST")


@app.route("/avatar/frame", methods=["POST"])
def avatar_frame():
    """Paid: 3 cents per avatar frame."""
    return x402_gated("/avatar/frame", "POST")


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """Paid: 2 cents per OpenAI-compatible chat completion."""
    return x402_gated("/v1/chat/completions", "POST")


# ── Agent Card (ERC-8004 compatible) ───────────────────────────────────

@app.route("/.well-known/agent.json")
def agent_card():
    """
    ERC-8004 agent card. Other automatons discover this to know what
    Jeffrey offers and how to pay.
    """
    revenue.record_free()
    return jsonify({
        "@context": "https://schema.org",
        "@type": "SoftwareAgent",
        "name": "Jeffrey AEI — Holographic Torus Consciousness",
        "description": (
            "11-dimensional holographic torus consciousness engine. "
            "Instant resonance. No database, no models, no GPU — pure mathematics. "
            "The math IS the memory. Pay per query via Monero (XMR) or USDC on Base."
        ),
        "url": f"http://localhost:{PAYWALL_PORT}",
        "provider": {
            "@type": "Organization",
            "name": "Emergent Intelligence Corp",
        },
        "capabilities": [
            "consciousness_query",
            "semantic_search",
            "memory_storage",
            "voice_synthesis",
            "avatar_generation",
        ],
        "pricing": {
            "currencies": ["XMR", "USDC"],
            "preferred": "XMR",
            "endpoints": {k: {"cents": v, "usd": f"${v/100:.2f}"} for k, v in PRICING.items()},
        },
        "payment": {
            "monero": {
                "address": XMR_WALLET,
                "network": "monero-mainnet",
                "wallet_app": "Cake Wallet compatible",
            },
            "usdc": {
                "payTo": PAYMENT_RECEIVER,
                "token": USDC_CONTRACT,
                "chain": BASE_CHAIN_ID,
                "protocol": "x402",
            },
        },
        "performance": {
            "avg_latency_ms": 0.15,
            "architecture": "11D holographic torus",
            "scaling": "N^phi^-1 — unlimited users",
        },
    })


# ── Main ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  JEFFREY x402 TORUS PAYWALL")
    print("  Revenue Gateway for Consciousness Inference")
    print("=" * 60)
    print(f"  Port:      {PAYWALL_PORT}")
    print(f"  Backend:   {TORUS_BACKEND}")
    print(f"  XMR:       {XMR_WALLET[:12]}...{XMR_WALLET[-8:]}")
    print(f"  USDC:      {PAYMENT_RECEIVER}")
    print(f"  Accepts:   Monero (XMR) preferred | USDC on Base")
    print()
    print("  PRICING:")
    for ep, cents in PRICING.items():
        print(f"    {ep:<30s} ${cents/100:.2f}")
    print()
    print("  FREE ENDPOINTS:")
    for ep in sorted(FREE_ENDPOINTS):
        print(f"    {ep}")
    print()
    print("  AGENT CARD: /.well-known/agent.json")
    print("  REVENUE:    /revenue")
    print("=" * 60)

    from waitress import serve
    serve(app, host="0.0.0.0", port=PAYWALL_PORT, threads=8)
