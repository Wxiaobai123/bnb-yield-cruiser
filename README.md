# BNB Yield Cruiser

[Live Demo](https://bnb-yield-cruiser.onrender.com) | [Deploy to Render](https://dashboard.render.com/blueprint/new?repo=https%3A%2F%2Fgithub.com%2FWxiaobai123%2Fbnb-yield-cruiser) | [GitHub Repository](https://github.com/Wxiaobai123/bnb-yield-cruiser)

Safe public demo mode:

- sample data by default
- official public event monitoring when available
- no personal Binance credentials
- no public Telegram credential collection

BNB Yield Cruiser is a Binance-native allocation copilot for BNB and idle funds.

It helps users balance three things at the same time:

- liquidity they may need in the near term
- core yield opportunities such as Simple Earn
- event-based opportunities such as Launchpool, HODLer Airdrops, and Megadrop

The product does not silently execute subscriptions or trades. It focuses on recommendation, explanation, reminder generation, and execution guidance.

## What It Does

- Reads a user's portfolio profile for `BNB` and `USDT`
- Supports live Binance balance and Simple Earn data when credentials are provided
- Monitors official Binance public announcement feeds for event opportunities
- Builds a four-bucket allocation plan:
  - `Reserve`
  - `Core Yield`
  - `Event Capture`
  - `Advanced Optional`
- Explains why a product is selected and why alternatives are excluded
- Generates reminder events and exports them as `.ics`
- Supports Telegram test notifications and plan push notifications

## Product Principles

- Official API first
- Official announcements first for event confirmation
- No guarantee language
- No silent execution
- Keep liquidity visible before chasing extra yield

## Product Experience

The web app provides:

- a desktop-first control panel
- dynamic scenario guidance
- live or sample data modes
- asset overview by:
  - spot
  - Simple Earn flexible
  - locked positions
  - deployable balances
- next-step action cards:
  - `现在处理`
  - `等待提醒`
  - `暂不纳入`

## Repository Layout

```text
app/                    Core planner, live data, public events, Telegram, ICS
web/                    Frontend UI
data/                   Sample profiles and normalized opportunities
scripts/                Local verification helpers
skill/                  OpenClaw/OpenAI skill package for the product
main.py                 CLI entry for plan generation
serve.py                Local demo server
```

## Quick Start

### 1. Install optional live-data dependencies

If you only want to use sample mode, the standard library is enough.

If you want live Binance balances and Simple Earn data:

```bash
pip install -r requirements.txt
```

### 2. Start the local web app

```bash
python3 serve.py
```

Open:

```text
http://127.0.0.1:8765
```

## Public Demo Deployment

This repository includes a ready-to-deploy `render.yaml` Blueprint for Render.

The public demo configuration is intentionally safer than local self-hosting:

- `PUBLIC_DEMO=true`
- `ENABLE_TELEGRAM=false`
- no Binance credentials are required

That means the hosted demo:

- uses sample data by default
- can still try official public announcement data
- does not accept personal Telegram credentials
- does not expose private Binance account access

One-click Blueprint setup:

```text
https://render.com/deploy?repo=https://github.com/Wxiaobai123/bnb-yield-cruiser
```

### 3. Run the CLI planner

```bash
python3 main.py --mode sample
```

For live mode:

```bash
BINANCE_API_KEY=... BINANCE_SECRET_KEY=... python3 main.py --mode live --use-wallet-balances
```

## Environment Variables

Copy `.env.example` and fill in only the values you need.

### Binance

- `BINANCE_API_KEY`
- `BINANCE_SECRET_KEY`

Used for:

- spot balances
- Simple Earn positions
- live Simple Earn opportunities

### Telegram

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Used for:

- connection testing
- sending the current plan to Telegram

If Telegram config is entered from the web UI, it is stored locally in `data/telegram_config.json`. That file is ignored by Git.

## Data Modes

- `sample`: only sample opportunities and sample balances
- `auto`: prefers live data when credentials are available, otherwise falls back
- `live`: requires Binance credentials
- `mixed-live`: live yield data with sample event data fallback
- `live+public`: live yield data with official public announcement events

## Event Sources

Event opportunities are sourced with this priority:

1. official Binance APIs and SDKs
2. official Binance announcement APIs
3. official Binance product and rule pages
4. third-party signals only as unconfirmed candidates

## Safety Notes

- This project is not investment advice.
- This project does not default to executing subscriptions, loans, or advanced products.
- API keys should never enable withdrawal permissions.
- Event opportunities should be treated as time-sensitive and may change after official updates.

## Local Validation

Check public event parsing:

```bash
python3 scripts/verify_public_events.py
```

Run the app in sample mode from the browser and verify:

- plan generation
- `.ics` export
- Telegram connect and test flow

## Included Product Package

The `skill/` directory contains the product skill package used to wrap the planning logic as an agent skill:

- `skill/SKILL.md`
- `skill/references/product-rules.md`
- `skill/agents/openai.yaml`

## What Is Intentionally Not Included

This public repository excludes:

- local-only planning notes
- private credentials
- local Telegram config
- generated build artifacts
- unrelated project files

## License

MIT
