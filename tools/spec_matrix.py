# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Matriz de trazabilidad specs ↔ tests (SDD) y gate de calidad.

    python tools/spec_matrix.py --resultados reports/motor.json reports/web.json \
        --out _site/calidad/data.json [--historial-previo URL_o_archivo] \
        [--resumen-md $GITHUB_STEP_SUMMARY] [--strict]

Estados por spec activa: ok (todos sus tests pasan) | falla | sin-tests.
Con --strict sale con código 1 si hay specs activas sin tests o en falla, tests
que referencian specs inexistentes o tests sin spec.
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_specs(folder):
    areas, specs = [], {}
    for path in sorted(glob.glob(os.path.join(folder, "*.yml"))):
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        areas.append({"area": doc["area"], "prefijo": doc["prefijo"],
                      "archivo": os.path.relpath(path, ROOT).replace("\\", "/")})
        for s in doc.get("specs", []):
            if s["id"] in specs:
                raise SystemExit("ID de spec repetido: %s" % s["id"])
            if not s["id"].startswith(doc["prefijo"] + "-"):
                raise SystemExit("%s no usa el prefijo %s" % (s["id"], doc["prefijo"]))
            s = dict(s, area=doc["area"], archivo=areas[-1]["archivo"])
            for k in ("descripcion", "criterio"):
                s[k] = " ".join(str(s.get(k, "")).split())
            specs[s["id"]] = s
    return areas, specs


def load_results(paths):
    suites, tests = [], []
    for p in paths:
        if not os.path.isfile(p):
            suites.append({"suite": os.path.basename(p), "missing": True})
            continue
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        suites.append({k: d[k] for k in ("suite", "seconds", "python", "started")})
        for t in d["tests"]:
            tests.append(dict(t, suite=d["suite"]))
    return suites, tests


def git(*args):
    try:
        return subprocess.check_output(["git"] + list(args), cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def previous_history(src):
    if not src:
        return []
    try:
        if src.startswith("http"):
            with urllib.request.urlopen(src, timeout=15) as r:
                return json.load(r).get("historial", [])
        with open(src, encoding="utf-8") as fh:
            return json.load(fh).get("historial", [])
    except Exception as ex:
        print("historial previo no disponible (%s)" % ex)
        return []


def build(specs_dir, results, prev=None):
    areas, specs = load_specs(specs_dir)
    suites, tests = load_results(results)
    by_spec = {k: [] for k in specs}
    problems = []
    for t in tests:
        if not t["specs"]:
            problems.append({"tipo": "test-sin-spec", "detalle": t["nodeid"]})
        for sid in t["specs"]:
            if sid not in specs:
                problems.append({"tipo": "spec-inexistente", "detalle": "%s en %s" % (sid, t["nodeid"])})
                continue
            by_spec[sid].append(t)
    rows = []
    for sid, s in specs.items():
        ts = by_spec[sid]
        if s.get("estado", "activa") != "activa":
            st = s.get("estado", "pendiente")
            if s.get("estado") == "obsoleta" and ts:
                problems.append({"tipo": "aviso-obsoleta", "detalle": "%s todavía tiene tests" % sid})
        elif not ts:
            st = "sin-tests"
            problems.append({"tipo": "spec-sin-tests", "detalle": sid})
        elif any(t["outcome"] in ("failed", "error") for t in ts):
            st = "falla"
            problems.append({"tipo": "spec-en-falla", "detalle": sid})
        elif all(t["outcome"] == "skipped" for t in ts):
            st = "sin-tests"
            problems.append({"tipo": "spec-sin-tests", "detalle": sid + " (todos salteados)"})
        else:
            st = "ok"
        rows.append(dict(s, status=st, tests=[t["nodeid"] for t in ts],
                         passed=sum(t["outcome"] == "passed" for t in ts),
                         failed=sum(t["outcome"] in ("failed", "error") for t in ts)))
    active = [r for r in rows if r.get("estado", "activa") == "activa"]
    tot = {
        "specs": len(rows), "activas": len(active),
        "cubiertas": sum(r["status"] == "ok" for r in active),
        "en_falla": sum(r["status"] == "falla" for r in active),
        "sin_tests": sum(r["status"] == "sin-tests" for r in active),
        "pendientes": sum(r.get("estado") == "pendiente" for r in rows),
        "tests": len(tests),
        "passed": sum(t["outcome"] == "passed" for t in tests),
        "failed": sum(t["outcome"] in ("failed", "error") for t in tests),
        "skipped": sum(t["outcome"] == "skipped" for t in tests),
        "segundos": round(sum(s.get("seconds", 0) or 0 for s in suites), 1),
    }
    tot["cobertura_specs_pct"] = round(100.0 * tot["cubiertas"] / max(tot["activas"], 1), 1)
    gate = not [p for p in problems if not p["tipo"].startswith("aviso")]
    run = {
        "fecha": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "commit": os.environ.get("GITHUB_SHA", git("rev-parse", "HEAD"))[:10],
        "rama": os.environ.get("GITHUB_REF_NAME", git("rev-parse", "--abbrev-ref", "HEAD")),
        "mensaje": git("log", "-1", "--pretty=%s")[:120],
        "run_url": ("%s/%s/actions/runs/%s" % (os.environ["GITHUB_SERVER_URL"],
                                              os.environ["GITHUB_REPOSITORY"],
                                              os.environ["GITHUB_RUN_ID"])
                    if os.environ.get("GITHUB_RUN_ID") else ""),
        "gate": gate,
    }
    hist = (prev or []) + [dict(run, **{k: tot[k] for k in ("cobertura_specs_pct", "tests",
                                                          "passed", "failed", "segundos")})]
    return {"run": run, "totales": tot, "areas": areas, "specs": rows, "tests": tests,
            "suites": suites, "problemas": problems, "historial": hist[-40:]}


def markdown(d):
    t = d["totales"]
    icon = {"ok": "✅", "falla": "❌", "sin-tests": "⚠️", "pendiente": "🕒", "obsoleta": "🗄️"}
    out = ["## Calidad Eden3D — %s" % ("gate OK ✅" if d["run"]["gate"] else "gate FALLA ❌"), "",
           "Specs activas cubiertas: **%d/%d (%.0f%%)** · tests: %d ✅ %d ❌ %d ⏭️ · %s s"
           % (t["cubiertas"], t["activas"], t["cobertura_specs_pct"], t["passed"], t["failed"],
              t["skipped"], t["segundos"]), "",
           "| Spec | Título | Estado | Tests |", "|---|---|---|---|"]
    for r in d["specs"]:
        out.append("| %s | %s | %s %s | %d/%d |" % (r["id"], r["titulo"], icon.get(r["status"], ""),
                                                   r["status"], r["passed"], len(r["tests"])))
    if d["problemas"]:
        out += ["", "### Problemas"] + ["- **%s**: %s" % (p["tipo"], p["detalle"]) for p in d["problemas"]]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs", default=os.path.join(ROOT, "specs"))
    ap.add_argument("--resultados", nargs="+", default=[os.path.join(ROOT, "reports", "motor.json")])
    ap.add_argument("--out", default=os.path.join(ROOT, "_site", "calidad", "data.json"))
    ap.add_argument("--historial-previo", default=None)
    ap.add_argument("--resumen-md", default=None)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    d = build(a.specs, a.resultados, previous_history(a.historial_previo))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    md = markdown(d)
    if a.resumen_md:
        with open(a.resumen_md, "a", encoding="utf-8") as fh:
            fh.write(md)
    print(md)
    if a.strict and not d["run"]["gate"]:
        sys.exit(1)
