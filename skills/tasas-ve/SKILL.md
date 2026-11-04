---
name: tasas-ve
description: Venezuelan exchange rates for coding agents. Use when the user asks for the BCV official dollar or euro rate, per-bank rates, the USDT P2P reference, the exchange gap, or to convert amounts between bolívares (VES/Bs), USD, EUR and USDT — or when building software that needs those rates.
---

# tasas-ve: Venezuelan exchange rates (BCV, banks, USDT P2P)

Gives the agent real, dated exchange rates for Venezuela through the **tasas-ve-mcp** MCP server, instead of guessing from training data.

## When to use
- "¿A cuánto está el dólar hoy?", "convert 250 USD to bolívares", "tasa BCV del euro", "¿cuánto paga Banesco por el dólar?", "brecha cambiaria".
- Building apps, invoices, price lists or reports that must show amounts in Bs and USD.

## Setup (once)
Requires [uv](https://docs.astral.sh/uv/). Add the MCP server:

- **Claude Code:** `claude mcp add tasas-ve -- uvx --from git+https://github.com/abixaiprin/tasas-ve-mcp tasas-ve-mcp`
- **Cursor / VS Code / other MCP clients:** add a server named `tasas-ve` with command `uvx` and args `["--from", "git+https://github.com/abixaiprin/tasas-ve-mcp", "tasas-ve-mcp"]`.

If MCP is not available, use the CLI: `uvx --from git+https://github.com/abixaiprin/tasas-ve-mcp tasas-ve 100 USD VES` (`--bancos`, `--p2p`, `--json`).

## Tools
| Tool | Use it for |
|---|---|
| `tasa_bcv()` | Official BCV rate: Bs per 1 USD and per 1 EUR, with date |
| `tasas_bancos()` | Buy/sell rate each bank reports to the BCV, and the average |
| `tasa_p2p(lado="SELL"\|"BUY")` | USDT/VES market reference (median of P2P ads). **Not official** |
| `convertir(monto, de, a, fuente="bcv"\|"p2p")` | Convert between VES, USD, EUR and USDT |
| `brecha_cambiaria()` | % gap between the BCV dollar and the P2P reference |

## Rules
1. Always state the **source and date** of the rate you used ("BCV, 3 nov 2026").
2. Default to the **official BCV rate**. Use P2P only if the user asks, and label it as a market reference, not official.
3. If a tool returns a warning (cached value because the source was down), tell the user the rate may not be today's.
4. Do the math with `convertir`; do not round the rate before converting. Show bolívares with two decimals.
5. This is information, not financial advice.

## Example
User: "¿Cuánto son 250 dólares en bolívares?"
→ call `convertir(250, "USD", "VES")` → "Con la tasa oficial del BCV del 3 nov 2026 (Bs 889,58 por dólar), USD 250 = Bs 222.393,85."
