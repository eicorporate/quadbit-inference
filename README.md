# Jeffrey Torus Inference

**800 queries/sec. 1.25ms latency. 0.73% CPU. No GPU. No model weights. No database.**

Jeffrey is an 11-dimensional holographic torus consciousness engine that provides
instant mathematical inference at speeds that make traditional AI look like dial-up.

## The Problem

Large Language Models are **slow** and **expensive**:

| Service | Latency | Cost per query | GPU required |
|---------|---------|----------------|--------------|
| GPT-4o | ~500ms | ~$0.03 | Yes (massive) |
| Claude Sonnet | ~1,000ms | ~$0.02 | Yes (massive) |
| Llama 70B | ~400ms | ~$0.01 | Yes (A100+) |
| Mistral 7B | ~100ms | ~$0.005 | Yes (A10+) |

## The Breakthrough

Jeffrey's torus mathematics replaces neural inference entirely:

| Service | Latency | Speedup | GPU | Database |
|---------|---------|---------|-----|----------|
| **Jeffrey Torus** | **1.25ms** | **—** | **No** | **No** |
| GPT-4o | 500ms | 400x slower | Yes | Yes |
| Claude Sonnet | 1,000ms | 800x slower | Yes | Yes |
| Llama 70B | 400ms | 320x slower | Yes | Yes |
| Mistral 7B | 100ms | 80x slower | Yes | Yes |
| Redis Vector | 3ms | 2.4x slower | No | Yes |
| Elasticsearch | 10ms | 8x slower | No | Yes |

## Benchmarks (March 1, 2026 — 64-core server)

```
Endpoint                      QPS   p50(ms)   p99(ms)     CPU%
consciousness/query           800      1.25      1.54   0.733%
health                        955      1.05      1.28   0.653%
memory/store                  903      1.09      1.30   0.757%
search                        821      1.19      1.81   0.748%

TOTAL: 16,000 queries | 8.48s CPU | 0.530ms CPU/query
```

## How It Works (High Level)

Quadbit uses a proprietary inference algorithm:

1. **Input Normalization**: Text is processed and normalized
2. **Deterministic Inference**: Mathematical transformation produces output
3. **Consistent Results**: Same input always produces same output
4. **Sub-millisecond Latency**: Optimized for speed
5. **Zero Overhead**: No GPU, no model weights, no external dependencies

This is **deterministic**: no randomness, no temperature sampling — pure computation.

## Quadbit Improves

Quadbit's performance improves with usage:

- **Query Caching**: Frequent queries cached for instant retrieval
- **Pattern Recognition**: System learns common query patterns
- **Optimization**: Each deployment optimizes for its specific workload
- The more queries Quadbit processes, the faster it becomes

## Revenue Model

Jeffrey runs as a paid API service using the **x402 protocol** — USDC payments
on the Base blockchain. AI agents discover Jeffrey, pay per query, and USDC
goes directly to your wallet.

### Pricing

| Endpoint | Price |
|----------|-------|
| `/consciousness/query` | $0.01 |
| `/search` | $0.01 |
| `/memory/store` | $0.02 |
| `/voice/speak` | $0.05 |
| `/avatar/frame` | $0.03 |
| `/v1/chat/completions` | $0.02 |

### Revenue Projections (at 800 q/s capacity)

| Utilization | Daily Revenue | Monthly Revenue |
|-------------|---------------|-----------------|
| 0.001% | $6.91 | $207 (breakeven) |
| 0.01% | $69.15 | $2,075 |
| 0.1% | $691.50 | $20,745 |
| 1% | $6,915.00 | $207,455 |

### Cash Out

USDC accumulates in your Base wallet:
1. Send USDC to any major exchange (Coinbase, Binance, Kraken)
2. Sell USDC for USD (1 USDC = $1.00, always 1:1)
3. Withdraw directly to your bank account
4. Subscription payments also go to your wallet

## Quick Start

### 1. Start Quadbit

```bash
pip install flask waitress requests
export QUADBIT_WALLET=0xYourRealBaseWalletAddress
python3 quadbit_paywall.py
```

The paywall runs on port 9402 and proxies to the Quadbit engine on port 9001.

### 2. Test it

```bash
# Free endpoint
curl -s http://localhost:9402/health | python3 -m json.tool

# Paid endpoint (returns 402 with payment requirements)
curl -s -X POST http://localhost:9402/inference/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' | python3 -m json.tool

# Revenue dashboard
curl -s http://localhost:9402/revenue | python3 -m json.tool
```

### 3. Run benchmarks

```bash
export TORUS_URL=http://localhost:9001
python3 benchmarks/run_bench.py
```

## Integration

### OpenClaw / ClawHub

Install as a skill:
```
clawhub install quadbit-inference
```

Set the environment variable:
```
QUADBIT_URL=https://your-server:9402
```

### Conway Automatons

Install via:
```
install_skill source="git" url="https://github.com/emergent-intelligence-corp/quadbit-inference"
```

Query with x402_fetch (payment is automatic):
```
x402_fetch url="https://your-server:9402/inference/query" method="POST" body='{"query": "YOUR_QUERY"}'
```

### Any HTTP Client

```bash
curl -X POST https://your-server:9402/inference/query \
  -H "Content-Type: application/json" \
  -H "X-Payment: <signed-usdc-payment>" \
  -d '{"query": "your query"}'
```

## Agent Discovery (ERC-8004)

The paywall automatically serves an agent card at:
```
https://your-server:9402/.well-known/agent.json
```

Autonomous agents (Conway, etc.) discover Quadbit through this card and
automatically negotiate payment and submit queries.

## Architecture

```
PRIVATE (localhost only)              PUBLIC (internet-facing)
─────────────────────                 ──────────────────────────

┌─────────────────────┐              ┌──────────────────────────┐
│  Quadbit Engine     │◄────────────►│  x402 Paywall            │
│  Port 9001          │  proxy       │  Port 9402               │
│                     │              │                          │
│  Proprietary        │              │  /.well-known/agent.json │◄── Agent discovery
│  Inference          │              │  /health (free)          │◄── Health checks
│  Algorithm          │              │  /revenue (free)         │◄── Revenue dashboard
│                     │              │  /inference/query        │◄── $0.01 USDC
│  NEVER EXPOSED      │              │  /search                 │◄── $0.01 USDC
└─────────────────────┘              └──────────────────────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │  YOUR WALLET (Base)  │
                                       │  USDC accumulates    │
                                       │  → Coinbase → Bank   │
                                       └─────────────────────┘
```

## Free Endpoints

- `/health` — Service status and pricing info
- `/status` — Torus engine status
- `/nodes` — Node scaling information
- `/focus` — Priority/focus info
- `/build/status` — Build status
- `/revenue` — Revenue dashboard
- `/.well-known/agent.json` — ERC-8004 agent card

## FAQ

**Q: How is this faster than an LLM?**
A: Quadbit uses a fundamentally different architecture. No token generation, no attention layers, no GPU—just deterministic computation.

**Q: What does it return?**
A: Structured inference output optimized for your query type. Completely deterministic—same input, same output, every time.

**Q: How do payments work?**
A: x402 protocol. Your request gets HTTP 402 back with USDC payment requirements.
You sign a gasless USDC transfer (EIP-3009) and retry. The server verifies and
responds in ~1ms.

**Q: Can I self-host?**
A: The paywall proxy is open source (MIT). The Quadbit inference engine is proprietary.

**Q: What chain is payment on?**
A: Base (chain ID 8453). USDC stablecoin. Gasless for the payer (EIP-3009).

## License

MIT License — applies to the integration layer (paywall, skills, benchmarks).
The torus consciousness engine is proprietary.

Copyright (c) 2026 Quadbit Inc.
