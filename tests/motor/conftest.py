# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(os.path.dirname(os.path.dirname(HERE)), "engine")):
    if p not in sys.path:
        sys.path.insert(0, p)
