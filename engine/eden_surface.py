# -*- coding: utf-8 -*-
# © 2026 Eden3D — Yoel Almirón. Todos los derechos reservados. Ver LICENSE.
"""
EDEN3D — Superficie visible: low poly y texturas
================================================
OBJETIVO
    Modificar SOLO la piel exterior visible de la maceta. La pared interior se
    sigue calculando desde la superficie base lisa (eden_core), así las facetas
    y los relieves nunca adelgazan ni pliegan la pared.

LOW POLY  (facetas planas reales)
    lowpoly_cols     facetas alrededor (0 = desactivado; 6–40)
    lowpoly_rows     bandas en altura (2–20)
    lowpoly_stagger  True = filas desfasadas media faceta (triángulos)
    lowpoly_jitter   desorden radial de los vértices, mm (0 = regular)
    lowpoly_seed     semilla del desorden
    Cada faceta es un plano exacto: el radio se obtiene intersectando el rayo
    horizontal (θ, z) con el triángulo 3D de la grilla gruesa.

TEXTURAS  (relieve SIEMPRE hacia afuera, 0 … tex_amp mm)
    tex_type   "none" | "rope" (soga) | "knit" (tejido) | "stone" (piedra)
               | "bubbles" (burbujas)
    tex_amp    profundidad del relieve, mm
    tex_count  repeticiones alrededor (soga, tejido, burbujas)
    tex_pitch  paso vertical, mm (soga, tejido, burbujas)
    tex_scale  tamaño de grano de la piedra, mm
    tex_seed   semilla (piedra)
"""
import math
import random

TAU = 2.0 * math.pi


# ---------------------------------------------------------------------------
# LOW POLY
# ---------------------------------------------------------------------------
class LowPoly(object):
    """Grilla gruesa triangulada sobre la superficie base."""

    def __init__(self, p, rb, H):
        self.cols = max(3, int(p.get("lowpoly_cols", 0)))
        self.rows = max(1, int(p.get("lowpoly_rows", 6)))
        stagger = bool(p.get("lowpoly_stagger", True))
        jit = float(p.get("lowpoly_jitter", 0.0) or 0.0)
        rnd = random.Random(int(p.get("lowpoly_seed", 1)))
        self.H = H
        self.dv = H / float(self.rows)
        # anillos de vértices gruesos: (u, P3d) con u en unidades de faceta
        self.rings = []
        for j in range(self.rows + 1):
            z = j * self.dv
            off = 0.5 * (j % 2) if stagger else 0.0
            # desorden por vértice REAL (i mod cols): los vértices repetidos en la
            # costura deben ser idénticos o las facetas no cierran
            jit_j = [rnd.uniform(-jit, jit) if 0 < j < self.rows else 0.0
                     for _ in range(self.cols)]
            base = {}
            for i in range(self.cols):
                u = i + off
                th = TAU * u / self.cols
                r = rb(th, z) + jit_j[i]
                base[i] = (r, th)
            ring = []
            for i in range(-1, self.cols + 2):
                r, th0 = base[i % self.cols]
                u = i + off
                th = TAU * u / self.cols
                ring.append((u, (r * math.cos(th), r * math.sin(th), z)))
            self.rings.append(ring)
        # triángulos por banda (zipper en u) + índice por celda entera de u
        self.bands = []
        for j in range(self.rows):
            A, B = self.rings[j], self.rings[j + 1]
            tris = []
            ia = ib = 0
            while ia < len(A) - 1 or ib < len(B) - 1:
                if ia < len(A) - 1 and (ib >= len(B) - 1 or A[ia + 1][0] <= B[ib + 1][0]):
                    tris.append(((A[ia][0], 0.0, A[ia][1]), (A[ia + 1][0], 0.0, A[ia + 1][1]),
                                 (B[ib][0], 1.0, B[ib][1])))
                    ia += 1
                else:
                    tris.append(((A[ia][0], 0.0, A[ia][1]), (B[ib + 1][0], 1.0, B[ib + 1][1]),
                                 (B[ib][0], 1.0, B[ib][1])))
                    ib += 1
            bins = {}
            for t_i, tri in enumerate(tris):
                us = [v[0] for v in tri]
                for b in range(int(math.floor(min(us))), int(math.floor(max(us))) + 1):
                    bins.setdefault(b, []).append(t_i)
            self.bands.append((tris, bins))
        self._adjacency()

    def _locate(self, th, z):
        """(índice de banda, índice de triángulo, u, v) del punto (θ, z)."""
        zc = min(max(z, 0.0), self.H)
        j = min(int(zc / self.dv), self.rows - 1)
        v = (zc - j * self.dv) / self.dv
        u = (th % TAU) / TAU * self.cols
        tris, bins = self.bands[j]
        best = None
        for t_i in bins.get(int(math.floor(u)), []):
            (u1, v1, _), (u2, v2, _), (u3, v3, _) = tris[t_i]
            det = (v2 - v3) * (u1 - u3) + (u3 - u2) * (v1 - v3)
            if abs(det) < 1e-12:
                continue
            l1 = ((v2 - v3) * (u - u3) + (u3 - u2) * (v - v3)) / det
            l2 = ((v3 - v1) * (u - u3) + (u1 - u3) * (v - v3)) / det
            worst = min(l1, l2, 1.0 - l1 - l2)
            if best is None or worst > best[0]:
                best = (worst, t_i)
            if worst >= -1e-9:
                break
        return j, best[1]

    @staticmethod
    def _plane(tri):
        P1, P2, P3 = tri[0][2], tri[1][2], tri[2][2]
        ax, ay, az = P2[0] - P1[0], P2[1] - P1[1], P2[2] - P1[2]
        bx, by, bz = P3[0] - P1[0], P3[1] - P1[1], P3[2] - P1[2]
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / L, ny / L, nz / L
        cx = (P1[0] + P2[0] + P3[0]) / 3.0
        cy = (P1[1] + P2[1] + P3[1]) / 3.0
        if nx * cx + ny * cy < 0:                     # normal hacia afuera
            nx, ny, nz = -nx, -ny, -nz
        return (nx, ny, nz), nx * P1[0] + ny * P1[1] + nz * P1[2]

    @staticmethod
    def _hit(plane, th, z, w):
        (nx, ny, nz), d = plane
        den = nx * math.cos(th) + ny * math.sin(th)
        if abs(den) < 1e-9:
            return None
        return (d - w - nz * z) / den

    def _adjacency(self):
        """Vecinos por ARISTA de cada triángulo (misma banda y bandas contiguas)
        y si esa arista es convexa. Se calcula una vez."""
        allt = []
        for j, (tris, _) in enumerate(self.bands):
            for t_i, t in enumerate(tris):
                allt.append((j, t_i, t))
        edge_map = {}
        for j, t_i, t in allt:
            ids = [self._key(v[2]) for v in t]
            for e in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[0], ids[2])):
                edge_map.setdefault(tuple(sorted(e)), []).append((j, t_i))
        self.adj = {}
        worst_concave = 1.0
        for e, owners in edge_map.items():
            if len(owners) != 2:
                continue
            (ja, ta), (jb, tb) = owners
            A, B = self.bands[ja][0][ta], self.bands[jb][0][tb]
            pA, pB = self._plane(A), self._plane(B)
            far = [v[2] for v in B if self._key(v[2]) not in e]
            (nx, ny, nz), d = pA
            convex = (nx * far[0][0] + ny * far[0][1] + nz * far[0][2] - d) < 1e-9 if far else True
            self.adj.setdefault((ja, ta), []).append((pB, convex))
            self.adj.setdefault((jb, tb), []).append((pA, convex))
            if not convex:
                c = sum(pA[0][k] * pB[0][k] for k in range(3))
                worst_concave = min(worst_concave, c)
        # hoyos (vértices cóncavos con varias facetas): margen chico extra
        self.w_comp = min(1.25, 1.0 + 0.5 * (1.0 / max(worst_concave, 0.6) - 1.0))

    @staticmethod
    def _key(P):
        return (round(P[0], 6), round(P[1], 6), round(P[2], 6))

    def inner_radius(self, th, z, w):
        """Radio de la pared interior a espesor w con facetas exactas.
        El plano de la faceta que contiene el punto se corre w hacia adentro;
        con cada faceta vecina por arista se toma el mínimo si la arista es
        convexa y el máximo si es cóncava (offset de un poliedro; continuo
        porque en la arista ambos planos coinciden). Los vértices hundidos
        (sólo con desorden) llevan un margen chico extra (w_comp)."""
        zc = min(max(z, 1e-6), self.H - 1e-6)
        q = zc / self.dv
        if abs(q - round(q)) < 1e-7:                   # justo en el borde de banda
            zc -= 1e-5
        j, t_i = self._locate(th, zc)
        T = self.bands[j][0][t_i]
        wc = w * self.w_comp
        r = self._hit(self._plane(T), th, z, wc)
        if r is None:
            return None
        for pN, convex in self.adj.get((j, t_i), []):
            rn = self._hit(pN, th, z, wc)
            if rn is None or rn <= 0:
                continue
            r = min(r, rn) if convex else max(r, rn)
        return r

    def radius(self, th, z):
        zc = min(max(z, 0.0), self.H)
        j = min(int(zc / self.dv), self.rows - 1)
        v = (zc - j * self.dv) / self.dv
        u = (th % TAU) / TAU * self.cols
        tris, bins = self.bands[j]
        best = None
        for t_i in bins.get(int(math.floor(u)), []):
            (u1, v1, P1), (u2, v2, P2), (u3, v3, P3) = tris[t_i]
            det = (v2 - v3) * (u1 - u3) + (u3 - u2) * (v1 - v3)
            if abs(det) < 1e-12:
                continue
            l1 = ((v2 - v3) * (u - u3) + (u3 - u2) * (v - v3)) / det
            l2 = ((v3 - v1) * (u - u3) + (u1 - u3) * (v - v3)) / det
            l3 = 1.0 - l1 - l2
            worst = min(l1, l2, l3)
            if best is None or worst > best[0]:
                best = (worst, P1, P2, P3)
            if worst >= -1e-9:
                break
        _, P1, P2, P3 = best
        # plano del triángulo ∩ rayo horizontal desde el eje
        ax, ay, az = P2[0] - P1[0], P2[1] - P1[1], P2[2] - P1[2]
        bx, by, bz = P3[0] - P1[0], P3[1] - P1[1], P3[2] - P1[2]
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        dx, dy = math.cos(th), math.sin(th)
        den = nx * dx + ny * dy
        if abs(den) < 1e-12:
            return math.hypot(P1[0], P1[1])
        return (nx * P1[0] + ny * P1[1] + nz * (P1[2] - z)) / den


# ---------------------------------------------------------------------------
# TEXTURAS
# ---------------------------------------------------------------------------
def _frac(x):
    return x - math.floor(x)


def _hash3(i, j, k, seed):
    h = (i * 374761393 + j * 668265263 + k * 2147483647 + seed * 144665) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def _vnoise(x, y, z, seed):
    xi, yi, zi = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))
    xf, yf, zf = x - xi, y - yi, z - zi
    sx = xf * xf * (3 - 2 * xf)
    sy = yf * yf * (3 - 2 * yf)
    sz = zf * zf * (3 - 2 * zf)
    acc = 0.0
    for dx in (0, 1):
        wx = sx if dx else 1 - sx
        for dy in (0, 1):
            wy = sy if dy else 1 - sy
            for dz in (0, 1):
                wz = sz if dz else 1 - sz
                acc += wx * wy * wz * _hash3(xi + dx, yi + dy, zi + dz, seed)
    return acc


def p_round(x):
    return int(math.floor(x + 0.5))


class Texture(object):
    TYPES = ("none", "rope", "knit", "stone", "bubbles",
             "lattice", "arches", "wavy_v", "wavy_h")
    # costillas en relieve (fotos de tendencia):
    #   lattice  rombos: dos familias de hélices cruzadas
    #   arches   arcos/ojivas: dos familias senoidales espejadas
    #   wavy_v   costillas verticales onduladas (serpenteantes)
    #   wavy_h   costillas horizontales onduladas (olas); flanco inferior más suave

    def __init__(self, p, r_nominal):
        self.t = str(p.get("tex_type", "none") or "none").strip().lower()
        if self.t not in self.TYPES:
            raise ValueError("tex_type desconocido: %s (usar %s)" % (self.t, ", ".join(self.TYPES)))
        self.amp = float(p.get("tex_amp", 1.2) or 0.0)
        self.count = max(3, int(p.get("tex_count", 24)))
        self.pitch = max(1.5, float(p.get("tex_pitch", 8.0)))
        self.scale = max(2.0, float(p.get("tex_scale", 10.0)))
        self.seed = int(p.get("tex_seed", 7))
        self.duty = min(0.8, max(0.12, float(p.get("tex_duty", 0.3) or 0.3)))
        self.wob = float(p.get("tex_wob", 0.3) or 0.0)
        self.r0 = r_nominal
        self.active = self.t != "none" and self.amp > 0

    def height(self, th, z):
        """Relieve en [0, 1] (se multiplica por tex_amp)."""
        t = self.t
        if t == "rope":
            # cordones helicoidales: perfil redondeado, surco en V
            s = _frac(self.count * th / TAU + z / self.pitch)
            return math.sqrt(max(0.0, math.sin(math.pi * s)))
        if t == "knit":
            # punto jersey: columnas de "V" (dos lóbulos inclinados por puntada)
            cx = _frac(self.count * th / TAU) - 0.5
            s = _frac(z / self.pitch + 1.1 * abs(cx))
            lobe = max(0.0, math.sin(math.pi * s)) ** 0.7
            col = max(0.0, math.sin(math.pi * (cx + 0.5))) ** 0.35
            return lobe * col
        if t == "stone":
            x = self.r0 * math.cos(th) / self.scale
            y = self.r0 * math.sin(th) / self.scale
            zz = z / self.scale
            v = (0.62 * _vnoise(x, y, zz, self.seed)
                 + 0.28 * _vnoise(2.1 * x, 2.1 * y, 2.1 * zz, self.seed + 1)
                 + 0.10 * _vnoise(4.3 * x, 4.3 * y, 4.3 * zz, self.seed + 2))
            return min(1.0, max(0.0, (v - 0.25) / 0.6))
        if t == "bubbles":
            # burbujas en tresbolillo; perfil coseno (flancos <= ~35°) y
            # mitad inferior estirada para no generar voladizos
            row = z / self.pitch
            j = math.floor(row)
            best = 0.0
            for jj in (j - 1, j, j + 1, j + 2):
                off = 0.5 * (int(jj) % 2)
                cx = (math.floor(self.count * th / TAU - off + 0.5) + off)
                for c in (cx - 1, cx, cx + 1):
                    du = (self.count * th / TAU - c) * (TAU * self.r0 / self.count)
                    dv = (row - jj) * self.pitch
                    if dv < 0:
                        dv /= 1.6
                    rad = 0.42 * min(self.pitch, TAU * self.r0 / self.count)
                    d = math.hypot(du, dv) / rad
                    if d < 1.0:
                        best = max(best, 0.5 * (1 + math.cos(math.pi * d)))
            return best
        if t in ("lattice", "arches", "wavy_v", "wavy_h"):
            u = self.count * th / TAU
            zp = z / self.pitch
            if t == "lattice":
                return max(self._rib(u + zp), self._rib(u - zp))
            if t == "arches":
                g = self.wob * math.sin(math.pi * zp)
                return max(self._rib(u + g), self._rib(u - g))
            if t == "wavy_v":
                return self._rib(u + self.wob * math.sin(TAU * zp))
            return self._rib(zp + self.wob * math.sin(self.count * th), low_soft=True)
        return 0.0

    def _rib(self, s, low_soft=False):
        """Costilla redondeada de ancho `duty` (fracción del período), alto 1.
        Perfil cos(πx/2): lomo redondo y flanco de pendiente finita (no hay
        paredes verticales). low_soft: el flanco inferior es 1,7× más ancho
        (costillas horizontales: voladizo suave)."""
        d = s - math.floor(s + 0.5)                # [-0.5, 0.5)
        half = self.duty / 2.0
        if low_soft and d < 0:
            half *= 1.7
        x = abs(d) / half
        if x >= 1.0:
            return 0.0
        return math.cos(0.5 * math.pi * x)

    def resolution(self):
        """(muestras angulares mínimas, paso vertical máximo)"""
        if not self.active:
            return 0, 99.0
        if self.t == "stone":
            n = int(TAU * self.r0 / (self.scale / 6.0))
            return n, self.scale / 6.0
        if self.t in ("lattice", "arches", "wavy_v", "wavy_h"):
            per = int(min(32, max(16, math.ceil(6.0 / self.duty))))
            dz = self.duty * self.pitch / 6.0
            if self.t in ("arches", "wavy_v") and self.wob > 0:
                dz = min(dz, self.duty * self.pitch / (TAU * self.wob) / 6.0)
            if self.t == "wavy_h":
                return max(self.count * 24, 360), max(dz, 0.3)
            return self.count * per, max(dz, 0.35)
        per = 12 if self.t in ("knit", "bubbles") else 14
        return self.count * per, self.pitch / 9.0
