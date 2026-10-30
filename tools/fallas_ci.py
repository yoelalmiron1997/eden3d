# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""Imprime cada test fallido de los JUnit XML como anotación de GitHub Actions (::error)."""
import os
import sys
import xml.etree.ElementTree as ET


def main(paths):
    n = 0
    for path in paths:
        if not os.path.exists(path):
            print("::error title=Sin reporte::%s no existe" % path)
            continue
        for tc in ET.parse(path).getroot().iter("testcase"):
            for tag in ("failure", "error"):
                el = tc.find(tag)
                if el is None:
                    continue
                msg = (el.get("message") or el.text or "").strip().replace("\n", " ")[:600]
                name = "%s::%s" % (tc.get("classname", ""), tc.get("name", ""))
                print("::error title=%s::%s" % (name[:200], msg.replace("::", ": :")))
                n += 1
    print("%d tests en rojo" % n)


if __name__ == "__main__":
    main(sys.argv[1:])
