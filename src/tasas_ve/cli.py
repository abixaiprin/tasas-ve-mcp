"""Uso rápido en terminal.

  tasas-ve                 → tasas BCV y P2P
  tasas-ve 100 USD VES     → convierte 100 USD a bolívares (BCV)
  tasas-ve 5000 VES USD --p2p
  tasas-ve --json
"""
from __future__ import annotations

import argparse
import json
import sys

from .servicio import Servicio


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tasas-ve", description="Tasas de cambio de Venezuela (BCV y USDT P2P).")
    p.add_argument("monto", nargs="?", type=float)
    p.add_argument("de", nargs="?")
    p.add_argument("a", nargs="?")
    p.add_argument("--p2p", action="store_true", help="usar la referencia P2P en vez del BCV")
    p.add_argument("--json", action="store_true", help="salida en JSON")
    a = p.parse_args(argv)
    s = Servicio()
    try:
        if a.monto is not None:
            if not (a.de and a.a):
                p.error("indica monto, moneda de origen y destino: tasas-ve 100 USD VES")
            r = s.convertir(a.monto, a.de, a.a, "p2p" if a.p2p else "bcv")
            print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else
                  f"{r['monto']:,.2f} {r['de']} = {r['resultado']:,.2f} {r['a']}  (tasa {r['tasa_usada']}, {r['fuente'].upper()})")
            return 0
        datos = {"bcv": s.bcv()}
        try:
            datos["p2p"] = s.p2p()
        except Exception as e:
            datos["p2p"] = {"error": str(e)}
        if a.json:
            print(json.dumps(datos, ensure_ascii=False, indent=2))
            return 0
        for t in datos["bcv"]["tasas"]:
            print(f"BCV  {t['moneda']:<4} Bs {t['bs']:>12,.4f}   {t['obtenida']}")
        for t in datos["p2p"].get("tasas", []):
            print(f"P2P  {t['moneda']:<4} Bs {t['bs']:>12,.4f}   {t['obtenida']}  (referencial)")
        for k in ("bcv", "p2p"):
            if datos[k].get("aviso"):
                print("Aviso:", datos[k]["aviso"], file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
