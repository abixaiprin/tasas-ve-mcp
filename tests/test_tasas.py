import json
from pathlib import Path

import httpx2 as httpx
import pytest

from tasas_ve.fuentes import parsear_bcv, parsear_p2p, obtener_bcv, obtener_p2p, Tasa, _numero
from tasas_ve.servicio import Servicio

FIX = Path(__file__).parent / "fixtures"


def test_numero_formatos():
    assert _numero(" 36,58740000 ") == 36.5874
    assert _numero("1.234,56") == 1234.56
    assert _numero("40.12") == 40.12


def test_parsear_bcv():
    t = {x.moneda: x for x in parsear_bcv((FIX / "bcv.html").read_text())}
    assert t["USD"].bs == 36.5874 and t["EUR"].bs == 42.6153


def test_parsear_bcv_sin_datos():
    with pytest.raises(ValueError):
        parsear_bcv("<html></html>")


def test_parsear_p2p_mediana():
    data = {"data": [{"adv": {"price": p}} for p in ("50.1", "50.3", "49.9", "80.0", "50.2")]}
    t = parsear_p2p(data, "SELL")
    assert t.bs == 50.2 and t.moneda == "USDT"


def test_obtener_con_transporte_simulado():
    def handler(req):
        if req.method == "GET":
            return httpx.Response(200, content=(FIX / "bcv.html").read_bytes())
        body = json.loads(req.content)
        assert body["tradeType"] == "BUY" and body["fiat"] == "VES"
        return httpx.Response(200, json={"data": [{"adv": {"price": "51"}}]})
    c = httpx.Client(transport=httpx.MockTransport(handler))
    assert obtener_bcv(c)[0].bs == 36.5874
    assert obtener_p2p("buy", client=c).bs == 51.0


def _svc(tmp_path, bcv=None, p2p=None, reloj=lambda: 1000.0):
    return Servicio(bcv=bcv or (lambda: [Tasa("bcv", "USD", 40.0, "2026-11-02T12:00:00+00:00"),
                                         Tasa("bcv", "EUR", 44.0, "2026-11-02T12:00:00+00:00")]),
                    p2p=p2p or (lambda lado: Tasa("p2p", "USDT", 50.0, "2026-11-02T12:00:00+00:00")),
                    ruta=tmp_path / "c.json", reloj=reloj)


def test_convertir(tmp_path):
    s = _svc(tmp_path)
    assert s.convertir(10, "USD", "VES")["resultado"] == 400.0
    assert s.convertir(400, "VES", "USD")["resultado"] == 10.0
    assert s.convertir(44, "EUR", "USD")["resultado"] == 48.4
    assert s.convertir(10, "USD", "VES", "p2p")["resultado"] == 500.0
    assert s.brecha()["brecha_pct"] == 25.0


def test_cache_y_ultimo_valor(tmp_path):
    llamadas = {"n": 0}
    t = {"v": 1000.0}
    def bcv():
        llamadas["n"] += 1
        if llamadas["n"] > 1:
            raise ConnectionError("BCV caído")
        return [Tasa("bcv", "USD", 40.0, "x")]
    s = _svc(tmp_path, bcv=bcv, reloj=lambda: t["v"])
    assert s.bcv()["desde_cache"] is False
    assert s.bcv()["desde_cache"] is True and llamadas["n"] == 1      # dentro del TTL no consulta
    t["v"] += 3600                                                   # vence el TTL y la fuente falla
    r = s.bcv()
    assert r["desde_cache"] is True and "último valor" in r["aviso"]
    # persiste en disco: una instancia nueva arranca con el dato guardado
    s2 = _svc(tmp_path, bcv=lambda: (_ for _ in ()).throw(ConnectionError()), reloj=lambda: t["v"])
    assert s2.bcv()["tasas"][0]["bs"] == 40.0


def test_servidor_mcp_expone_herramientas():
    from tasas_ve import server
    import anyio
    nombres = {t.name for t in anyio.run(server.mcp.list_tools)}
    assert {"tasa_bcv", "tasa_p2p", "convertir", "brecha_cambiaria"} <= nombres


def test_llamar_herramienta_por_mcp(tmp_path, monkeypatch):
    from tasas_ve import server
    import anyio
    monkeypatch.setattr(server, "_svc", _svc(tmp_path))
    r = anyio.run(server.mcp.call_tool, "convertir", {"monto": 25, "de": "USD", "a": "VES"})
    texto = json.dumps(r, default=str)
    assert "1000.0" in texto


def test_api_rest(tmp_path, monkeypatch):
    from starlette.testclient import TestClient
    from tasas_ve import server
    monkeypatch.setattr(server, "_svc", _svc(tmp_path))
    with TestClient(server.app()) as c:
        r = c.get("/api/convertir", params={"monto": 10, "de": "USD", "a": "VES"})
        assert r.status_code == 200 and r.json()["resultado"] == 400.0
        assert r.headers["access-control-allow-origin"] == "*"
        assert c.get("/api/convertir").status_code == 400
        t = c.get("/api/tasas").json()
        assert t["bcv"]["tasas"][0]["moneda"] == "USD" and t["p2p"]["tasas"][0]["bs"] == 50.0
        assert c.get("/salud").json()["ok"] is True
