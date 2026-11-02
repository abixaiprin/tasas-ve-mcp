"""Servidor MCP: expone las tasas como herramientas para Claude, Cursor, VS Code y otros clientes MCP."""
from __future__ import annotations

import argparse
import os

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

from .servicio import Servicio

mcp = MCPServer(
    name="tasas-ve",
    title="Tasas de Venezuela",
    description="Tasa oficial del BCV (USD, EUR) y referencia USDT P2P, con conversión de montos.",
    website_url="https://github.com/abixaiprin/tasas-ve-mcp",
    version="0.1.0",
    instructions=(
        "Usa estas herramientas cuando el usuario pregunte por el dólar o el euro en Venezuela, "
        "o quiera convertir montos entre bolívares (VES), dólares (USD), euros (EUR) o USDT. "
        "La fuente 'bcv' es la tasa oficial; 'p2p' es una referencia de mercado no oficial. "
        "Indica siempre la fuente y la fecha de la tasa en tu respuesta."
    ),
)
_svc: Servicio | None = None


def svc() -> Servicio:
    global _svc
    if _svc is None:
        _svc = Servicio()
    return _svc


@mcp.tool(description="Tasa oficial del Banco Central de Venezuela: bolívares por 1 USD y por 1 EUR.")
def tasa_bcv() -> dict:
    return svc().bcv()


@mcp.tool(description="Referencia de mercado USDT/VES: mediana de anuncios P2P. lado='SELL' (venta) o 'BUY' (compra). No es oficial.")
def tasa_p2p(lado: str = "SELL") -> dict:
    return svc().p2p(lado)


@mcp.tool(description="Convierte un monto entre VES, USD, EUR y USDT. fuente='bcv' (oficial) o 'p2p' (mercado).")
def convertir(monto: float, de: str, a: str, fuente: str = "bcv") -> dict:
    return svc().convertir(monto, de, a, fuente)


@mcp.tool(description="Diferencia porcentual entre la tasa oficial BCV del dólar y la referencia USDT P2P.")
def brecha_cambiaria() -> dict:
    return svc().brecha()


# ---------- API REST (para React, Vue, Java, PHP o cualquier app) ----------
CORS = {"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=60"}


def _json(data, status=200):
    return JSONResponse(data, status_code=status, headers=CORS)


@mcp.custom_route("/api/tasas", methods=["GET"])
async def api_tasas(request: Request):
    """GET /api/tasas → BCV y P2P."""
    datos = {"bcv": svc().bcv()}
    try:
        datos["p2p"] = svc().p2p(request.query_params.get("lado", "SELL"))
    except Exception as e:
        datos["p2p"] = {"error": str(e)}
    return _json(datos)


@mcp.custom_route("/api/convertir", methods=["GET"])
async def api_convertir(request: Request):
    """GET /api/convertir?monto=100&de=USD&a=VES&fuente=bcv"""
    q = request.query_params
    try:
        return _json(svc().convertir(float(q["monto"]), q["de"], q["a"], q.get("fuente", "bcv")))
    except KeyError:
        return _json({"error": "Faltan parámetros: monto, de, a"}, 400)
    except ValueError as e:
        return _json({"error": str(e)}, 400)


@mcp.custom_route("/salud", methods=["GET"])
async def salud(request: Request):
    return _json({"ok": True, "servicio": "tasas-ve-mcp"})


def app():
    """App HTTP: MCP remoto en /mcp y API REST en /api/*."""
    return mcp.streamable_http_app(stateless_http=True, json_response=True, host="0.0.0.0")


def main() -> None:
    p = argparse.ArgumentParser(prog="tasas-ve-mcp", description="Servidor MCP y API REST de tasas de Venezuela.")
    p.add_argument("--http", action="store_true", help="servir por HTTP (MCP en /mcp y API en /api) en vez de stdio")
    p.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    a = p.parse_args()
    if a.http:
        import uvicorn
        uvicorn.run(app(), host=a.host, port=a.port)
    else:
        mcp.run("stdio")


if __name__ == "__main__":
    main()
