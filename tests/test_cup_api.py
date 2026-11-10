from cup_checker.cup_api import appointments_from

# Shape of a real "no availability" response (esito 127).
assert appointments_from({"response": {"listaAppuntamenti": {"appuntamento": []}, "esito": [{"codice": "127"}]}}) == []
assert appointments_from({"response": {"listaAppuntamenti": None}}) == []
assert appointments_from({"response": {"listaAppuntamenti": {"appuntamento": [{"id": 1}]}}}) == [{"id": 1}]
print("ok")

from cup_checker.cup_api import service_names

assert service_names({"prescrizione": [{"listaPrestazioni": {"prestazione": [{"descrizionePrestazione": "VISITA X"}, {}]}}]}) == ["VISITA X"]
assert service_names({"prescrizione": [{"listaPrestazioni": None}]}) == []
print("ok services")

import gzip
import zlib
from cup_checker.cup_api import decode_body

body = b'{"ok": true}'
for raw, enc in [(body, None), (body, "identity"), (gzip.compress(body), "gzip"), (zlib.compress(body), "deflate"),
                 (zlib.compress(body)[2:-4], "deflate")]:
    assert decode_body(raw, enc) == body, enc
import cup_checker.cup_api as cup_api

if cup_api.zstd:
    assert decode_body(cup_api.zstd.compress(body), "zstd") == body
    assert "zstd" in cup_api.PORTAL_HEADERS["Accept-Encoding"]
else:  # Python < 3.14: zstd is neither advertised nor decoded
    assert "zstd" not in cup_api.PORTAL_HEADERS["Accept-Encoding"]

if cup_api.brotli:
    assert decode_body(cup_api.brotli.compress(body), "br") == body
    assert "br" in cup_api.PORTAL_HEADERS["Accept-Encoding"]
else:  # without the package, br is neither advertised nor decoded
    assert "br" not in cup_api.PORTAL_HEADERS["Accept-Encoding"]
try:
    decode_body(body, "compress")
    raise AssertionError("unknown encoding must be rejected")
except RuntimeError:
    pass
print("ok decode")
