# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Render para Instagram desde Rhino (1080 × 1350, formato 4:5)
=====================================================================
1. Copia temporalmente las piezas al documento con material PBR mate (PLA
   real: rugosidad alta, brillo bajo), apaga la vista de Grasshopper,
   enciende cielo + sol con sombras y captura la perspectiva en modo
   Renderizado, a 2× y con fondo transparente.
2. Borra las copias y deja la vista, las luces y Grasshopper como estaban.
3. Compone sobre un fondo de naturaleza desenfocado (renders/fondos/naturaleza,
   o fotos propias en renders/fondos/propias, que se recortan a 4:5 y se
   desenfocan solas): marca, nombre "EDEN · DISEÑO", tres etiquetas de venta
   centradas y pie con el usuario de Instagram. La maceta se apoya en la mesa
   o el suelo del fondo (fondos.json dice a qué altura y si el texto va claro).
Sólo corre dentro de Rhino 8 (RhinoCommon + System.Drawing).

API usada (RhinoCommon / Grasshopper / .NET, estándar en Rhino 8):
    Rhino.Display.ViewCapture, DisplayModeDescription.RenderedId,
    RhinoViewport.SetCameraLocations / ZoomBoundingBox / WorldToClient /
    SetViewProjection, DocObjects.Material.ToPhysicallyBased + PhysicallyBased,
    doc.Lights.Skylight / Sun, doc.Objects.AddMesh / Delete,
    Grasshopper GH_Document.PreviewMode, System.Drawing.
    Si alguna no existe en tu build, ese paso se saltea (el render sale igual).
"""
import os

W, H = 1080, 1350
GREEN = (47, 79, 46)          # verde del catálogo Edén3D
INK = (64, 64, 60)

COLORS = {                    # (maceta RGB, rugosidad)
    "Blanco mate": ((236, 233, 226), 0.62),
    "Terracota": ((196, 112, 82), 0.70),
    "Verde salvia": ((132, 160, 120), 0.66),
    "Rosa pastel": ((232, 170, 178), 0.64),
    "Celeste": ((128, 176, 222), 0.62),
    "Amarillo": ((236, 196, 92), 0.62),
    "Negro mate": ((44, 44, 44), 0.58),
    "Arena": ((214, 196, 166), 0.70),
}


def _pick_view(doc):
    best = None
    for v in doc.Views:
        if v.ActiveViewport.IsPerspectiveProjection:
            if best is None or v.Maximized:
                best = v
    return best or doc.Views.ActiveView


def _try(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


LOG = []


def _log(*a):
    LOG.append(" ".join(str(x) for x in a))


def _luma(bmp):
    """Brillo medio (0-255) de los píxeles opacos, muestreado en una grilla."""
    w, h = bmp.Width, bmp.Height
    tot, n = 0.0, 0
    for j in range(8, 48):
        for i in range(8, 48):
            c = bmp.GetPixel(int(w * i / 56.0), int(h * j / 56.0))
            if c.A > 200:
                tot += 0.299 * c.R + 0.587 * c.G + 0.114 * c.B
                n += 1
    return tot / n if n else 255.0


def _clean_old_lights(doc):
    """Borra SÓLO las luces que creaba el render viejo: direccionales, color
    (255,252,246) e intensidad 0,85 / 0,30 / 0,45. No toca otras luces."""
    import Rhino
    ids = []
    try:
        for i in range(doc.Lights.Count):
            lo = doc.Lights[i]                       # LightObject
            if getattr(lo, "IsDeleted", False):
                continue
            L = getattr(lo, "LightGeometry", lo)
            c = L.Diffuse
            if (L.LightStyle == Rhino.Geometry.LightStyle.WorldDirectional
                    and (c.R, c.G, c.B) == (255, 252, 246)
                    and any(abs(L.Intensity - v) < 1e-3 for v in (0.85, 0.30, 0.45))):
                ids.append(lo.Id)
    except Exception as ex:
        _log("limpiar luces err", ex)
    n = 0
    for gid in ids:
        ok = False
        try:
            ok = doc.Objects.Delete(gid, True)
        except Exception:
            ok = False
        if not ok:                                   # respaldo: por índice
            try:
                for i in range(doc.Lights.Count - 1, -1, -1):
                    if doc.Lights[i].Id == gid:   # LightObject.Id
                        ok = doc.Lights.Delete(i, True)
                        break
            except Exception:
                pass
        n += 1 if ok else 0
    if ids:
        _log("luces viejas borradas", n, "de", len(ids), "quedan", doc.Lights.Count)


SCENE_MATS = {                # escena de la foto: (RGB, brillo 0-1)
    "planta": ((116, 150, 118), 0.30),     # suculenta cerosa
    "piedra": ((228, 222, 210), 0.02),
    "arcilla": ((172, 108, 72), 0.02),
    "tierra": ((88, 64, 46), 0.0),
}

SHOTS = {
    # dir: de la maceta hacia la cámara · lens: mm · passes: muestras de Raytraced
    "portada": {"dir": (-0.42, -1.0, 0.40), "lens": 70.0, "width": 1800, "passes": 90},
    "foto": {"dir": (-0.30, -1.0, 0.22), "lens": 85.0, "width": 1800, "passes": 130},
    "detalle": {"dir": (-0.16, -1.0, 0.26), "lens": 120.0, "width": 1800, "passes": 150,
                "detail": True},
}


def _find_mode(name):
    import Rhino
    for dm in Rhino.Display.DisplayModeDescription.GetDisplayModes():
        if dm.EnglishName.lower() == name.lower():
            return dm
    return None


def _set_uv(mesh, uv):
    """Coordenadas de textura de una vez (para la textura de capas)."""
    import array
    import System
    import Rhino.Geometry as rg
    from System.Runtime.InteropServices import GCHandle, GCHandleType, Marshal
    if not uv or len(uv) != mesh.Vertices.Count:
        return False
    fl = array.array("f", [c for p in uv for c in p])
    arr = System.Array.CreateInstance(rg.Point2f, len(uv))
    h = GCHandle.Alloc(arr, GCHandleType.Pinned)
    try:
        Marshal.Copy(System.Array[System.Single](fl), 0, h.AddrOfPinnedObject(), len(fl))
    finally:
        h.Free()
    mesh.TextureCoordinates.Clear()
    mesh.TextureCoordinates.AddRange(arr)
    return mesh.TextureCoordinates.Count == mesh.Vertices.Count


def _add_material(doc, rgb, shine, bump=None):
    import Rhino
    import System
    sysd = System.Drawing
    m = Rhino.DocObjects.Material()
    m.Name = "Eden3D_render_tmp"
    m.DiffuseColor = sysd.Color.FromArgb(*rgb)
    m.AmbientColor = sysd.Color.FromArgb(*[int(c * 0.35) for c in rgb])
    sp = int(40 + 160 * shine)
    m.SpecularColor = sysd.Color.FromArgb(sp, sp, sp)
    m.Shine = max(0.04, shine) * Rhino.DocObjects.Material.MaxShine
    m.Reflectivity = 0.0
    m.Transparency = 0.0
    if bump and os.path.isfile(bump):
        ok = _try(m.SetBumpTexture, bump)
        _log("textura de capas", bool(ok))
    idx = doc.Materials.Add(m)
    rm = None
    try:
        rm = Rhino.Render.RenderMaterial.CreateBasicMaterial(doc.Materials[idx], doc)
        doc.RenderMaterials.Add(rm)
    except Exception as ex:
        _log("render material err", ex)
        rm = None
    return idx, rm


def _render_cycles(doc, view, width, height, tmp_png, quality="high"):
    """Render real (Rhino Render / Cycles) de la vista con fondo transparente,
    con los comandos -Render / -SaveRenderWindowAs / -CloseRenderWindow.
    Devuelve un Bitmap en memoria o None."""
    import Rhino
    import System
    rs = doc.RenderSettings
    old = {}
    for attr in ("ImageSize", "TransparentBackground", "UseViewportSize", "AntialiasLevel"):
        try:
            old[attr] = getattr(rs, attr)
        except Exception:
            pass
    try:
        _try(setattr, rs, "UseViewportSize", False)
        rs.ImageSize = System.Drawing.Size(int(width), int(height))
        rs.TransparentBackground = True
        doc.RenderSettings = rs
        doc.Views.ActiveView = view
        if os.path.isfile(tmp_png):
            os.remove(tmp_png)
        import time as _t
        t0 = _t.time()
        ok1 = Rhino.RhinoApp.RunScript("_-Render", False)
        ok2 = Rhino.RhinoApp.RunScript('_-SaveRenderWindowAs "%s"' % tmp_png, False)
        ok3 = Rhino.RhinoApp.RunScript("_-CloseRenderWindow", False)
        _log("render Cycles", ok1, ok2, ok3, "%.0f s" % (_t.time() - t0),
             "archivo", os.path.isfile(tmp_png))
        if not os.path.isfile(tmp_png):
            return None
        b0 = System.Drawing.Bitmap(tmp_png)          # copia en memoria (libera el archivo)
        bmp = System.Drawing.Bitmap(b0)
        b0.Dispose()
        _try(os.remove, tmp_png)
        return bmp
    finally:
        rs = doc.RenderSettings
        for attr, val in old.items():
            _try(setattr, rs, attr, val)
        _try(setattr, doc, "RenderSettings", rs)


def capture_shots(pieces, bbox, shots=("portada",), extras=(), bump=None, raytraced=True,
                  tmp_dir=None):
    """Arma la escena una vez y saca varias fotos.
    pieces: [(mesh, rgb, rugosidad[, tipo, uv])] (tipo "maceta" lleva textura de capas)
    extras: [(material, mesh)] planta/piedras/tierra.
    Devuelve [(nombre_toma, bitmap, caja_px)]."""
    import Rhino
    import Rhino.Geometry as rg
    import System
    doc = Rhino.RhinoDoc.ActiveDoc
    view = _pick_view(doc)
    vp = view.ActiveViewport
    info = Rhino.DocObjects.ViewportInfo(vp)
    old_mode = vp.DisplayMode
    added, mats, rmats = [], [], []
    gh_doc = gh_old = None
    restore = []
    out = []
    try:
        _clean_old_lights(doc)
        # 1) objetos temporales con material
        items = []
        for pc in pieces:
            mesh, rgb = pc[0], pc[1]
            kind = pc[3] if len(pc) > 3 else "maceta"
            uv = pc[4] if len(pc) > 4 else None
            items.append((mesh, rgb, 0.05, bump if kind == "maceta" else None, uv))
        for key, mesh in extras:
            rgb, sh = SCENE_MATS.get(key, ((200, 200, 200), 0.05))
            items.append((mesh, rgb, sh, None, None))
        for mesh, rgb, sh, bp, uv in items:
            idx, rm = _add_material(doc, rgb, sh, bp)
            mats.append(idx)
            at = Rhino.DocObjects.ObjectAttributes()
            at.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
            at.MaterialIndex = idx
            at.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
            at.ObjectColor = System.Drawing.Color.FromArgb(*rgb)
            if rm is not None:
                at.RenderMaterial = rm
                rmats.append(rm)
            mm = mesh.DuplicateMesh()
            mm.VertexColors.Clear()
            if bp and uv:
                _log("uv capas", _try(_set_uv, mm, uv))
            mm.Normals.ComputeNormals()
            mm.FaceNormals.ComputeFaceNormals()
            _try(mm.Faces.CullDegenerateFaces)
            mm.Compact()
            gid = doc.Objects.AddMesh(mm, at)
            if gid == System.Guid.Empty:
                _log("no se pudo agregar una malla (válida: %s)" % mm.IsValid)
            else:
                added.append(gid)
        _log("objetos", len(added), "de", len(items))
        # 2) apagar la vista de Grasshopper
        try:
            import Grasshopper
            gh_doc = Grasshopper.Instances.ActiveCanvas.Document
            gh_old = gh_doc.PreviewMode
            gh_doc.PreviewMode = Grasshopper.Kernel.GH_PreviewMode.Disabled
        except Exception:
            gh_doc = None
        # 3) luz de foto: sol cálido de costado-atrás + cielo + sombra en el piso
        mode = _find_mode("Raytraced") if raytraced else None
        sun, sky, gp = doc.Lights.Sun, doc.Lights.Skylight, doc.GroundPlane
        for obj, attr in ((sun, "Enabled"), (sun, "ManualControlOn"), (sun, "Azimuth"),
                          (sun, "Altitude"), (sun, "Intensity"), (sky, "Enabled"),
                          (gp, "Enabled"), (gp, "ShadowOnly"), (gp, "AutoAltitude"),
                          (gp, "Altitude")):
            try:
                restore.append((obj, attr, getattr(obj, attr)))
            except Exception:
                pass
        if mode is not None:
            for obj, attr, val in ((sun, "Enabled", True), (sun, "ManualControlOn", True),
                                   (sun, "Azimuth", 58.0), (sun, "Altitude", 34.0),
                                   (sky, "Enabled", True), (gp, "Enabled", True),
                                   (gp, "ShadowOnly", True), (gp, "AutoAltitude", False),
                                   (gp, "Altitude", bbox.Min.Z)):
                try:
                    setattr(obj, attr, val)
                except Exception as ex:
                    _log("luz", attr, "err", ex)
        else:
            _try(setattr, sun, "Enabled", False)
            _try(setattr, sky, "Enabled", True)
        _log("modo", mode.EnglishName if mode else "Rendered")
        # 4) tomas
        for name in shots:
            cfg = SHOTS.get(name, SHOTS["portada"])
            dm = mode or Rhino.Display.DisplayModeDescription.GetDisplayMode(
                Rhino.Display.DisplayModeDescription.RenderedId)
            vp.DisplayMode = dm
            lens = cfg["lens"]
            if not vp.IsPerspectiveProjection:
                vp.ChangeToPerspectiveProjection(True, lens)
            vp.Camera35mmLensLength = lens
            d = rg.Vector3d(*cfg["dir"])
            d.Unitize()
            box = bbox
            if cfg.get("detail"):
                R = 0.5 * max(bbox.Max.X - bbox.Min.X, bbox.Max.Y - bbox.Min.Y)
                h = bbox.Max.Z - bbox.Min.Z
                box = rg.BoundingBox(rg.Point3d(-0.40 * R, bbox.Min.Y, bbox.Min.Z + 0.40 * h),
                                     rg.Point3d(0.40 * R, -0.25 * R, bbox.Min.Z + 0.97 * h))
            c = box.Center
            diag = max(box.Diagonal.Length, 1.0)
            vp.SetCameraLocations(c, c + d * (diag * 4.0))
            vp.ZoomBoundingBox(box)
            view.Redraw()
            vw, vh = vp.Size.Width, vp.Size.Height
            width = cfg["width"]
            cap = Rhino.Display.ViewCapture()
            cap.Width = width
            cap.Height = int(round(width * vh / float(max(vw, 1))))
            cap.ScaleScreenItems = False
            cap.DrawAxes = False
            cap.DrawGrid = False
            cap.DrawGridAxes = False
            cap.TransparentBackground = True
            if mode is not None:
                try:
                    cap.RealtimeRenderPasses = int(cfg["passes"])
                except Exception as ex:
                    _log("RealtimeRenderPasses no disponible:", ex)
            import time as _t
            t0 = _t.time()
            bmp = None
            if mode is not None:                 # render real con sombras (Cycles)
                vp.DisplayMode = Rhino.Display.DisplayModeDescription.GetDisplayMode(
                    Rhino.Display.DisplayModeDescription.RenderedId)
                view.Redraw()
                try:
                    bmp = _render_cycles(doc, view, cap.Width, cap.Height,
                                         os.path.join(tmp_dir or os.environ.get("TEMP", "."),
                                                      "_eden3d_%s.png" % name),
                                         cfg.get("quality", "high"))
                except Exception as ex:
                    _log("render Cycles err", ex)
                    bmp = None
            if bmp is None:
                bmp = cap.CaptureToBitmap(view)
            lum = _luma(bmp) if bmp is not None else 0.0
            _log("toma", name, "%.1f s" % (_t.time() - t0), "brillo", round(lum, 1))
            if (bmp is None or lum < 45.0) and mode is not None:   # respaldo: Renderizado
                vp.DisplayMode = Rhino.Display.DisplayModeDescription.GetDisplayMode(
                    Rhino.Display.DisplayModeDescription.RenderedId)
                view.Redraw()
                bmp = cap.CaptureToBitmap(view)
                _log("toma", name, "respaldo Renderizado")
            s = width / float(max(vw, 1))
            xs, ys = [], []
            for pt in bbox.GetCorners():
                p2 = vp.WorldToClient(pt)
                xs.append(p2.X * s)
                ys.append(p2.Y * s)
            r = 0.5 * max(bbox.Max.X - bbox.Min.X, bbox.Max.Y - bbox.Min.Y)
            hz = rg.Vector3d(d.X, d.Y, 0.0)
            hz.Unitize()
            pf = rg.Point3d(bbox.Center.X + hz.X * r, bbox.Center.Y + hz.Y * r, bbox.Min.Z)
            yb = vp.WorldToClient(pf).Y * s
            out.append((name, bmp, (min(xs), min(ys), max(xs), yb)))
        return out
    finally:
        for gid in added:
            _try(doc.Objects.Delete, gid, True)
        for idx in mats:
            _try(doc.Materials.DeleteAt, idx)
        for rm in rmats:
            _try(doc.RenderMaterials.Remove, rm)
        for obj, attr, val in reversed(restore):
            _try(setattr, obj, attr, val)
        if gh_doc is not None and gh_old is not None:
            _try(setattr, gh_doc, "PreviewMode", gh_old)
        vp.SetViewProjection(info, True)
        vp.DisplayMode = old_mode
        view.Redraw()


def capture(pieces, bbox, lens=70.0, width=2200):
    """Compatibilidad: una sola toma 'portada' en modo Renderizado."""
    res = capture_shots(pieces, bbox, ("portada",), raytraced=False)
    return res[0][1], res[0][2]


def _rounded(path, x, y, w, h, r):
    path.AddArc(x, y, 2 * r, 2 * r, 180, 90)
    path.AddArc(x + w - 2 * r, y, 2 * r, 2 * r, 270, 90)
    path.AddArc(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, 0, 90)
    path.AddArc(x, y + h - 2 * r, 2 * r, 2 * r, 90, 90)
    path.CloseFigure()


TONE = {"gamma": 1.7,    # GDI+: >1 oscurece medios tonos (verificado en Rhino)
        "contrast": 1.04, "offset": -0.01, "warm": (1.0, 0.992, 0.972)}


TONE_RT = {"gamma": 0.80, "contrast": 1.07, "offset": 0.0, "warm": (1.0, 0.985, 0.95)}
_TONE_NOW = [None]


def _draw_toned(g, bmp, dx, dy, k):
    """Dibuja la captura con curva de tono: medios tonos más profundos (se lee el
    relieve), blancos que no queman y un toque cálido de PLA mate."""
    import System
    from System.Drawing import Rectangle, RectangleF, GraphicsUnit
    from System.Drawing.Imaging import ImageAttributes, ColorMatrix
    try:
        T_ = _TONE_NOW[0] or TONE
        c, t, w = T_["contrast"], T_["offset"], T_["warm"]
        F = System.Single
        rows = [[c * w[0], 0, 0, 0, 0], [0, c * w[1], 0, 0, 0], [0, 0, c * w[2], 0, 0],
                [0, 0, 0, 1, 0], [t, t, t, 0, 1]]
        jag = System.Array[System.Array[F]]([System.Array[F]([F(v) for v in row])
                                             for row in rows])
        ia = ImageAttributes()
        ia.SetGamma(F(T_["gamma"]))
        ia.SetColorMatrix(ColorMatrix(jag))
        dest = Rectangle(int(round(dx)), int(round(dy)), int(round(bmp.Width * k)),
                         int(round(bmp.Height * k)))
        g.DrawImage(bmp, dest, 0, 0, bmp.Width, bmp.Height, GraphicsUnit.Pixel, ia)
    except Exception:
        g.DrawImage(bmp, RectangleF(dx, dy, bmp.Width * k, bmp.Height * k))


def bg_meta(bg_path):
    """Datos del fondo: altura del suelo (fracción de H), tema del texto y
    desenfoque a aplicar (las fotos propias se desenfocan; las generadas ya lo están)."""
    import json
    meta = {"suelo": 0.80, "tema": "auto", "blur": 10}
    try:
        p = os.path.join(os.path.dirname(bg_path), "fondos.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                m = json.load(fh).get(os.path.splitext(os.path.basename(bg_path))[0])
            if m:
                meta.update(m)
    except Exception:
        pass
    return meta


def _draw_background(g, bg_path, blur):
    """Fondo recortado a 4:5 (como 'cover') y desenfocado si hace falta.
    Desenfoque barato y suave: se achica la imagen y se vuelve a agrandar."""
    from System.Drawing import Bitmap, Graphics, Rectangle, RectangleF, GraphicsUnit
    from System.Drawing.Drawing2D import InterpolationMode
    bg = Bitmap(bg_path)
    try:
        sw, sh = float(bg.Width), float(bg.Height)
        s = max(W / sw, H / sh)
        cw, ch = W / s, H / s
        src = RectangleF((sw - cw) / 2.0, (sh - ch) / 2.0, cw, ch)
        if blur and blur > 1:
            f = 1.0 / float(blur)
            sm = Bitmap(max(8, int(W * f)), max(8, int(H * f)))
            gs = Graphics.FromImage(sm)
            gs.InterpolationMode = InterpolationMode.HighQualityBilinear
            gs.DrawImage(bg, RectangleF(0, 0, sm.Width, sm.Height), src, GraphicsUnit.Pixel)
            gs.Dispose()
            # dos pasos de agrandado: más suave que uno solo
            mid = Bitmap(max(16, int(W * f * 3)), max(16, int(H * f * 3)))
            gm = Graphics.FromImage(mid)
            gm.InterpolationMode = InterpolationMode.HighQualityBicubic
            gm.DrawImage(sm, Rectangle(-1, -1, mid.Width + 2, mid.Height + 2))
            gm.Dispose()
            g.DrawImage(mid, Rectangle(-2, -2, W + 4, H + 4))
            sm.Dispose()
            mid.Dispose()
        else:
            g.DrawImage(bg, RectangleF(0, 0, W, H), src, GraphicsUnit.Pixel)
    finally:
        bg.Dispose()


def _region_luma(canvas, y0, y1):
    tot, n = 0.0, 0
    for j in range(8):
        for i in range(12):
            c = canvas.GetPixel(int(W * (i + 0.5) / 12.0),
                                int(y0 + (y1 - y0) * (j + 0.5) / 8.0))
            tot += 0.299 * c.R + 0.587 * c.G + 0.114 * c.B
            n += 1
    return tot / n


def compose(bmp, box, bg_path, title, subtitle, chips, brand="Eden3D", handle="",
            footer="", out_paths=()):
    """Imagen final 1080×1350 guardada en cada ruta de out_paths."""
    import System
    from System.Drawing import (Bitmap, Graphics, Color, Font, FontStyle, SolidBrush,
                                RectangleF, StringFormat, StringAlignment, Pen)
    from System.Drawing.Drawing2D import (SmoothingMode, InterpolationMode, GraphicsPath,
                                          PathGradientBrush, CompositingQuality)
    from System.Drawing.Text import TextRenderingHint
    from System.Drawing.Imaging import ImageFormat

    canvas = Bitmap(W, H)
    g = Graphics.FromImage(canvas)
    g.SmoothingMode = SmoothingMode.AntiAlias
    g.InterpolationMode = InterpolationMode.HighQualityBicubic
    g.CompositingQuality = CompositingQuality.HighQuality
    g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit
    meta = bg_meta(bg_path) if bg_path else {"suelo": 0.775, "tema": "claro", "blur": 0}
    if bg_path and os.path.isfile(bg_path):
        try:
            _draw_background(g, bg_path, float(meta.get("blur", 0) or 0))
        except Exception as ex:
            _log("fondo err", ex)
            g.Clear(Color.FromArgb(226, 232, 214))
    else:
        g.Clear(Color.FromArgb(226, 232, 214))
    tema = meta.get("tema", "auto")
    if tema not in ("claro", "oscuro"):
        tema = "oscuro" if _region_luma(canvas, 30, 260) < 110 else "claro"
    dark = tema == "oscuro"
    # velo suave detrás del encabezado: el título se lee sobre cualquier foto
    from System.Drawing.Drawing2D import LinearGradientBrush
    from System.Drawing import PointF
    veil = (12, 20, 12) if dark else (250, 250, 244)
    vb = LinearGradientBrush(PointF(0, 0), PointF(0, 300), Color.FromArgb(170, *veil),
                             Color.FromArgb(0, *veil))
    g.FillRectangle(vb, 0, 0, W, 300)
    fb = LinearGradientBrush(PointF(0, H - 250), PointF(0, H), Color.FromArgb(0, *veil),
                             Color.FromArgb(115, *veil))
    g.FillRectangle(fb, 0, H - 250, W, 250)

    # producto
    x0, y0, x1, yb = box
    base_y = H * float(meta.get("suelo", 0.80))
    k = min((base_y - 270.0) / max(yb - y0, 1.0), H * 0.50 / max(yb - y0, 1.0),
            W * 0.78 / max(x1 - x0, 1.0))
    dx = W / 2.0 - (x0 + x1) / 2.0 * k
    dy = base_y - yb * k
    sw = (x1 - x0) * k * 0.95
    for grow, alpha in ((1.25, 45), (1.0, 95)):          # sombra de contacto en 2 capas
        path = GraphicsPath()
        path.AddEllipse(RectangleF(W / 2.0 - sw * grow / 2.0, base_y - 22 * grow,
                                   sw * grow, 44 * grow))
        pb = PathGradientBrush(path)
        pb.CenterColor = Color.FromArgb(int(alpha * 1.25), 24, 22, 16)
        pb.SurroundColors = System.Array[Color]([Color.FromArgb(0, 24, 22, 16)])
        g.FillPath(pb, path)
    _draw_toned(g, bmp, dx, dy, k)

    green = SolidBrush(Color.FromArgb(255, *GREEN))
    title_b = SolidBrush(Color.FromArgb(255, 246, 248, 240)) if dark else green
    ink = SolidBrush(Color.FromArgb(235, 226, 232, 220)) if dark else \
        SolidBrush(Color.FromArgb(235, *INK))
    cc = StringFormat()
    cc.Alignment = StringAlignment.Center
    cc.LineAlignment = StringAlignment.Center
    f_brand = Font("Segoe UI", 26, FontStyle.Bold)
    f_title = Font("Segoe UI", 54, FontStyle.Bold)
    f_sub = Font("Segoe UI", 24, FontStyle.Regular)
    f_chip = Font("Segoe UI Semibold", 21, FontStyle.Regular)
    f_foot = Font("Segoe UI", 19, FontStyle.Regular)

    # marca arriba (pastilla verde) + título estilo catálogo
    bw = g.MeasureString(brand, f_brand).Width + 56
    rp = GraphicsPath()
    _rounded(rp, (W - bw) / 2.0, 44, bw, 56, 28)
    g.FillPath(green, rp)
    g.DrawString(brand, f_brand, SolidBrush(Color.White), RectangleF((W - bw) / 2.0, 44, bw, 56), cc)
    g.DrawString(title, f_title, title_b, RectangleF(0, 112, W, 84), cc)
    if subtitle:
        g.DrawString(subtitle, f_sub, ink, RectangleF(0, 192, W, 44), cc)

    # etiquetas de venta: centradas en X e Y dentro de cada pastilla
    ph, gap = 58.0, 16.0
    widths = [g.MeasureString(t, f_chip).Width + 44 for t in chips]
    total = sum(widths) + gap * max(len(chips) - 1, 0)
    if total > W - 60:                                    # no entran: se achica la letra
        f_chip = Font("Segoe UI Semibold", 18, FontStyle.Regular)
        widths = [g.MeasureString(t, f_chip).Width + 36 for t in chips]
        total = sum(widths) + gap * max(len(chips) - 1, 0)
    x = (W - total) / 2.0
    y = H - 168.0
    pill = SolidBrush(Color.FromArgb(230, 255, 255, 255))
    edge = Pen(Color.FromArgb(120, *GREEN), 1.6)
    for t, w in zip(chips, widths):
        rp = GraphicsPath()
        _rounded(rp, x, y, w, ph, ph / 2.0)
        g.FillPath(pill, rp)
        g.DrawPath(edge, rp)
        g.DrawString(t, f_chip, green, RectangleF(x, y, w, ph), cc)
        x += w + gap
    # pie
    foot = "   ·   ".join([s for s in (footer, handle) if s])
    if foot:
        g.DrawString(foot, f_foot, ink, RectangleF(0, H - 86, W, 40), cc)
    g.Dispose()
    done = []
    for p in out_paths:
        dd = os.path.dirname(p)
        if dd and not os.path.isdir(dd):
            os.makedirs(dd)
        canvas.Save(p, ImageFormat.Png)
        done.append(p)
    canvas.Dispose()
    bmp.Dispose()
    return done


def _new_canvas():
    from System.Drawing import Bitmap, Graphics
    from System.Drawing.Drawing2D import SmoothingMode, InterpolationMode, CompositingQuality
    from System.Drawing.Text import TextRenderingHint
    canvas = Bitmap(W, H)
    g = Graphics.FromImage(canvas)
    g.SmoothingMode = SmoothingMode.AntiAlias
    g.InterpolationMode = InterpolationMode.HighQualityBicubic
    g.CompositingQuality = CompositingQuality.HighQuality
    g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit
    return canvas, g


def _small_brand(g, brand):
    from System.Drawing import Color, Font, FontStyle, SolidBrush, RectangleF, StringFormat, \
        StringAlignment
    from System.Drawing.Drawing2D import GraphicsPath
    f = Font("Segoe UI", 19, FontStyle.Bold)
    bw = g.MeasureString(brand, f).Width + 36
    x, y = W - bw - 36, H - 36 - 42
    rp = GraphicsPath()
    _rounded(rp, x, y, bw, 42, 21)
    g.FillPath(SolidBrush(Color.FromArgb(225, *GREEN)), rp)
    cc = StringFormat()
    cc.Alignment = StringAlignment.Center
    cc.LineAlignment = StringAlignment.Center
    g.DrawString(brand, f, SolidBrush(Color.White), RectangleF(x, y, bw, 42), cc)


def _save(canvas, paths):
    from System.Drawing.Imaging import ImageFormat
    done = []
    for p in paths:
        dd = os.path.dirname(p)
        if dd and not os.path.isdir(dd):
            os.makedirs(dd)
        canvas.Save(p, ImageFormat.Png)
        done.append(p)
    return done


def compose_photo(bmp, box, bg_path, brand, out_paths, height_frac=0.56):
    """Foto de producto limpia (sin textos): la maceta apoyada en la mesa del fondo."""
    import System
    from System.Drawing import Color, RectangleF
    from System.Drawing.Drawing2D import GraphicsPath, PathGradientBrush
    canvas, g = _new_canvas()
    meta = bg_meta(bg_path)
    _draw_background(g, bg_path, float(meta.get("blur", 0) or 0))
    x0, y0, x1, yb = box
    base_y = H * float(meta.get("suelo", 0.80))
    k = min(H * height_frac / max(yb - y0, 1.0), W * 0.82 / max(x1 - x0, 1.0))
    dx = W / 2.0 - (x0 + x1) / 2.0 * k
    dy = base_y - yb * k
    sw = (x1 - x0) * k * 0.95
    path = GraphicsPath()
    path.AddEllipse(RectangleF(W / 2.0 - sw / 2.0, base_y - 16, sw, 32))
    pb = PathGradientBrush(path)
    pb.CenterColor = Color.FromArgb(70, 30, 22, 14)
    pb.SurroundColors = System.Array[Color]([Color.FromArgb(0, 30, 22, 14)])
    g.FillPath(pb, path)
    _draw_toned(g, bmp, dx, dy, k)
    _small_brand(g, brand)
    g.Dispose()
    done = _save(canvas, out_paths)
    canvas.Dispose()
    return done


def compose_detail(bmp, bg_path, brand, out_paths):
    """Primer plano: la captura cubre todo el cuadro (se ve la textura de capas)."""
    canvas, g = _new_canvas()
    meta = bg_meta(bg_path)
    _draw_background(g, bg_path, float(meta.get("blur", 0) or 0))
    k = max(W / float(bmp.Width), H / float(bmp.Height)) * 1.02
    dx = W / 2.0 - bmp.Width * k / 2.0
    dy = H / 2.0 - bmp.Height * k / 2.0
    _draw_toned(g, bmp, dx, dy, k)
    _small_brand(g, brand)
    g.Dispose()
    done = _save(canvas, out_paths)
    canvas.Dispose()
    return done


def render_set(pieces, bbox, out_base, bgs, title, subtitle, chips, brand="Eden3D",
               handle="", footer="", extras=(), bump=None, shots=("portada", "foto", "detalle"),
               copies=(), raytraced=True):
    """Carrusel de Instagram: varias tomas de la misma escena.
        out_base  ruta sin extensión: <out_base>_1_portada.png, _2_foto.png, _3_detalle.png
        bgs       {toma: ruta del fondo}
        copies    otras carpetas donde guardar una copia (p. ej. la de exportación)
    Devuelve la lista de archivos escritos."""
    del LOG[:]
    done = []
    try:
        res = capture_shots(pieces, bbox, shots, extras=extras, bump=bump, raytraced=raytraced)
        rt = any("Raytraced" in x for x in LOG)
        _TONE_NOW[0] = TONE_RT if rt else TONE
        for i, (name, bmp, box) in enumerate(res):
            fn = "%s_%d_%s.png" % (os.path.basename(out_base), i + 1, name)
            paths = [os.path.join(os.path.dirname(out_base), fn)] + \
                [os.path.join(c, fn) for c in copies]
            bg = bgs.get(name) or bgs.get("portada")
            try:
                if name == "portada":
                    done += compose(bmp, box, bg, title, subtitle, chips, brand, handle,
                                    footer, paths)
                elif name == "detalle":
                    done += compose_detail(bmp, bg, brand, paths)
                    bmp.Dispose()
                else:
                    done += compose_photo(bmp, box, bg, brand, paths)
                    bmp.Dispose()
            except Exception as ex:
                import traceback
                _log("componer", name, "err", ex, traceback.format_exc()[-400:])
        return done
    finally:
        _TONE_NOW[0] = None
        try:
            p = os.path.join(os.path.dirname(out_base), "_render_log.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("\n".join(LOG))
        except Exception:
            pass


def render_instagram(pieces, bbox, out_paths, bg_path, title, subtitle, chips,
                     brand="Eden3D", handle="", footer=""):
    """Compatibilidad (una sola imagen, modo Renderizado)."""
    del LOG[:]
    bmp, box = capture(pieces, bbox)
    return compose(bmp, box, bg_path, title, subtitle, chips, brand, handle, footer, out_paths)
