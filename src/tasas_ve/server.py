"""Servidor MCP: expone las tasas como herramientas para Claude, Cursor, VS Code y otros clientes MCP."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

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


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
