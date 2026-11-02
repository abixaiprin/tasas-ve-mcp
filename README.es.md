# tasas-ve-mcp

**Las tasas de Venezuela para tu asistente de IA, en una línea.**
Tasa oficial del BCV (USD, EUR) y la referencia de mercado USDT P2P, como servidor MCP, comando de terminal y librería de Python.

[English](README.md) · [Español](README.es.md)

> *Conversación de ejemplo (cifras ilustrativas):*
>
> **Tú:** ¿Cuánto son 250 dólares en bolívares hoy?
> **Claude:** A la tasa oficial del BCV de hoy (Bs 36,59 por USD, 2 nov. 2026), USD 250 = **Bs 9.146,85**. La referencia USDT P2P está en Bs 50,20, una brecha de 37 %.

## Por qué
- **Tu asistente deja de adivinar.** Los modelos no saben la tasa de hoy; esto le da el número real, con fuente y fecha.
- **Rápido y barato.** Una sola llamada pequeña y el cálculo se hace en local: casi no gasta tokens.
- **Sigue funcionando si la fuente se cae.** Guarda el último valor en disco y lo devuelve con un aviso.

## Empezar

Necesitas [uv](https://docs.astral.sh/uv/) (o `pip install tasas-ve-mcp`).

**VS Code** — `.vscode/mcp.json`
```json
{ "servers": { "tasas-ve": { "command": "uvx", "args": ["tasas-ve-mcp"] } } }
```

**Claude Desktop / Cursor**
```json
{ "mcpServers": { "tasas-ve": { "command": "uvx", "args": ["tasas-ve-mcp"] } } }
```

**Terminal**
```bash
uvx --from tasas-ve-mcp tasas-ve
uvx --from tasas-ve-mcp tasas-ve 100 USD VES
uvx --from tasas-ve-mcp tasas-ve 5000 VES USD --p2p
```

## Herramientas
| Herramienta | Qué hace |
|---|---|
| `tasa_bcv` | Tasa oficial del BCV: Bs por 1 USD y 1 EUR |
| `tasa_p2p` | Referencia USDT/VES (mediana de anuncios P2P, venta o compra) |
| `convertir` | Convierte entre VES, USD, EUR y USDT con `bcv` o `p2p` |
| `brecha_cambiaria` | Diferencia (%) entre la tasa oficial y la referencia P2P |

## Fuentes y aviso
- **BCV:** página pública `bcv.org.ve`. Si su certificado TLS no se puede verificar, la respuesta lo indica.
- **P2P:** listado público de anuncios P2P de Binance. Es una **referencia de mercado, no una tasa oficial**. Sin afiliación con el BCV ni con Binance.
- Las tasas son informativas. Verifica la fuente oficial antes de usarlas con fines legales o contables.

## ¿Lo necesitas para tu empresa?
Adapto herramientas como esta a tu negocio: integración con tus sistemas, pagos, asistentes con IA y soporte.
→ [dev-abixai.netlify.app](https://dev-abixai.netlify.app) · dev.abixai.martinez@gmail.com

⭐ **Dale una estrella** si te ahorró tiempo.

## Licencia
MIT © 2026 Abixai Prin
