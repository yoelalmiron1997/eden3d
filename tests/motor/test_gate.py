# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""El gate de trazabilidad (tools/spec_matrix.py) sobre casos armados a mano."""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))
import spec_matrix  # noqa: E402

SPECS = """area: Prueba
prefijo: T
specs:
  - {id: T-001, titulo: uno, criterio: c, prioridad: alta, nivel: motor, estado: activa}
  - {id: T-002, titulo: dos, criterio: c, prioridad: baja, nivel: motor, estado: pendiente}
"""


def _run(tmp_path, tests):
    sd = tmp_path / "specs"
    sd.mkdir()
    (sd / "t.yml").write_text(SPECS, encoding="utf-8")
    res = tmp_path / "r.json"
    res.write_text(json.dumps({"suite": "x", "seconds": 1, "python": "3", "started": 0,
                               "tests": tests}), encoding="utf-8")
    return spec_matrix.build(str(sd), [str(res)])


def T(nodeid, specs, outcome="passed"):
    return {"nodeid": nodeid, "name": nodeid, "file": "f", "doc": "", "specs": specs,
            "outcome": outcome, "duration": 0.1, "message": ""}


@pytest.mark.spec("QA-001")
@pytest.mark.parametrize("tests,ok,tipo", [
    ([T("a", ["T-001"])], True, None),                                   # todo cubierto
    ([], False, "spec-sin-tests"),                                       # activa sin test
    ([T("a", ["T-001"]), T("b", ["T-999"])], False, "spec-inexistente"),
    ([T("a", ["T-001"]), T("b", [])], False, "test-sin-spec"),
    ([T("a", ["T-001"], "failed")], False, "spec-en-falla"),
    ([T("a", ["T-001"], "skipped")], False, "spec-sin-tests"),
])
def test_gate(tmp_path, tests, ok, tipo):
    d = _run(tmp_path, tests)
    assert d["run"]["gate"] is ok
    if tipo:
        assert tipo in [p["tipo"] for p in d["problemas"]]
    pend = [s for s in d["specs"] if s["id"] == "T-002"][0]
    assert pend["status"] == "pendiente"          # las pendientes no rompen el build


@pytest.mark.spec("QA-001")
def test_specs_del_repo_validas():
    """Las specs reales cargan: IDs únicos, prefijo correcto y criterio escrito."""
    areas, specs = spec_matrix.load_specs(os.path.join(REPO, "specs"))
    assert len(areas) >= 7 and len(specs) >= 25
    for s in specs.values():
        assert s["criterio"] and s.get("estado") in ("activa", "pendiente", "obsoleta"), s["id"]
        assert s.get("prioridad") in ("alta", "media", "baja"), s["id"]
