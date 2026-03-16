---
name: bnb-yield-cruiser
description: Build Binance-native BNB and idle-fund allocation plans with Simple Earn, Launchpool, HODLer Airdrops, Megadrop, Soft Staking, and optional Loan or Dual Investment logic. Use when users ask about BNB 闲置资金、Earn 收益、Simple Earn、Launchpool、HODLer Airdrops、Megadrop、流动性管理、收益提醒、Binance Earn recommendation, or want a safe AI copilot for Binance yield products.
metadata:
  version: "0.1.0"
  author: "kb"
license: MIT
---

# BNB Yield Cruiser

## Overview

Use this skill to turn Binance product data and event information into a practical allocation plan for BNB and idle funds.

This skill is for recommendation, ranking, reminder generation, and explanation. It is not for silent execution.

## Use This Skill When

Trigger this skill when the user asks for any of the following:

- how to allocate BNB or idle USDT inside Binance Earn
- whether to use `Simple Earn Flexible` or `Locked`
- how to stay eligible for `Launchpool`, `HODLer Airdrops`, or `Megadrop`
- how to preserve liquidity while keeping yield
- whether to redeem or use `Binance Loan`
- whether advanced products like `Dual Investment` fit their goals
- how to export reminder dates for Binance events

## Workflow

### 1. Gather user constraints

Collect or infer:

- assets and balances
- liquidity window
- risk tolerance
- whether locked products are acceptable
- whether advanced products are acceptable
- whether reminders are needed

If balances are not available, work from the user's stated holdings and label the output as estimate-based.

### 2. Pull data in source-priority order

Use sources in this order:

1. official API or official SDK
2. official Binance announcement pages
3. official Binance product and FAQ pages
4. third-party signals only as unconfirmed candidates

Use official API or SDK for:

- wallet balances
- `Simple Earn` product lists
- `Simple Earn` positions
- real-time APR or rate history when supported

Use official announcements for:

- `Launchpool`
- `HODLer Airdrops`
- `Megadrop`

Use official product and FAQ pages for:

- eligibility rules
- redemption timing
- snapshot behavior
- conversion or settlement risk

Never treat third-party media or KOL posts as confirmed fact. Require official confirmation before turning them into reminders or actionable recommendations.

### 3. Normalize opportunities

Convert each candidate into a common structure:

- `product_name`
- `category`
- `source_type`
- `source_url`
- `asset`
- `apr_type`
- `apr_value`
- `lock_days`
- `liquidity_level`
- `event_eligibility`
- `risk_tier`
- `confidence`
- `deadline`
- `notes`

Use the product tiers and default roles in [references/product-rules.md](./references/product-rules.md) when normalizing or comparing products.

### 4. Build a four-bucket plan

Every recommendation should use these buckets:

1. `Reserve`
2. `Core Yield`
3. `Event Capture`
4. `Advanced Optional`

Do not recommend a product list without a portfolio shape.

### 5. Score by fit, not by raw APR

Use a weighted fit model:

`score = yield_value + liquidity_fit + event_bonus + simplicity_bonus - lock_penalty - complexity_penalty - downside_penalty`

Emphasize:

- liquidity fit over APR when the user needs funds soon
- event eligibility when the user is BNB-centric
- simplicity for default users
- explicit tradeoff disclosure for advanced products

### 6. Explain both inclusion and exclusion

For each final plan:

- explain why selected products fit
- explain why at least one alternative was excluded

Good examples:

- `Locked BNB excluded because the user needs liquidity within 7 days.`
- `Dual Investment excluded because settlement may convert the asset.`
- `Megadrop downgraded because it favors Locked BNB and the user wants flexibility.`

### 7. Produce reminders

When event timing matters, generate reminder items for:

- subscription or eligibility windows
- snapshot periods
- farming end dates
- estimated reward distribution windows
- lock expiry or early-redemption risk dates

Prefer `.ics` export when the user wants something actionable.

## Product Scope

### Core

Default recommendation space:

- `Simple Earn Flexible`
- `Simple Earn Locked`
- `Launchpool`
- `HODLer Airdrops`
- `Soft Staking`

### Advanced

Show only when the user accepts more complexity or the scenario clearly calls for it:

- `Megadrop`
- `Binance Loan`
- `Dual Investment`

### High Risk

Do not recommend by default to conservative users:

- `On-chain Yields`
- `Smart Arbitrage`

For detailed product roles and current design assumptions, read [references/product-rules.md](./references/product-rules.md).

## Safety Rules

- Never imply guaranteed returns.
- Never recommend enabling withdrawal permissions on API keys.
- Treat all auto-subscribe, subscribe, redeem, borrow, or settlement actions as confirmation-required.
- If data is partial, label the plan as partial.
- If a signal comes from a non-official source, label it `unconfirmed`.
- Surface region, KYC, task, and collateral caveats when relevant.

## Output Format

Default output should contain:

### 1. Recommendation summary

- user inputs used
- confidence level
- whether data is live, estimated, or mixed

### 2. Allocation plan

- `Reserve`
- `Core Yield`
- `Event Capture`
- `Advanced Optional`

### 3. Top opportunities

For each item:

- product
- why it fits
- what the user gives up
- any deadline or eligibility condition

### 4. Excluded products

- short reason for exclusion

### 5. Reminders

- event name
- date or timing note
- why it matters

### 6. Risk notice

- no guaranteed returns
- product-specific caveats

## Example Requests

- `我有 8 BNB + 3000 USDT，7 天内要保留流动性，帮我做一个币安收益方案。`
- `Use $bnb-yield-cruiser to compare Simple Earn Flexible, Locked BNB, and Launchpool eligibility for my BNB.`
- `我想拿 Launchpool 和 HODLer 空投，但不想锁太久。`
- `Should I redeem my BNB position or use Binance Loan for short-term liquidity?`
- `帮我生成 Launchpool 和 Megadrop 的提醒日历。`

## Implementation Notes

- For live product data, prefer the official Binance SDK modules for `simple_earn` and `wallet`.
- For `Launchpool`, `HODLer Airdrops`, and `Megadrop`, prefer official announcement monitoring over unofficial scraping.
- Use third-party signals only for early discovery, then upgrade them to confirmed only after official verification.
