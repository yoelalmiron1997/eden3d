# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D STUDIO — Componente Grasshopper (Rhino 8, "Python 3 Script")
===================================================================
Todo con listas desplegables y botones. El catálogo de diseños está en
eden3d/colecciones/catalogo_eden3d.json (agregás diseños ahí).

ENTRADAS (nombre exacto; si una entrada está vacía, el componente le crea
sola su lista o su botón la primera vez que corre):
    lib_path       Panel con la carpeta eden3d
    diseno         lista: diseños del catálogo
    modo           lista: Todos (catálogo) | Autorriego con rosca | Plato inclinado
                   con rosca | Plato apoyado | Sin plato | Plato oculto ... | Inserto
    drenaje        lista: Todos (catálogo) | Hojas | Circular | Ranuras | Sin drenaje
    tamano         lista: M | Mini | S | L | XL | Todos (catálogo)
    tex_count, tex_pitch, tex_amp, tex_duty, tex_wob, ondas, amp_ondas
                   (opcionales) sliders del patrón; 0 = valor del diseño. Si
                   tocás alguno, el nombre exportado lleva el ajuste
                   (p. ej. ...-HOJAS-N36P14). Cualquier otra entrada con el
                   nombre de un parámetro del motor también se aplica.
    vista          lista: Armado | Despiece | Corte | Base (marca) | Galería
    quality        lista: preview | normal   (sólo la vista; exportar siempre usa normal)
    exportar       botón: exporta el diseño elegido en todas las versiones elegidas
    exportar_todo  botón: exporta TODO el catálogo con esas versiones
    out_dir        (opcional) carpeta de exportación; por defecto MACETAS_EDEN3D/exportadas
    fondo          lista: fondos de naturaleza desenfocados (eden3d/renders/fondos/naturaleza).
                   Tus fotos: ponelas en eden3d/renders/fondos/propias (JPG o PNG, cualquier
                   tamaño): se recortan a 4:5 y se desenfocan solas. Aparecen como "propia: ..."
    render_ig      botón: carrusel para Instagram de lo que se ve (con suculenta, piedritas y
                   luz de sol, en modo Raytraced): <SKU>_IG_1_portada (con textos),
                   _2_foto (foto limpia en la mesa) y _3_detalle (primer plano de las capas).
                   render_auto hace sólo la portada.
    tests          botón: autotest del autorriego del diseño elegido (S y M): luz bajo la
                   maceta, agua que llega a la tierra, vueltas de rosca, holguras,
                   sólidos cerrados y tiempos. El resultado queda en el reporte.
    color          lista: color del PLA para el render (Blanco mate, Terracota, ...)
    render_auto    interruptor: si está en True, cada cambio de diseño genera su
                   render solo (MACETAS_EDEN3D/renders/instagram/<SKU>_IG.png).
                   Al exportar también se guarda <SKU>_IG.png en la carpeta del diseño.
SALIDAS: pot (maceta/s), plate (plato/s e insertos), agua (opcional: el agua
         del plato lleno, en azul translúcido), report (texto), out
         La primera vez se crean dos "Custom Preview" (terracota y gris) para
         verlos con luz y sombra; la vista propia del componente se apaga.

"Todos (catálogo)" usa la matriz "export" del catálogo (por defecto: Plato
apoyado + Autorriego con rosca × Hojas + Circular × M). Nombres de archivo:
    Eden3D-<DISEÑO>-<TAMAÑO>-<MODO>-<DRENAJE>
Cada pieza lleva la marca "Eden3D" grabada en la base.

API de Grasshopper usada para crear las listas/botones (estándar en Rhino 8):
    Grasshopper.Kernel.Special.GH_ValueList / GH_ValueListItem / GH_ButtonObject,
    GH_Document.ScheduleSolution, IGH_Param.AddSource. Si algo de esto fallara
    en tu versión, el reporte lo dice y podés crear la lista a mano.
"""
import sys
import os
import json
import time
import importlib

import Rhino.Geometry as rg

pot = plate = agua = None
report = ""
out = ""

TODOS = "Todos (catálogo)"
COLORS = {"MACETA": (196, 112, 82), "PLATO": (58, 55, 53), "INSERTO": (120, 150, 105),
          "AGUA": (60, 150, 230)}


def _input_names():
    try:
        return set(p.Name for p in ghenv.Component.Params.Input)   # noqa: F821
    except Exception:
        return None


_INPUTS = _input_names()


def opt(name):
    if _INPUTS is not None and name not in _INPUTS:
        return None
    v = globals().get(name, None)
    if isinstance(v, str):
        v = v.strip()
    return v


def resolve_lib(path):
    raw = str(path or "")
    p = raw.replace("\r", "").replace("\n", "").strip().strip('"').strip("'").strip()
    p = "".join(ch for ch in p if ord(ch) >= 32 and ch not in "‪‫‬‎‏")
    p = os.path.normpath(os.path.expandvars(os.path.expanduser(p))) if p else p
    if p.lower().endswith(".py"):
        p = os.path.dirname(p)
    for c in (p, os.path.dirname(p), os.path.join(p, "eden3d")):
        if c and os.path.isfile(os.path.join(c, "eden_core.py")):
            return c
    raise IOError("No encuentro eden_core.py en: %r" % raw)


def _cache():
    c = getattr(sys, "_eden3d_cache", None)
    if c is None:
        c = {}
        sys._eden3d_cache = c
    return c


def _to_rhino_fast(V, F):
    """Copia los arreglos de una vez (memoria fijada + Marshal.Copy) en vez de
    agregar vértice por vértice: ~20× más rápido con mallas de 250 mil puntos."""
    import array
    import System
    from System.Runtime.InteropServices import GCHandle, GCHandleType, Marshal
    fv = array.array("d", [c for v in V for c in v])
    fi = array.array("i", [i for f in F for i in (f[0], f[1], f[2], f[2])])
    pts = System.Array.CreateInstance(rg.Point3d, len(V))   # Point3d: única sobrecarga que elige pythonnet
    fcs = System.Array.CreateInstance(rg.MeshFace, len(F))
    for dst, src, typ in ((pts, fv, System.Double), (fcs, fi, System.Int32)):
        net = System.Array[typ](src)
        h = GCHandle.Alloc(dst, GCHandleType.Pinned)
        try:
            Marshal.Copy(net, 0, h.AddrOfPinnedObject(), len(src))
        finally:
            h.Free()
    m = rg.Mesh()
    m.Vertices.AddVertices(pts)
    m.Faces.AddFaces(fcs)
    # control: mismo conteo y mismos datos en las puntas
    if m.Vertices.Count != len(V) or m.Faces.Count != len(F):
        raise ValueError("conteo")
    for i in (0, len(V) - 1):
        q = m.Vertices[i]
        if abs(q.X - V[i][0]) + abs(q.Y - V[i][1]) + abs(q.Z - V[i][2]) > 1e-3:
            raise ValueError("vértice")
    for i in (0, len(F) - 1):
        f = m.Faces[i]
        if (f.A, f.B, f.C) != tuple(F[i]):
            raise ValueError("cara")
    return m


def to_rhino(V, F, rgb=None):
    m = None
    if getattr(sys, "_eden3d_fastmesh", True):
        try:
            m = _to_rhino_fast(V, F)
        except Exception as ex:
            sys._eden3d_fastmesh = False      # no anduvo en esta versión: modo seguro
            sys._eden3d_fastmesh_err = repr(ex)[:200]
            m = None
    if m is None:
        m = rg.Mesh()
        for x, y, z in V:
            m.Vertices.Add(x, y, z)
        for a, b, c in F:
            m.Faces.AddFace(a, b, c)
    m.Normals.ComputeNormals()
    m.Compact()
    return m


def place_pieces(res, view, dx=0.0, dy=0.0):
    """[(nombre, V, F)] ya ubicadas según la vista."""
    A = res["report"].get("assembly") or {}
    mode = res["params"].get("mode", "pot")
    out_ = []
    pcs = ec.pieces(res)
    lift = 0.0
    if mode in ("hidden_tray", "screw_tray", "screw_dish", "screw_dish_sw", "saucer"):
        lift = A.get("pot_bottom_z_mm", 0.0) - A.get("pot_drop_on_seat_mm", 0.0)
    for k, (nm, V, F) in enumerate(pcs):
        oz = 0.0
        ox = 0.0
        if nm == "MACETA":
            oz = lift
        if nm == "INSERTO":
            oz = res["params"]["floor"] + A.get("reservoir_h_mm", 0) - A.get("insert_drop_on_rim_mm", 0)
        if view == "Despiece":
            if nm == "MACETA" and len(pcs) > 1:
                oz += A.get("tray_h_mm", 30.0) + 45.0
            if nm == "INSERTO":
                oz += res["params"]["height"] + 30.0
        if view.startswith("Base"):
            zmax = max(v[2] for v in V)
            w = max(v[0] for v in V) - min(v[0] for v in V)
            ox = sum(max(vv[0] for vv in pp[1]) - min(vv[0] for vv in pp[1]) + 20.0
                     for pp in pcs[:k])
            V = [(x + ox, -y, zmax - z) for x, y, z in V]
            F = [(a, c, b) for a, b, c in F]       # el giro invierte la orientación
            oz = 0.0
        if view == "Corte":
            V, F = half_cut(V, F)
        if oz or dx or dy:
            V = [(x + dx, y + dy, z + oz) for x, y, z in V]
        out_.append((nm, V, F))
    return out_


def half_cut(V, F, y0=0.0137):
    """Corte real por el plano y = y0: se quita la mitad delantera (y < y0) y
    se tapa la sección (cara plana mirando a la vista Frontal)."""
    V = list(V)
    keep, segs, cache = [], [], {}

    def cut_pt(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in cache:
            (xa, ya, za), (xb, yb, zb) = V[a], V[b]
            t = (y0 - ya) / (yb - ya)
            V.append((xa + t * (xb - xa), y0, za + t * (zb - za)))
            cache[k] = len(V) - 1
        return cache[k]
    for f in F:
        ins = [V[i][1] >= y0 for i in f]
        n_in = sum(ins)
        if n_in == 3:
            keep.append(f)
            continue
        if n_in == 0:
            continue
        # rotar para que el vértice "solitario" quede primero
        for r_ in range(3):
            g_ = f[r_:] + f[:r_]
            i_ = ins[r_:] + ins[:r_]
            if (n_in == 1 and i_[0]) or (n_in == 2 and not i_[0]):
                break
        a, b, c = g_
        p_ab, p_ac = cut_pt(a, b), cut_pt(a, c)
        if n_in == 1:                       # queda el triángulo de 'a'
            keep.append((a, p_ab, p_ac))
            segs.append((p_ab, p_ac))
        else:                               # 'a' afuera: queda el cuadrilátero b-c
            keep.append((p_ab, b, c))
            keep.append((p_ab, c, p_ac))
            segs.append((p_ac, p_ab))
    # tapa: unir segmentos en contornos y triangular (earcut del motor)
    try:
        nxt = {}
        for s0, s1 in segs:
            nxt[s0] = s1
        loops, seen = [], set()
        for st in nxt:
            if st in seen:
                continue
            lp, cur = [], st
            while cur not in seen and cur in nxt:
                seen.add(cur)
                lp.append(cur)
                cur = nxt[cur]
            if len(lp) >= 3 and cur == st:
                loops.append(lp)
        import eden_floor as ef_
        import eden_font as fn_
        pts2 = [[(V[i][0], V[i][2]) for i in lp] for lp in loops]
        depth = [sum(1 for j, q in enumerate(pts2) if j != k and fn_._inside(pts2[k][0], q))
                 for k in range(len(pts2))]
        for k, lp in enumerate(loops):
            if depth[k] % 2:
                continue
            holes = [(pts2[j], loops[j]) for j in range(len(loops))
                     if depth[j] == depth[k] + 1 and fn_._inside(pts2[j][0], pts2[k])]
            for t in ef_.earcut(pts2[k], lp, holes):
                (ax_, _, az_), (bx_, _, bz_), (cx_, _, cz_) = V[t[0]], V[t[1]], V[t[2]]
                ny_ = (bz_ - az_) * (cx_ - ax_) - (bx_ - ax_) * (cz_ - az_)
                keep.append(t if ny_ < 0 else (t[0], t[2], t[1]))   # normal hacia -Y
    except Exception:
        pass
    return V, keep


def scene_extras(res, view):
    """Planta, piedritas y tierra para la foto (sólo vista Armado), en caché."""
    if view != "Armado" or not res:
        return [], None
    import eden_escena
    reload_if_changed(eden_escena)
    A = res["report"].get("assembly") or {}
    lift = A.get("pot_bottom_z_mm", 0.0) - A.get("pot_drop_on_seat_mm", 0.0) \
        if A.get("pot_bottom_z_mm") is not None else 0.0
    key = ("_escena", os.path.getmtime(eden_escena.__file__),
           json.dumps(res["params"], sort_keys=True))
    c = _cache()
    if key not in c:
        V = [(x, y, z + lift) for x, y, z in res["vertices"]]
        ex = [(k, to_rhino(Vs, Fs)) for k, Vs, Fs in eden_escena.build(V)]
        uv = eden_escena.layer_uv(res["vertices"])
        c[key] = (ex, uv)
    return c[key]


def schedule_ig(cat, design, m0, d0, s0, ovr, view, meshes, platos, lib_path, od, also_export,
                res=None, shots=("portada",)):
    """Programa las fotos para cuando Rhino termine de dibujar (evento Idle)."""
    import Rhino
    import Rhino.Geometry as rg_
    import eden_render as er0
    er0 = importlib.reload(er0)                 # Rhino guarda el módulo viejo en memoria
    bb = rg_.BoundingBox.Empty
    for m in meshes + platos:
        bb.Union(m.GetBoundingBox(True))
    root = os.path.dirname(os.path.dirname(lib_path))          # MACETAS_EDEN3D
    brand = cat.get("brand", "Eden3D")
    ig = cat.get("instagram", {})
    if view == "Galería":
        sku = "%s-GALERIA-%s-%s" % (brand, ec.mode_code(m0), ec.drain_code(d0))
        title = "CATÁLOGO DE MACETAS"
        subtitle = "%d diseños disponibles" % len(cat["designs"])
    else:
        sku = ec.sku(design["code"], s0, m0, d0, brand) + ec.override_tag(ovr)
        title = "EDEN · %s" % design["code"]
        subtitle = design.get("name", "")
    chips = list((ig.get("chips") or {}).get(m0) or SELL_CHIPS.get(m0) or SELL_CHIPS["pot"])
    if d0 == "none" and len(chips) > 1:
        chips[1] = "Cubremaceta"
    col_name = opt("color") or ig.get("color", "Blanco mate")
    rgb, rough = er0.COLORS.get(col_name, er0.COLORS["Blanco mate"])
    extras, uv = scene_extras(res, view) if len(meshes) == 1 else ([], None)
    pieces = [(m, rgb, rough, "maceta", uv) for m in meshes] + \
             [(m, tuple(int(c * 0.93) for c in rgb), rough, "plato") for m in platos]
    out_base = os.path.join(root, "renders", "instagram", sku + "_IG")
    copies = []
    if also_export and view != "Galería":
        copies.append(os.path.join(od, "%s-%s" % (brand, design["code"])))
    fondo = opt("fondo") or (FONDOS[0] if FONDOS else "")
    bg = FONDO_PATH.get(fondo) or (FONDO_PATH.get(FONDOS[0]) if FONDOS else "")
    bgs = {"portada": bg, "foto": FONDO_PATH.get("interior_sol", bg),
           "detalle": FONDO_PATH.get("interior_sol_detalle", bg)}
    bump = os.path.join(lib_path, "renders", "texturas", "capas_fdm2.png")
    if view == "Galería" or not extras:
        shots = ("portada",)

    def on_idle(sender, e):
        try:
            Rhino.RhinoApp.Idle -= sys._eden3d_idle
        except Exception:
            pass
        try:
            import eden_render
            er = importlib.reload(eden_render)
            t0 = time.time()
            done = er.render_set(pieces, bb, out_base, bgs, title, subtitle, chips, brand,
                                 ig.get("handle", ""), ig.get("footer", ""), extras=extras,
                                 bump=bump, shots=shots, copies=copies,
                                 raytraced=len(shots) > 1)   # auto: vista rápida
            sys._eden3d_ig_last = "%d foto(s) en %.0f s: %s  (%s)" % (
                len(done), time.time() - t0, "  +  ".join(os.path.basename(x) for x in done),
                time.strftime("%H:%M:%S"))
        except Exception as ex_:
            import traceback
            sys._eden3d_ig_last = "FALLÓ: %s %s" % (ex_, traceback.format_exc()[-300:])
    try:
        Rhino.RhinoApp.Idle -= sys._eden3d_idle
    except Exception:
        pass
    sys._eden3d_idle = on_idle
    Rhino.RhinoApp.Idle += on_idle


def build_cached(p):
    key = json.dumps(p, sort_keys=True)
    c = _cache()
    if key in c:
        return c[key], True
    res = core.build_pot(p)
    if len(c) > 30:
        c.clear()
    c[key] = res
    return res, False


# ---------------------------------------------------------------------------
# listas y botones automáticos
# ---------------------------------------------------------------------------
def control_spec(cat):
    return {
        "diseno": ("list", ["%s · %s" % (d["code"], d.get("name", "")) for d in cat["designs"]]),
        "modo": ("list", [TODOS] + [lab for _, lab, _ in ec.MODES]),
        "drenaje": ("list", [TODOS] + [lab for _, lab, _, _ in ec.DRAINS]),
        "tamano": ("list", ["M", "Mini", "S", "L", "XL", TODOS]),
        "vista": ("list", ["Armado", "Despiece", "Corte", "Base (marca)", "Galería"]),
        "quality": ("list", ["preview", "normal"]),
        "exportar": ("button", None),
        "exportar_todo": ("button", None),
        "tests": ("button", None),
        # patrón: 0 = usar el valor del diseño
        "tex_count": ("slider", (0, 80, 0)),
        "tex_pitch": ("slider", (0, 60, 1)),
        "tex_amp": ("slider", (0, 4, 1)),
        "tex_duty": ("slider", (0, 0.8, 2)),
        "tex_wob": ("slider", (0, 1.5, 2)),
        "ondas": ("slider", (0, 60, 0)),
        "amp_ondas": ("slider", (0, 4, 1)),
        # render para Instagram
        "fondo": ("list", FONDOS or ["bosque_mesa"]),
        "render_ig": ("button", None),
        "render_auto": ("toggle", None),
        "color": ("list", ["Blanco mate", "Terracota", "Verde salvia", "Rosa pastel", "Celeste",
                           "Amarillo", "Negro mate", "Arena"]),
    }


SELL_CHIPS = {   # textos de venta por modo (se pueden cambiar en el catálogo: instagram.chips)
    "screw_dish_sw": ["Autorriego personalizable", "Drenaje incluido", "Material 3D ecológico"],
    "screw_dish": ["Plato enroscable", "Drenaje incluido", "Material 3D ecológico"],
    "saucer": ["Con plato a juego", "Drenaje incluido", "Material 3D ecológico"],
    "pot": ["Diseño exclusivo", "Drenaje incluido", "Material 3D ecológico"],
    "hidden_tray": ["Plato oculto", "Drenaje incluido", "Material 3D ecológico"],
    "screw_tray": ["Plato oculto enroscable", "Drenaje incluido", "Material 3D ecológico"],
    "self_watering": ["Autorriego con mecha", "Depósito de agua", "Material 3D ecológico"],
}


FONDOS = []
FONDO_PATH = {}
IMG_EXT = (".jpg", ".jpeg", ".png")


def list_fondos(lib_path):
    """Fondos generados (en el orden de fondos.json) + fotos propias."""
    names, paths = [], {}
    nat = os.path.join(lib_path, "renders", "fondos", "naturaleza")
    order = []
    try:
        with open(os.path.join(nat, "fondos.json"), encoding="utf-8") as fh:
            order = list(json.load(fh))
    except Exception:
        pass
    if os.path.isdir(nat):
        files = {os.path.splitext(f)[0]: f for f in os.listdir(nat)
                 if f.lower().endswith(IMG_EXT)}
        for nm in order + sorted(set(files) - set(order)):
            if nm in files:
                names.append(nm)
                paths[nm] = os.path.join(nat, files[nm])
    own = os.path.join(lib_path, "renders", "fondos", "propias")
    if os.path.isdir(own):
        for f in sorted(os.listdir(own)):
            if f.lower().endswith(IMG_EXT):
                nm = "propia: " + os.path.splitext(f)[0]
                names.append(nm)
                paths[nm] = os.path.join(own, f)
    return names, paths


if getattr(sys, "_eden3d_fm_ver", None) != 3:      # nueva versión del cargador rápido
    sys._eden3d_fastmesh = True
    sys._eden3d_fm_ver = 3
_MTIMES = getattr(sys, "_eden3d_mtimes", None)
if _MTIMES is None:
    _MTIMES = sys._eden3d_mtimes = {}


def reload_if_changed(mod):
    """Recarga el módulo sólo si su archivo cambió (conserva sus cachés).
    Devuelve True si lo recargó."""
    f = getattr(mod, "__file__", None)
    try:
        mt = os.path.getmtime(f)
    except Exception:
        importlib.reload(mod)
        return True
    if _MTIMES.get(f) != mt:
        importlib.reload(mod)
        _MTIMES[f] = mt
        return True
    return False


PATTERN_KEYS = ("tex_count", "tex_pitch", "tex_amp", "tex_duty", "tex_wob", "ondas", "amp_ondas")


def read_overrides():
    """Sliders del patrón conectados y distintos de 0 + cualquier entrada con
    el nombre exacto de un parámetro del motor."""
    ov = {}
    for k in PATTERN_KEYS:
        v = opt(k)
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v > 0:
            ov[k] = int(round(v)) if k in ("tex_count", "ondas") else round(v, 3)
    skip = set(control_spec({"designs": []})) | {"lib_path", "out_dir"}
    for k, dflt in core.DEFAULTS.items():
        if k in skip or k in ov or k in ("waves", "model_id", "mode", "quality"):
            continue
        v = opt(k)
        if v is None or v == "":
            continue
        try:
            if isinstance(dflt, bool):
                v = str(v).strip().lower() in ("1", "true", "si", "sí")
            elif isinstance(dflt, int):
                v = int(round(float(v)))
            elif isinstance(dflt, float):
                v = float(v)
            else:
                v = str(v).strip()
        except ValueError:
            continue
        ov[k] = v
    return ov


def ensure_controls(cat, notes):
    try:
        comp = ghenv.Component                                         # noqa: F821
        doc = comp.OnPingDocument()
    except Exception:
        return
    if doc is None:
        return
    try:
        import System
        from Grasshopper.Kernel import GH_Document
        from Grasshopper.Kernel.Special import (GH_ValueList, GH_ValueListItem,
                                                GH_ValueListMode, GH_ButtonObject,
                                                GH_NumberSlider, GH_BooleanToggle)
        from Grasshopper.GUI.Base import GH_SliderAccuracy
    except Exception as ex:
        notes.append("No pude cargar la API de Grasshopper para crear listas: %s" % ex)
        return
    spec = control_spec(cat)
    todo, refresh = [], []
    for prm in comp.Params.Input:
        nm = prm.Name
        if nm not in spec:
            continue
        if prm.SourceCount == 0:
            todo.append((prm, nm))
        elif spec[nm][0] == "list":
            src = prm.Sources[0]
            if isinstance(src, GH_ValueList):
                names = [it.Name for it in src.ListItems]
                if names != spec[nm][1]:
                    refresh.append((src, nm))
    if not todo and not refresh:
        return

    def cb(d):
        cb_ = comp.Attributes.Bounds
        order = list(spec)
        for k, (prm, nm) in enumerate(todo):
            kind, items = spec[nm]
            if kind == "list":
                obj = GH_ValueList()
                obj.CreateAttributes()
                obj.ListMode = GH_ValueListMode.DropDown
                obj.ListItems.Clear()
                for it in items:
                    obj.ListItems.Add(GH_ValueListItem(it, '"%s"' % it))
            elif kind == "slider":
                lo, hi, dec = items
                obj = GH_NumberSlider()
                obj.CreateAttributes()
                obj.Slider.Minimum = System.Decimal(lo)
                obj.Slider.Maximum = System.Decimal(hi)
                obj.Slider.DecimalPlaces = dec
                obj.Slider.Type = GH_SliderAccuracy.Integer if dec == 0 else GH_SliderAccuracy.Float
                obj.SetSliderValue(System.Decimal(0))
            elif kind == "toggle":
                obj = GH_BooleanToggle()
                obj.CreateAttributes()
                obj.Value = False
            else:
                obj = GH_ButtonObject()
                obj.CreateAttributes()
            obj.NickName = nm
            row = order.index(nm)                  # columna ordenada a la izquierda
            obj.Attributes.Pivot = System.Drawing.PointF(cb_.Left - 330,
                                                         cb_.Top + 10 + 34 * row)
            d.AddObject(obj, False)
            prm.AddSource(obj)
        for src, nm in refresh:
            sel = src.FirstSelectedItem.Name if src.FirstSelectedItem else None
            src.ListItems.Clear()
            for it in spec[nm][1]:
                src.ListItems.Add(GH_ValueListItem(it, '"%s"' % it))
            if sel in spec[nm][1]:
                src.SelectItem(spec[nm][1].index(sel))
            src.ExpireSolution(False)
        comp.ExpireSolution(False)
    doc.ScheduleSolution(5, GH_Document.GH_ScheduleDelegate(cb))
    if todo:
        notes.append("Creé los controles: %s" % ", ".join(nm for _, nm in todo))


def ensure_preview(notes):
    """Dos Custom Preview con color (maceta terracota, plato gris) conectados
    a las salidas pot y plate; se apaga la vista roja/verde del componente."""
    try:
        comp = ghenv.Component                                         # noqa: F821
        doc = comp.OnPingDocument()
    except Exception:
        return
    if doc is None:
        return
    outs = {p.Name: p for p in comp.Params.Output}
    if "pot" not in outs or "plate" not in outs:
        return
    if outs["pot"].Recipients.Count > 0 and not comp.Hidden:
        comp.Hidden = True
    names = [n for n in ("pot", "plate", "agua") if n in outs]
    if all(outs[n].Recipients.Count > 0 for n in names):
        return
    try:
        import System
        from Grasshopper.Kernel import GH_Document
        from Grasshopper.Kernel.Components import GH_CustomPreviewComponent
        from Grasshopper.Kernel.Special import GH_ColourSwatch
    except Exception as ex:
        notes.append("No pude crear la vista con color automáticamente (%s). Conectá a "
                     "mano un Custom Preview a 'pot' y otro a 'plate'." % ex)
        return

    def cb(d):
        b = comp.Attributes.Bounds
        for k, (name, rgb) in enumerate((("pot", COLORS["MACETA"]), ("plate", COLORS["PLATO"]),
                                         ("agua", COLORS["AGUA"]))):
            if name not in outs or outs[name].Recipients.Count > 0:
                continue
            sw = GH_ColourSwatch()
            sw.CreateAttributes()
            sw.SwatchColour = System.Drawing.Color.FromArgb(150 if name == "agua" else 255, *rgb)
            sw.NickName = "color " + name
            sw.Attributes.Pivot = System.Drawing.PointF(b.Right + 40, b.Bottom + 30 + 70 * k)
            cp = GH_CustomPreviewComponent()
            cp.CreateAttributes()
            cp.NickName = "vista " + name
            cp.Attributes.Pivot = System.Drawing.PointF(b.Right + 170, b.Bottom + 20 + 70 * k)
            d.AddObject(sw, False)
            d.AddObject(cp, False)
            cp.Params.Input[0].AddSource(outs[name])
            cp.Params.Input[1].AddSource(sw)
        comp.Hidden = True
        comp.ExpireSolution(False)
    doc.ScheduleSolution(5, GH_Document.GH_ScheduleDelegate(cb))
    notes.append("Creé la vista con color (2 Custom Preview).")


# ---------------------------------------------------------------------------
try:
    lib_path = resolve_lib(lib_path)                                   # noqa: F821
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)
    import eden_floor
    import eden_font
    import eden_surface
    import eden_core
    import eden_catalog
    T0 = time.time()
    changed = False
    for mod in (eden_floor, eden_font, eden_surface):
        changed = reload_if_changed(mod) or changed
    if changed:                               # un cambio abajo obliga a recargar arriba
        _MTIMES.pop(getattr(eden_core, "__file__", ""), None)
        _MTIMES.pop(getattr(eden_catalog, "__file__", ""), None)
    changed = reload_if_changed(eden_core) or changed
    changed = reload_if_changed(eden_catalog) or changed
    core, ec = eden_core, eden_catalog
    if changed:                               # motor nuevo: resultados viejos fuera
        _cache().clear()
    FONDOS, FONDO_PATH = list_fondos(lib_path)

    notes = []
    cat_path = os.path.join(lib_path, "colecciones", "catalogo_eden3d.json")
    cat = ec.load_catalog(cat_path)
    ensure_controls(cat, notes)
    ensure_preview(notes)

    design = ec.find_design(cat, (opt("diseno") or "").split(" · ")[0])
    mode_sel = ec.label_to_mode(opt("modo")) if opt("modo") and opt("modo") != TODOS else None
    drain_sel = ec.label_to_drain(opt("drenaje")) if opt("drenaje") and opt("drenaje") != TODOS else None
    size_in = opt("tamano") or "M"
    size_sel = size_in if size_in in ec.SIZES else None
    view = opt("vista") or "Armado"
    qual = opt("quality") or "preview"
    want_ig = bool(opt("render_ig")) or bool(opt("render_auto")) or bool(opt("exportar"))
    if want_ig and view != "Galería":
        qual = "normal"                    # el render usa la malla buena
    ovr = read_overrides()
    matrix = ec.export_matrix(cat, mode_sel, drain_sel, size_sel)
    m0, d0, s0 = matrix[0]
    od = core.clean_path(opt("out_dir") or "") or \
        os.path.join(os.path.dirname(os.path.dirname(lib_path)), "exportadas")

    lines = []
    T_BUILD = T_MESH = 0.0
    agua_m = None
    # ---------------- tests -------------------------------------------------
    if opt("tests"):
        import eden_selftest
        reload_if_changed(eden_selftest)
        tl = []
        eden_selftest.run(cat, [design["code"]], log=tl.append)
        sys._eden3d_testlog = tl + ["(%s)" % time.strftime("%H:%M:%S")]
    # ---------------- exportar --------------------------------------------
    if opt("exportar") or opt("exportar_todo"):
        codes = None if opt("exportar_todo") else [design["code"]]
        t0 = time.time()
        log = []
        ec.run(cat_path, od, codes=codes, mode=mode_sel, drain=drain_sel, size=size_sel,
               log=log.append, overrides=ovr)
        lines.append("EXPORTACIÓN (%.0f s) -> %s" % (time.time() - t0, od))
        lines += ["  " + x for x in log]
        lines.append("Índice: %s" % os.path.join(od, "Eden3D_indice.csv"))
        lines.append("")
        sys._eden3d_lastlog = lines[:] + ["(%s)" % time.strftime("%H:%M")]

    # ---------------- vista -----------------------------------------------
    meshes, platos = [], []
    if view == "Galería":
        designs = cat["designs"]
        t0 = time.time()
        built = 0
        for i, d in enumerate(designs):
            p = ec.design_params(cat, d, s0, m0, d0, "preview", ovr)
            res, hit = build_cached(p)
            built += 0 if hit else 1
            if not res["report"].get("valid"):
                lines.append("%-10s INVÁLIDO: %s" % (d["code"], res["report"]["errors"][:1]))
                continue
            gx, gy = (i % 5) * 190.0, -(i // 5) * 210.0
            for nm, V, F in place_pieces(res, "Armado", gx, gy):
                (meshes if nm == "MACETA" else platos).append(to_rhino(V, F))
        lines.insert(0, "GALERÍA · %s · %s · %s  (%d diseños, %d calculados en %.0f s)"
                     % (ec.mode_code(m0), ec.drain_code(d0), s0, len(designs), built,
                        time.time() - t0))
        for r_ in range(0, len(designs), 5):
            lines.append("  fila %d: %s" % (r_ // 5 + 1,
                                            ", ".join(d["code"] for d in designs[r_:r_ + 5])))
    else:
        p = ec.design_params(cat, design, s0, m0, d0, qual, ovr)
        t_ = time.time()
        res, hit = build_cached(p)
        T_BUILD = time.time() - t_
        rep = res["report"]
        lines.insert(0, "%s  ->  %s%s" % (p["model_id"], "VÁLIDA" if rep.get("valid") else "INVÁLIDA",
                                          "  (memoria)" if hit else ""))
        lines += ["ERROR: " + e for e in rep["errors"]]
        lines += ["Aviso: " + w for w in rep["warnings"]]
        if rep.get("valid"):
            t_ = time.time()
            mc = _cache().setdefault("_meshes", {})
            mkey = (json.dumps(p, sort_keys=True), view)
            if mkey in mc:                         # mallas de Rhino ya armadas
                meshes, platos = [list(x) for x in mc[mkey]]
            else:
                for nm, V, F in place_pieces(res, view):
                    (meshes if nm == "MACETA" else platos).append(to_rhino(V, F))
                if len(mc) > 8:
                    mc.clear()
                mc[mkey] = (list(meshes), list(platos))
            T_MESH = time.time() - t_
            A = rep.get("assembly") or {}
            lines.append("Maceta: %s g PLA · %s ml de tierra · %s mm" %
                         (rep.get("mass_g_PLA_100pct"), rep.get("soil_capacity_ml"),
                          " × ".join(str(x) for x in rep.get("bbox_mm", []))))
            for pt in res.get("parts") or []:
                lines.append("%s: %s g PLA · %s mm" % (pt["name"], pt["report"].get("mass_g_PLA_100pct"),
                                                      " × ".join(str(x) for x in pt["report"].get("bbox_mm", []))))
            if "water_min_wet_ml" in A:
                lines.append("AUTORRIEGO: la maceta queda a %.1f mm del piso del plato. "
                             "Con %s ml el agua entra por los drenajes y moja la tierra; "
                             "plato lleno = %s ml (%.0f mm de tierra en remojo)."
                             % (A["water_gap_under_pot_mm"], A["water_min_wet_ml"],
                                A["water_reservoir_ml"], A["water_over_soil_mm"]))
            elif A.get("water_reservoir_ml"):
                lines.append("Agua: %s ml" % A["water_reservoir_ml"])
            if A.get("thread"):
                lines.append("Rosca: %s" % A["thread"])
            if "dish_inner_r0_mm" in A and view in ("Armado", "Corte"):
                Vw, Fw = core.water_mesh(res)
                if view == "Corte":
                    Vw, Fw = half_cut(Vw, Fw)
                agua_m = [to_rhino(Vw, Fw)] if Vw else []
            b = rep.get("brand")
            lines.append("Marca: %s" % ("%s grabada %.1f mm de alto, %.1f mm de profundidad"
                                         % (b["text"], b["cap_h_mm"], b["depth_mm"]) if b else "no entró"))
            lines.append("Drenaje: %s agujeros, %s%% del fondo" % (rep.get("drain_holes"),
                                                                  rep.get("drain_area_pct_floor")))
        dp_ = design["params"]
        if dp_.get("tex_type", "none") not in ("none", ""):
            lines.append("Patrón del diseño (%s): tex_count %s · tex_pitch %s · tex_amp %s · "
                         "tex_duty %s · tex_wob %s" % (dp_["tex_type"], dp_.get("tex_count", "-"),
                         dp_.get("tex_pitch", "-"), dp_.get("tex_amp", "-"),
                         dp_.get("tex_duty", "-"), dp_.get("tex_wob", "-")))
        rw = [w for w in dp_.get("waves", []) if w.get("type", "radial") == "radial"]
        if rw:
            lines.append("Ondas del diseño: ondas %s · amp_ondas %s" % (rw[0].get("count"),
                                                                     rw[0].get("amp")))
        if ovr:
            lines.append("AJUSTES ACTIVOS: %s  (0 en el slider = valor del diseño)" %
                         ", ".join("%s=%s" % kv for kv in sorted(ovr.items())))
    if not (opt("exportar") or opt("exportar_todo")) and getattr(sys, "_eden3d_lastlog", None):
        lines.append("")
        lines.append("ÚLTIMA EXPORTACIÓN %s" % sys._eden3d_lastlog[-1])
        lines += sys._eden3d_lastlog[1:-1]
    lines.append("")
    lines.append("Al exportar salen %d versión(es) por diseño:" % len(matrix))
    for m, d, s in matrix:
        lines.append("  " + ec.sku(design["code"], s, m, d, cat.get("brand", "Eden3D"))
                     + ec.override_tag(ovr))
    # ---------------- render Instagram (después de dibujar) -----------------
    try:
        ig_key = "%s|%s|%s|%s|%s" % (lines[0] if lines else "", view, opt("fondo"),
                                     sorted(ovr.items()), opt("color"))
        auto_new = bool(opt("render_auto")) and getattr(sys, "_eden3d_ig_key", None) != ig_key
        if (opt("render_ig") or auto_new or opt("exportar")) and (meshes or platos):
            full = bool(opt("render_ig") or opt("exportar"))   # botón: carrusel completo
            schedule_ig(cat, design, m0, d0, s0, ovr, view, meshes, platos, lib_path, od,
                        bool(opt("exportar")), res=locals().get("res"),
                        shots=("portada", "foto", "detalle") if full else ("portada",))
            sys._eden3d_ig_key = ig_key
    except Exception as ex_:
        lines.append("Render Instagram: no se pudo programar (%s)" % ex_)
    last = getattr(sys, "_eden3d_ig_last", None)
    if last:
        lines.append("")
        lines.append("RENDER INSTAGRAM: %s" % last)
    tl = getattr(sys, "_eden3d_testlog", None)
    if tl:
        lines.append("")
        lines.append("TESTS %s" % tl[-1])
        lines += ["  " + x for x in tl[:-1]]
    lines += notes
    pot = meshes
    plate = platos
    agua = agua_m or None
    lines.insert(1, "Tiempos: motor %.1f s · mallas %.1f s · total %.1f s%s"
                 % (T_BUILD, T_MESH, time.time() - T0, "" if getattr(sys, "_eden3d_fastmesh", True)
                    else " (mallas en modo seguro: %s)" % getattr(sys, "_eden3d_fastmesh_err", "")))
    report = "\n".join(lines)
    out = report

except Exception as ex:
    import traceback
    report = "FALLO: %s\n%s" % (ex, traceback.format_exc())
    out = report
