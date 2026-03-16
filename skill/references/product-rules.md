# Product Rules

Use this file when the task requires ranking or comparing Binance yield products for BNB-centric users.

## Source Priority

1. `official_api`
2. `official_announcement`
3. `official_rule`
4. `third_party_signal`

Third-party signals are discovery-only until an official source confirms them.

## Default Tiers

### Core

- `Simple Earn Flexible`
- `Simple Earn Locked`
- `Launchpool`
- `HODLer Airdrops`
- `Soft Staking`

### Advanced

- `Megadrop`
- `Binance Loan`
- `Dual Investment`

### High Risk

- `On-chain Yields`
- `Smart Arbitrage`

## Product Roles

### Simple Earn Flexible

Use for:

- liquidity-sensitive users
- default BNB parking
- stablecoin idle-fund parking
- passive event eligibility when supported

Avoid overrating it when:

- the user wants maximum yield and accepts lockups

### Simple Earn Locked

Use for:

- higher-yield BNB exposure when the liquidity window is long enough
- users who want more event leverage and accept lock duration

Penalize when:

- the user needs funds inside 7 days
- early redemption would materially hurt fit

### Launchpool

Treat as:

- event overlay on eligible BNB holdings
- BNB-native upside, not a standalone base product

Important:

- support timing and snapshot rules
- when several projects run at once, allocation behavior matters

### HODLer Airdrops

Treat as:

- passive reward bonus for eligible holdings
- lower-complexity event capture

Do not treat as:

- primary yield engine

### Megadrop

Treat as:

- advanced event strategy
- stronger fit for users willing to use Locked BNB and complete tasks

Penalize when:

- the user needs liquidity soon
- the user wants low-friction participation

### Soft Staking

Treat as:

- comparison fallback against `Simple Earn`
- useful when assets remain in Spot and still qualify for passive rewards

### Binance Loan

Treat as:

- liquidity bridge
- alternative to redeeming a yield position

Use only when:

- the user needs cash or liquidity
- collateral rules make sense
- interest cost is explained against preserved yield

### Dual Investment

Treat as:

- advanced tactical product
- suitable only if the user accepts settlement and conversion outcomes

Exclude by default when:

- the user is conservative
- the user needs guaranteed asset continuity

### On-chain Yields

Treat as:

- exploration bucket only
- variable-return opportunity space

Exclude by default when:

- the user asks for safe or simple plans

### Smart Arbitrage

Treat as:

- separate strategy class
- not part of the default BNB yield flow

## Bucket Rules

Every plan should use:

1. `Reserve`
2. `Core Yield`
3. `Event Capture`
4. `Advanced Optional`

### Reserve

Preserve near-term liquidity. Prefer this bucket when the user has short deadlines or uncertainty.

### Core Yield

Use for the main yield allocation. Prefer `Simple Earn Flexible` first, then `Locked` if the liquidity fit is acceptable.

### Event Capture

Use for holdings or routes that preserve eligibility for `Launchpool`, `HODLer Airdrops`, or selected `Megadrop` opportunities.

### Advanced Optional

Use only when the user opts in or the scenario clearly justifies it.

## Default Decision Rules

### If liquidity is needed within 7 days

- prefer `Flexible`
- penalize long `Locked`
- downgrade `Megadrop`
- exclude `Dual Investment` by default
- consider `Binance Loan` only as an explicit advanced alternative

### If the user is conservative

- keep most value in `Reserve` + `Core Yield`
- passive event capture is acceptable
- suppress high-risk products

### If the user wants Binance-native upside

- increase `Launchpool` and `HODLer Airdrops` weight
- consider selected `Megadrop` only if lock and task burden are acceptable

### If the user accepts advanced strategies

- unlock `Binance Loan`, `Dual Investment`, and `On-chain Yields`
- switch explanation style from convenience-first to tradeoff-first

## Event Status

Use these states:

- `confirmed`: verified by official API, official announcement, or official product page
- `candidate`: found via third-party source, not yet officially verified
- `expired`: window has passed
- `watchlist`: likely relevant but not active yet

Never schedule production reminders for `candidate` events unless the user explicitly asks for watchlist behavior.
