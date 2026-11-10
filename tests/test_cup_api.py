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
