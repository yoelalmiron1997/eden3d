# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Plugin de trazabilidad (SDD): cada test declara qué spec verifica con
@pytest.mark.spec("AUT-001", ...) y al final se escribe un JSON con el resultado
de cada test y sus specs, que tools/spec_matrix.py convierte en la matriz."""
import json
import os
import platform
import time

import pytest

_RESULTS = {}


def pytest_addoption(parser):
    g = parser.getgroup("eden3d")
    g.addoption("--resultados", default=None,
                help="archivo JSON con el resultado de cada test y sus specs")
    g.addoption("--suite", default="motor", help="nombre de la suite (motor, web)")


def pytest_configure(config):
    config.addinivalue_line("markers", "spec(*ids): specs (IDs de specs/*.yml) que verifica el test")
    config._eden_t0 = time.time()


def _specs(item):
    ids = []
    for m in item.iter_markers("spec"):
        ids.extend(str(a) for a in m.args)
    return sorted(set(ids))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    out = yield
    rep = out.get_result()
    r = _RESULTS.setdefault(item.nodeid, {
        "nodeid": item.nodeid, "name": item.name, "file": item.location[0],
        "doc": (item.function.__doc__ or "").strip().split("\n")[0]
        if getattr(item, "function", None) else "",
        "specs": _specs(item), "outcome": "passed", "duration": 0.0, "message": ""})
    r["duration"] = round(r["duration"] + rep.duration, 3)
    if rep.failed:
        r["outcome"] = "failed" if rep.when == "call" else "error"
        r["message"] = str(rep.longreprtext)[-1500:]
    elif rep.skipped and r["outcome"] == "passed":
        r["outcome"] = "skipped"
        r["message"] = str(rep.longrepr[-1]) if isinstance(rep.longrepr, tuple) else ""


def pytest_sessionfinish(session, exitstatus):
    path = session.config.getoption("--resultados")
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = {
        "suite": session.config.getoption("--suite"),
        "started": session.config._eden_t0,
        "seconds": round(time.time() - session.config._eden_t0, 1),
        "python": platform.python_version(),
        "tests": sorted(_RESULTS.values(), key=lambda r: r["nodeid"]),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
