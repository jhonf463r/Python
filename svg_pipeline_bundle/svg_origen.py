#!/usr/bin/env python3
"""SVG Origin Preserver - V22 reducida a la capa de origen.

Flujo:
- Subir SVG
- Procesar con la lógica de origen de la V22
- Descargar SVG

Recorte deliberado:
- leer SVG
- calcular bbox visible / frame
- anclar origen superior izquierda
- aplicar la matriz cartesiana de salida de la V22
- exportar SVG

No optimización.
No rutas.
No unión de nodos.
No heurísticas.
No diagnósticos extra.
"""
from __future__ import annotations

import io
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree

try:
    import streamlit as st
except Exception:  # pragma: no cover
    class _Dummy:
        def __getattr__(self, _name):
            def _noop(*args, **kwargs):
                return None
            return _noop
    st = _Dummy()  # type: ignore


SVG_NS = "http://www.w3.org/2000/svg"
DEFAULT_UNITS_PER_MM = 96.0 / 25.4
EPS = 1e-9

Affine = Tuple[float, float, float, float, float, float]
IDENTITY: Affine = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

_TRANSFORM_FN_RE = re.compile(r"([a-zA-Z]+)\s*\(([^)]*)\)")
_NUM_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
_LENGTH_RE = re.compile(r"^\s*([0-9.+eE-]+)\s*([a-zA-Z%]*)\s*$")
HEX_RE = re.compile(r"^#([0-9a-f]{3}|[0-9a-f]{6})$", re.I)
RGB_RE = re.compile(r"^rgba?\(([^)]*)\)$", re.I)


# -----------------------------------------------------------------------------
# Affine helpers
# -----------------------------------------------------------------------------

def _compose(m1: Affine, m2: Affine) -> Affine:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply(m: Affine, z: complex) -> complex:
    a, b, c, d, e, f = m
    return complex(a * z.real + c * z.imag + e, b * z.real + d * z.imag + f)


def _matrix_to_transform(m: Affine) -> str:
    a, b, c, d, e, f = m
    return f"matrix({a:.12g} {b:.12g} {c:.12g} {d:.12g} {e:.12g} {f:.12g})"


def _parse_numbers(s: str) -> List[float]:
    return [float(x) for x in _NUM_RE.findall(s)]


def _matrix_from_transform(transform: str | None) -> Affine:
    if not transform:
        return IDENTITY
    total = IDENTITY
    for fn, args in _TRANSFORM_FN_RE.findall(transform):
        vals = _parse_numbers(args)
        name = fn.strip().lower()
        if name == "matrix" and len(vals) >= 6:
            m = (vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])
        elif name == "translate":
            tx = vals[0] if vals else 0.0
            ty = vals[1] if len(vals) > 1 else 0.0
            m = (1.0, 0.0, 0.0, 1.0, tx, ty)
        elif name == "scale":
            sx = vals[0] if vals else 1.0
            sy = vals[1] if len(vals) > 1 else sx
            m = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif name == "rotate" and vals:
            ang = math.radians(vals[0])
            ca = math.cos(ang)
            sa = math.sin(ang)
            r = (ca, sa, -sa, ca, 0.0, 0.0)
            if len(vals) >= 3:
                cx, cy = vals[1], vals[2]
                m = _compose((1.0, 0.0, 0.0, 1.0, cx, cy), _compose(r, (1.0, 0.0, 0.0, 1.0, -cx, -cy)))
            else:
                m = r
        elif name == "skewx" and vals:
            ang = math.radians(vals[0])
            m = (1.0, 0.0, math.tan(ang), 1.0, 0.0, 0.0)
        elif name == "skewy" and vals:
            ang = math.radians(vals[0])
            m = (1.0, math.tan(ang), 0.0, 1.0, 0.0, 0.0)
        else:
            continue
        total = _compose(total, m)
    return total


def _root_viewbox_matrix(root: etree._Element | None) -> Affine:
    if root is None:
        return IDENTITY
    vb = _parse_viewbox(root.get("viewBox"))
    if not vb:
        return IDENTITY
    vx, vy, _, _ = vb
    return (1.0, 0.0, 0.0, 1.0, -vx, -vy)


# -----------------------------------------------------------------------------
# SVG length / visibility helpers
# -----------------------------------------------------------------------------

def _length_to_px(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    m = _LENGTH_RE.match(value)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("", "px"):
        return num
    if unit == "mm":
        return num * 96.0 / 25.4
    if unit == "cm":
        return num * 96.0 / 2.54
    if unit == "in":
        return num * 96.0
    if unit == "pt":
        return num * 96.0 / 72.0
    if unit == "pc":
        return num * 16.0
    return None


def _length_to_mm(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    m = _LENGTH_RE.match(value)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("", "px"):
        return num * 25.4 / 96.0
    if unit == "mm":
        return num
    if unit == "cm":
        return num * 10.0
    if unit == "in":
        return num * 25.4
    if unit == "pt":
        return num * 25.4 / 72.0
    if unit == "pc":
        return num * 25.4 / 6.0
    return None




def _parse_viewbox(vb: str | None) -> Tuple[float, float, float, float] | None:
    if not vb:
        return None
    parts = re.split(r"[\s,]+", vb.strip())
    if len(parts) != 4:
        return None
    try:
        return tuple(float(x) for x in parts)  # type: ignore[return-value]
    except Exception:
        return None


def _parse_style(style: str | None) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not style:
        return out
    for part in style.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _style_value(el: etree._Element, key: str, default: str = "") -> str:
    style = _parse_style(el.get("style"))
    if key in style:
        return style[key]
    return (el.get(key) or default).strip()


def _norm_color(v: str | None) -> str:
    if not v:
        return "none"
    return v.strip().lower() or "none"








def _element_is_effectively_visible(el: etree._Element) -> bool:
    cur: Optional[etree._Element] = el
    blocked_tags = {"defs", "clipPath", "mask", "pattern", "symbol", "marker"}
    while cur is not None:
        if not isinstance(cur.tag, str):
            cur = cur.getparent()
            continue
        lname = etree.QName(cur).localname
        if lname in blocked_tags:
            return False
        display = _style_value(cur, "display", "").strip().lower()
        visibility = _style_value(cur, "visibility", "").strip().lower()
        if display == "none" or visibility == "hidden":
            return False
        cur = cur.getparent()
    return True


# -----------------------------------------------------------------------------
# Path parsing
# -----------------------------------------------------------------------------

def _tokenize_path(d: str) -> List[str]:
    parts = re.split(r"([MmZzLlHhVvCcSsQqTtAa])", d)
    return [p for p in parts if p and p.strip()]


def _reflect(p: Optional[complex], about: complex) -> complex:
    if p is None:
        return about
    return about + (about - p)


def _eval_quad(p0: complex, p1: complex, p2: complex, t: float) -> complex:
    mt = 1.0 - t
    return (mt * mt) * p0 + 2.0 * mt * t * p1 + (t * t) * p2


def _eval_cubic(p0: complex, p1: complex, p2: complex, p3: complex, t: float) -> complex:
    mt = 1.0 - t
    return (mt ** 3) * p0 + 3.0 * (mt ** 2) * t * p1 + 3.0 * mt * (t ** 2) * p2 + (t ** 3) * p3


def _quadratic_extrema_t(p0: float, p1: float, p2: float) -> List[float]:
    denom = p0 - 2.0 * p1 + p2
    if abs(denom) <= EPS:
        return []
    t = (p0 - p1) / denom
    return [t] if 0.0 < t < 1.0 else []


def _cubic_extrema_t(p0: float, p1: float, p2: float, p3: float) -> List[float]:
    a = -p0 + 3.0 * p1 - 3.0 * p2 + p3
    b = 2.0 * (p0 - 2.0 * p1 + p2)
    c = -p0 + p1
    ts: List[float] = []
    if abs(a) <= EPS:
        if abs(b) > EPS:
            t = -c / b
            if 0.0 < t < 1.0:
                ts.append(t)
        return ts
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return ts
    s = math.sqrt(max(0.0, disc))
    for t in ((-b - s) / (2.0 * a), (-b + s) / (2.0 * a)):
        if 0.0 < t < 1.0:
            ts.append(t)
    return ts


def _arc_to_center(
    start: complex,
    end: complex,
    rx: float,
    ry: float,
    phi_deg: float,
    large_arc: int,
    sweep: int,
) -> Tuple[complex, float, float, float, float]:
    phi = math.radians(phi_deg % 360.0)
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    x1 = start.real
    y1 = start.imag
    x2 = end.real
    y2 = end.imag

    rx = abs(rx)
    ry = abs(ry)
    if rx <= EPS or ry <= EPS:
        return complex((x1 + x2) / 2.0, (y1 + y2) / 2.0), phi, 0.0, 0.0, max(rx, EPS), max(ry, EPS)

    dx = (x1 - x2) / 2.0
    dy = (y1 - y2) / 2.0
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy

    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        s = math.sqrt(lam)
        rx *= s
        ry *= s

    sign = -1.0 if large_arc == sweep else 1.0
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = sign * math.sqrt(max(0.0, num / den)) if den > EPS else 0.0
    cxp = coef * (rx * y1p / ry) if ry > EPS else 0.0
    cyp = coef * (-ry * x1p / rx) if rx > EPS else 0.0

    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2.0

    def angle(u: Tuple[float, float], v: Tuple[float, float]) -> float:
        dot = u[0] * v[0] + u[1] * v[1]
        det = u[0] * v[1] - u[1] * v[0]
        return math.atan2(det, dot)

    ux = ((x1p - cxp) / rx, (y1p - cyp) / ry)
    vx = ((-x1p - cxp) / rx, (-y1p - cyp) / ry)
    theta1 = angle((1.0, 0.0), ux)
    delta = angle(ux, vx)

    if sweep == 0 and delta > 0:
        delta -= 2.0 * math.pi
    elif sweep == 1 and delta < 0:
        delta += 2.0 * math.pi

    return complex(cx, cy), phi, theta1, delta, rx, ry


def _arc_sample_points(seg: Dict[str, object], samples: int = 64) -> List[complex]:
    start = seg["start"]  # type: ignore[assignment]
    end = seg["end"]  # type: ignore[assignment]
    center, phi, theta1, delta, rx, ry = _arc_to_center(
        start, end, float(seg["rx"]), float(seg["ry"]), float(seg["phi"]), int(seg["laf"]), int(seg["swf"])
    )
    if abs(delta) <= EPS:
        return [start, end]
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)
    pts = []
    for i in range(samples + 1):
        t = i / samples
        th = theta1 + delta * t
        x = center.real + rx * math.cos(th) * cos_phi - ry * math.sin(th) * sin_phi
        y = center.imag + rx * math.cos(th) * sin_phi + ry * math.sin(th) * cos_phi
        pts.append(complex(x, y))
    return pts


def _parse_path_exact(d: str) -> List[Dict[str, object]]:
    tokens = _tokenize_path(d)
    if not tokens:
        return []

    subpaths: List[Dict[str, object]] = []
    cur = complex(0.0, 0.0)
    start: Optional[complex] = None
    curr_subpath: Optional[Dict[str, object]] = None
    prev_cmd: Optional[str] = None
    prev_cubic_ctrl: Optional[complex] = None
    prev_quad_ctrl: Optional[complex] = None

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if re.fullmatch(r"[MmZzLlHhVvCcSsQqTtAa]", tok):
            cmd = tok
            i += 1
        else:
            if prev_cmd is None:
                break
            cmd = prev_cmd

        up = cmd.upper()
        rel = cmd.islower()

        def read_nums() -> List[float]:
            nonlocal i
            if i >= len(tokens) or re.fullmatch(r"[MmZzLlHhVvCcSsQqTtAa]", tokens[i]):
                return []
            nums = _parse_numbers(tokens[i])
            i += 1
            return nums

        def ensure_subpath() -> Dict[str, object]:
            nonlocal curr_subpath, start
            if curr_subpath is None:
                curr_subpath = {"start": cur, "segments": [], "closed": False}
                start = cur
            return curr_subpath

        if up == "M":
            nums = read_nums()
            if len(nums) < 2:
                prev_cmd = cmd
                continue
            for j in range(0, len(nums) - 1, 2):
                p = complex(nums[j], nums[j + 1])
                if rel:
                    p += cur
                if j == 0:
                    if curr_subpath is not None and curr_subpath["segments"]:
                        subpaths.append(curr_subpath)
                    curr_subpath = {"start": p, "segments": [], "closed": False}
                else:
                    sp = ensure_subpath()
                    sp["segments"].append({"type": "L", "start": cur, "end": p})
                cur = p
            prev_cmd = "l" if rel else "L"
            prev_cubic_ctrl = None
            prev_quad_ctrl = None
            continue

        if up == "L":
            nums = read_nums()
            sp = ensure_subpath()
            for j in range(0, len(nums) - 1, 2):
                p = complex(nums[j], nums[j + 1])
                if rel:
                    p += cur
                sp["segments"].append({"type": "L", "start": cur, "end": p})
                cur = p
            prev_cmd = cmd
            prev_cubic_ctrl = None
            prev_quad_ctrl = None
            continue

        if up == "H":
            nums = read_nums()
            sp = ensure_subpath()
            for x in nums:
                p = complex(cur.real + x if rel else x, cur.imag)
                sp["segments"].append({"type": "L", "start": cur, "end": p})
                cur = p
            prev_cmd = cmd
            prev_cubic_ctrl = None
            prev_quad_ctrl = None
            continue

        if up == "V":
            nums = read_nums()
            sp = ensure_subpath()
            for y in nums:
                p = complex(cur.real, cur.imag + y if rel else y)
                sp["segments"].append({"type": "L", "start": cur, "end": p})
                cur = p
            prev_cmd = cmd
            prev_cubic_ctrl = None
            prev_quad_ctrl = None
            continue

        if up == "C":
            nums = read_nums()
            sp = ensure_subpath()
            for j in range(0, len(nums) - 5, 6):
                c1 = complex(nums[j], nums[j + 1])
                c2 = complex(nums[j + 2], nums[j + 3])
                p = complex(nums[j + 4], nums[j + 5])
                if rel:
                    c1 += cur
                    c2 += cur
                    p += cur
                sp["segments"].append({"type": "C", "start": cur, "c1": c1, "c2": c2, "end": p})
                cur = p
                prev_cubic_ctrl = c2
                prev_quad_ctrl = None
            prev_cmd = cmd
            continue

        if up == "S":
            nums = read_nums()
            sp = ensure_subpath()
            for j in range(0, len(nums) - 3, 4):
                c2 = complex(nums[j], nums[j + 1])
                p = complex(nums[j + 2], nums[j + 3])
                if rel:
                    c2 += cur
                    p += cur
                c1 = _reflect(prev_cubic_ctrl, cur) if prev_cmd and prev_cmd.upper() in ("C", "S") else cur
                sp["segments"].append({"type": "C", "start": cur, "c1": c1, "c2": c2, "end": p})
                cur = p
                prev_cubic_ctrl = c2
                prev_quad_ctrl = None
            prev_cmd = cmd
            continue

        if up == "Q":
            nums = read_nums()
            sp = ensure_subpath()
            for j in range(0, len(nums) - 3, 4):
                c = complex(nums[j], nums[j + 1])
                p = complex(nums[j + 2], nums[j + 3])
                if rel:
                    c += cur
                    p += cur
                sp["segments"].append({"type": "Q", "start": cur, "c": c, "end": p})
                cur = p
                prev_quad_ctrl = c
                prev_cubic_ctrl = None
            prev_cmd = cmd
            continue

        if up == "T":
            nums = read_nums()
            sp = ensure_subpath()
            for j in range(0, len(nums) - 1, 2):
                p = complex(nums[j], nums[j + 1])
                if rel:
                    p += cur
                c = _reflect(prev_quad_ctrl, cur) if prev_cmd and prev_cmd.upper() in ("Q", "T") else cur
                sp["segments"].append({"type": "Q", "start": cur, "c": c, "end": p})
                cur = p
                prev_quad_ctrl = c
                prev_cubic_ctrl = None
            prev_cmd = cmd
            continue

        if up == "A":
            nums = read_nums()
            sp = ensure_subpath()
            for j in range(0, len(nums) - 6, 7):
                rx, ry, phi, laf, swf, x, y = nums[j:j + 7]
                p = complex(x, y)
                if rel:
                    p += cur
                sp["segments"].append({
                    "type": "A",
                    "start": cur,
                    "rx": float(rx),
                    "ry": float(ry),
                    "phi": float(phi),
                    "laf": int(round(laf)),
                    "swf": int(round(swf)),
                    "end": p,
                })
                cur = p
                prev_cubic_ctrl = None
                prev_quad_ctrl = None
            prev_cmd = cmd
            continue

        if up == "Z":
            if curr_subpath is not None:
                curr_subpath["closed"] = True
                if start is not None and abs(cur - start) > EPS:
                    curr_subpath["segments"].append({"type": "L", "start": cur, "end": start})
                    cur = start
                subpaths.append(curr_subpath)
                curr_subpath = None
                start = None
            prev_cmd = cmd
            prev_cubic_ctrl = None
            prev_quad_ctrl = None
            continue

        _ = read_nums()
        prev_cmd = cmd

    if curr_subpath is not None and (curr_subpath["segments"] or curr_subpath.get("start") is not None):
        subpaths.append(curr_subpath)

    for sp in subpaths:
        if sp["segments"]:
            sp["start"] = sp["segments"][0]["start"]

    return subpaths


def _subpath_start(subpath: Dict[str, object]) -> complex:
    return subpath["start"]  # type: ignore[return-value]




def _subpath_bbox(subpath: Dict[str, object], matrix: Affine) -> Tuple[float, float, float, float]:
    pts: List[complex] = []
    segs = subpath["segments"]  # type: ignore[assignment]
    for seg in segs:
        t = seg["type"]
        if t == "L":
            pts.append(_apply(matrix, seg["start"]))
            pts.append(_apply(matrix, seg["end"]))
        elif t == "Q":
            p0 = _apply(matrix, seg["start"])
            p1 = _apply(matrix, seg["c"])
            p2 = _apply(matrix, seg["end"])
            pts.extend([p0, p2])
            for tt in _quadratic_extrema_t(p0.real, p1.real, p2.real):
                pts.append(_eval_quad(p0, p1, p2, tt))
            for tt in _quadratic_extrema_t(p0.imag, p1.imag, p2.imag):
                pts.append(_eval_quad(p0, p1, p2, tt))
        elif t == "C":
            p0 = _apply(matrix, seg["start"])
            p1 = _apply(matrix, seg["c1"])
            p2 = _apply(matrix, seg["c2"])
            p3 = _apply(matrix, seg["end"])
            pts.extend([p0, p3])
            for tt in _cubic_extrema_t(p0.real, p1.real, p2.real, p3.real):
                pts.append(_eval_cubic(p0, p1, p2, p3, tt))
            for tt in _cubic_extrema_t(p0.imag, p1.imag, p2.imag, p3.imag):
                pts.append(_eval_cubic(p0, p1, p2, p3, tt))
        elif t == "A":
            for p in _arc_sample_points(seg, samples=64):
                pts.append(_apply(matrix, p))
        else:
            pts.append(_apply(matrix, seg["start"]))
            pts.append(_apply(matrix, seg["end"]))

    if not pts:
        s = _apply(matrix, _subpath_start(subpath))
        return (s.real, s.imag, s.real, s.imag)

    xs = [p.real for p in pts]
    ys = [p.imag for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))



def _document_visible_path_bbox(root: etree._Element) -> Optional[Tuple[float, float, float, float]]:
    paths = [el for el in root.iter() if isinstance(el.tag, str) and etree.QName(el).localname == "path"]
    if not paths:
        return None

    root_matrix = _root_viewbox_matrix(root)
    minx = miny = float("inf")
    maxx = maxy = float("-inf")

    for el in paths:
        if not _element_is_effectively_visible(el):
            continue

        d = el.get("d") or ""
        if not d:
            continue

        try:
            subpaths = _parse_path_exact(d)
        except Exception:
            continue

        if not subpaths:
            continue

        # IMPORTANT:
        # The V22 origin branch measures bbox in the same CTM chain that the
        # drawing actually uses on screen. That means every parent <g> transform
        # must be included, not only the <path>'s own transform.
        mat = root_matrix
        chain: List[etree._Element] = []
        cur: Optional[etree._Element] = el
        while cur is not None:
            if isinstance(cur.tag, str):
                chain.append(cur)
            cur = cur.getparent()

        for node in reversed(chain):
            mat = _compose(mat, _matrix_from_transform(node.get("transform")))

        for sp in subpaths:
            bx0, by0, bx1, by1 = _subpath_bbox(sp, mat)
            minx = min(minx, bx0)
            miny = min(miny, by0)
            maxx = max(maxx, bx1)
            maxy = max(maxy, by1)

    if not math.isfinite(minx):
        return None
    return (minx, miny, maxx, maxy)




def _document_frame_bbox(root: etree._Element) -> Optional[Tuple[float, float, float, float]]:
    vb = _parse_viewbox(root.get("viewBox"))
    if vb is not None:
        return vb
    width_px = _length_to_px(root.get("width"))
    height_px = _length_to_px(root.get("height"))
    if width_px is not None and height_px is not None and width_px > 0 and height_px > 0:
        return (0.0, 0.0, width_px, height_px)
    return _document_visible_path_bbox(root)


def infer_units_per_mm(svg_root: etree._Element) -> float:
    width_mm = _length_to_mm(svg_root.get("width"))
    height_mm = _length_to_mm(svg_root.get("height"))
    vb = _parse_viewbox(svg_root.get("viewBox"))
    candidates: List[float] = []
    if vb is not None:
        _, _, vbw, vbh = vb
        if width_mm and width_mm > 0 and vbw > 0:
            candidates.append(vbw / width_mm)
        if height_mm and height_mm > 0 and vbh > 0:
            candidates.append(vbh / height_mm)
    return sum(candidates) / len(candidates) if candidates else DEFAULT_UNITS_PER_MM




def _origin_anchor_from_mode(
    origin_mode: str,
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    custom_x_mm: float = 0.0,
    custom_y_mm: float = 0.0,
    units_per_mm: float = DEFAULT_UNITS_PER_MM,
) -> Tuple[float, float]:
    minx, miny, maxx, maxy = bbox
    origin_mode = origin_mode.strip()
    if origin_mode.startswith("Superior izquierda"):
        return minx, miny
    if origin_mode.startswith("Inferior izquierda"):
        return minx, maxy
    if origin_mode.startswith("Centro"):
        return (minx + maxx) / 2.0, (miny + maxy) / 2.0
    if origin_mode.startswith("Superior derecha"):
        return maxx, miny
    if origin_mode.startswith("Inferior derecha"):
        return maxx, maxy
    return custom_x_mm * units_per_mm, custom_y_mm * units_per_mm


def _origin_output_matrix(
    origin_mode: str,
    bbox: Tuple[float, float, float, float],
    custom_x_mm: float = 0.0,
    custom_y_mm: float = 0.0,
    units_per_mm: float = DEFAULT_UNITS_PER_MM,
) -> Affine:
    """
    Export matrix for the saved SVG.

    Important:
    - This is TRANSLATION ONLY.
    - No rotation.
    - No mirror / invert.
    - The output must remain a pure origin shift so the saved geometry is not
      reinterpreted by the viewer as a different plane orientation.
    """
    ax, ay = _origin_anchor_from_mode(origin_mode, bbox, custom_x_mm, custom_y_mm, units_per_mm)
    return (1.0, 0.0, 0.0, 1.0, -ax, -ay)


def _transform_bbox(
    bbox: Optional[Tuple[float, float, float, float]],
    matrix: Affine,
) -> Optional[Tuple[float, float, float, float]]:
    """
    Transform an axis-aligned bbox by an affine matrix and return the
    axis-aligned bbox of the transformed corners.
    """
    if bbox is None:
        return None
    minx, miny, maxx, maxy = bbox
    corners = [
        complex(minx, miny),
        complex(minx, maxy),
        complex(maxx, miny),
        complex(maxx, maxy),
    ]
    pts = [_apply(matrix, p) for p in corners]
    xs = [p.real for p in pts]
    ys = [p.imag for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _origin_debug_report(
    svg_bytes: bytes,
    origin_mode: str = "Superior izquierda (0,0)",
    custom_x_mm: float = 0.0,
    custom_y_mm: float = 0.0,
    units_per_mm: float = DEFAULT_UNITS_PER_MM,
) -> Dict[str, object]:
    parser = etree.XMLParser(remove_blank_text=False, recover=True, huge_tree=True)
    root = etree.parse(io.BytesIO(svg_bytes), parser).getroot()

    path_bbox = _document_visible_path_bbox(root)
    frame_bbox = _document_frame_bbox(root)
    chosen_bbox = path_bbox if path_bbox is not None else frame_bbox if frame_bbox is not None else (0.0, 0.0, 0.0, 0.0)

    origin_matrix = _origin_output_matrix(origin_mode, chosen_bbox, custom_x_mm, custom_y_mm, units_per_mm)
    output_bbox = _transform_bbox(chosen_bbox, origin_matrix) or chosen_bbox

    return {
        "path_bbox": path_bbox,
        "frame_bbox": frame_bbox,
        "chosen_bbox": chosen_bbox,
        "anchor": _origin_anchor_from_mode(origin_mode, chosen_bbox, custom_x_mm, custom_y_mm, units_per_mm),
        "matrix": origin_matrix,
        "output_bbox": output_bbox,
        "origin_mode": origin_mode,
        "custom_x_mm": custom_x_mm,
        "custom_y_mm": custom_y_mm,
    }


def _build_visual_transform(rotation_deg: int, invert_x: bool = False, invert_y: bool = True) -> Affine:
    """Build the diagnostic/export Cartesian transform used by the V22 branch."""
    rotation_deg = int(rotation_deg) % 360
    transform = IDENTITY
    if invert_x:
        transform = _compose((-1.0, 0.0, 0.0, 1.0, 0.0, 0.0), transform)
    if invert_y:
        transform = _compose((1.0, 0.0, 0.0, -1.0, 0.0, 0.0), transform)
    if rotation_deg == 90:
        transform = _compose((0.0, 1.0, -1.0, 0.0, 0.0, 0.0), transform)
    elif rotation_deg == 180:
        transform = _compose((-1.0, 0.0, 0.0, -1.0, 0.0, 0.0), transform)
    elif rotation_deg == 270:
        transform = _compose((0.0, -1.0, 1.0, 0.0, 0.0, 0.0), transform)
    return transform


def _unwrap_origin_wrapper(root: etree._Element) -> None:
    for el in list(root.iter()):
        if isinstance(el.tag, str) and etree.QName(el).localname == "g" and el.get("id") == "svg_laser_optimizer_work_origin":
            parent = el.getparent()
            if parent is not None:
                idx = parent.index(el)
                for child in list(el):
                    parent.insert(idx, child)
                    idx += 1
                parent.remove(el)


def _apply_origin_transform_to_svg(
    svg_bytes: bytes,
    origin_mode: str = "Superior izquierda (0,0)",
    rotation_deg: int = 0,
    invert_x: bool = False,
    invert_y: bool = True,
    custom_x_mm: float = 0.0,
    custom_y_mm: float = 0.0,
    units_per_mm: float = DEFAULT_UNITS_PER_MM,
) -> bytes:
    parser = etree.XMLParser(remove_blank_text=False, recover=True, huge_tree=True)
    tree = etree.parse(io.BytesIO(svg_bytes), parser)
    root = tree.getroot()

    # V22 export branch: compute bbox -> anchor -> apply cartesian matrix
    # and bake the whole drawing into a wrapper, keeping the same origin logic.
    _unwrap_origin_wrapper(root)

    path_bbox = _document_visible_path_bbox(root)
    frame_bbox = _document_frame_bbox(root)
    bbox = path_bbox if path_bbox is not None else frame_bbox if frame_bbox is not None else (0.0, 0.0, 0.0, 0.0)

    ax, ay = _origin_anchor_from_mode(origin_mode, bbox, custom_x_mm, custom_y_mm, units_per_mm)
    base_matrix = (1.0, 0.0, 0.0, 1.0, -ax, -ay)
    visual_matrix = _build_visual_transform(rotation_deg, invert_x=invert_x, invert_y=invert_y)
    matrix = _compose(visual_matrix, base_matrix)

    def _prune_editor_and_empty_nodes(node: etree._Element) -> None:
        for child in list(node):
            _prune_editor_and_empty_nodes(child)
        lname = etree.QName(node).localname if isinstance(node.tag, str) else ""
        if lname in {"namedview", "metadata"}:
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
            return
        if lname in {"g", "defs"} and len(node) == 0 and not (node.text or "").strip():
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)

    _prune_editor_and_empty_nodes(root)

    wrapper = etree.Element(f"{{{SVG_NS}}}g")
    wrapper.set("id", "svg_laser_optimizer_work_origin")
    wrapper.set("transform", _matrix_to_transform(matrix))

    moved_any = False
    insert_at = 0
    for child in list(root):
        lname = etree.QName(child).localname if isinstance(child.tag, str) else ""
        if lname == "defs":
            insert_at += 1
            continue
        root.remove(child)
        wrapper.append(child)
        moved_any = True

    if moved_any:
        root.insert(insert_at, wrapper)

    # This is the key difference from the top-left wrapper that felt "unchanged":
    # the V22 export branch removes the canvas frame so the SVG importer does not
    # recentre it back into the original page.
    for attr in ("viewBox", "width", "height", "preserveAspectRatio"):
        if attr in root.attrib:
            del root.attrib[attr]

    out = io.BytesIO()
    tree.write(out, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return out.getvalue()



def process_svg_bytes(
    svg_bytes: bytes,
    origin_mode: str = "Superior izquierda (0,0)",
    custom_x_mm: float = 0.0,
    custom_y_mm: float = 0.0,
    show_diagnostic: bool = True,
) -> Tuple[bytes, Dict[str, object]]:
    """
    Process one SVG using the exact origin/export behavior that already works.

    The saved SVG is intentionally left with the same export matrix logic as the
    validated reduced version. The extra options only choose the anchor point.
    """
    parser = etree.XMLParser(remove_blank_text=False, recover=True, huge_tree=True)
    source_root = etree.parse(io.BytesIO(svg_bytes), parser).getroot()
    units_per_mm = infer_units_per_mm(source_root)

    debug = _origin_debug_report(
        svg_bytes,
        origin_mode=origin_mode,
        custom_x_mm=custom_x_mm,
        custom_y_mm=custom_y_mm,
        units_per_mm=units_per_mm,
    )

    out = _apply_origin_transform_to_svg(
        svg_bytes,
        origin_mode=origin_mode,
        rotation_deg=0,
        invert_x=False,
        invert_y=True,
        custom_x_mm=custom_x_mm,
        custom_y_mm=custom_y_mm,
        units_per_mm=units_per_mm,
    )

    out_root = etree.parse(io.BytesIO(out), parser).getroot()
    wrapper = None
    for el in out_root.iter():
        if isinstance(el.tag, str) and etree.QName(el).localname == "g" and el.get("id") == "svg_laser_optimizer_work_origin":
            wrapper = el
            break

    info = {
        "transform": wrapper.get("transform") if wrapper is not None else None,
        "width": out_root.get("width"),
        "height": out_root.get("height"),
        "viewBox": out_root.get("viewBox"),
        "chosen_bbox": debug.get("chosen_bbox"),
        "path_bbox": debug.get("path_bbox"),
        "frame_bbox": debug.get("frame_bbox"),
        "anchor": debug.get("anchor"),
        "matrix": debug.get("matrix"),
        "output_bbox": debug.get("output_bbox"),
        "origin_mode": origin_mode,
        "custom_x_mm": custom_x_mm,
        "custom_y_mm": custom_y_mm,
        "show_diagnostic": show_diagnostic,
    }
    return out, info


def _safe_output_name(name: str) -> str:
    return f"{Path(name).stem}_origin_top_left.svg"


def _format_bbox_text(bbox: Optional[Tuple[float, float, float, float]]) -> str:
    if bbox is None:
        return "N/D"
    minx, miny, maxx, maxy = bbox
    return f"({minx:.3f}, {miny:.3f}) → ({maxx:.3f}, {maxy:.3f})"


def _format_point(pt: object) -> str:
    try:
        x, y = pt
        return f"({float(x):.3f}, {float(y):.3f})"
    except Exception:
        return "N/D"


def _format_matrix(m: object) -> str:
    try:
        a, b, c, d, e, f = m
        return f"[{a:.3f} {c:.3f} {e:.3f}; {b:.3f} {d:.3f} {f:.3f}]"
    except Exception:
        return "N/D"


def _svg_preview_html(svg_bytes: bytes) -> str:
    import base64
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f'<iframe src="data:image/svg+xml;base64,{encoded}" style="width:100%;height:760px;border:1px solid #ddd;border-radius:12px;background:white;" loading="lazy"></iframe>'



def _run_streamlit_ui() -> None:
    st.set_page_config(page_title="SVG Origen V22 - Capa robusta", layout="wide")
    st.title("SVG Origen V22 - Capa robusta")
    st.caption(
        "Capa de origen pura: leer SVG → medir bbox visible real → anclar → exportar con la lógica validada. "
        "La rotación/preview cartesiana, si se usa, no debe contaminar el SVG exportado."
    )

    origin_mode = st.selectbox(
        "Origen CNC del trabajo",
        [
            "Superior izquierda (0,0)",
            "Inferior izquierda",
            "Centro",
            "Superior derecha",
            "Inferior derecha",
            "Personalizado X/Y",
        ],
        index=0,
        help="Selecciona el punto de referencia del origen. La exportación conserva la lógica validada.",
    )

    custom_x_mm = 0.0
    custom_y_mm = 0.0
    if origin_mode == "Personalizado X/Y":
        c1, c2 = st.columns(2)
        with c1:
            custom_x_mm = st.number_input("Origen X personalizado (mm)", value=0.0, step=1.0, format="%.3f")
        with c2:
            custom_y_mm = st.number_input("Origen Y personalizado (mm)", value=0.0, step=1.0, format="%.3f")

    show_diagnostic = st.checkbox("Mostrar diagnóstico", value=True, help="Muestra bbox, ancla y matriz calculados; no altera la exportación.")
    uploaded = st.file_uploader("Sube un SVG", type=["svg"], accept_multiple_files=False)

    with st.form("process_form", clear_on_submit=False):
        submitted = st.form_submit_button("Procesar", use_container_width=True)

    if not submitted:
        st.info("Sube un archivo y pulsa Procesar.")
        return

    if uploaded is None:
        st.warning("Primero carga un SVG.")
        return

    try:
        output_bytes, info = process_svg_bytes(
            uploaded.getvalue(),
            origin_mode=origin_mode,
            custom_x_mm=custom_x_mm,
            custom_y_mm=custom_y_mm,
            show_diagnostic=show_diagnostic,
        )
    except Exception as exc:
        st.error(f"No se pudo procesar el SVG: {exc}")
        return

    st.success("Archivo procesado correctamente.")
    st.write(f"Transform aplicado: `{info.get('transform')}`")
    st.write(f"Canvas de salida: width={info.get('width')} height={info.get('height')} viewBox={info.get('viewBox')}")

    if show_diagnostic:
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"BBox archivo: {_format_bbox_text(info.get('path_bbox'))}")
            st.write(f"BBox frame: {_format_bbox_text(info.get('frame_bbox'))}")
            st.write(f"BBox elegida: {_format_bbox_text(info.get('chosen_bbox'))}")
        with col2:
            st.write(f"Ancla: {_format_point(info.get('anchor'))}")
            st.write(f"Matriz origen: {_format_matrix(info.get('matrix'))}")
            st.write(f"BBox salida: {_format_bbox_text(info.get('output_bbox'))}")

    st.subheader("Vista previa procesada")
    st.components.v1.html(_svg_preview_html(output_bytes), height=780, scrolling=True)

    st.download_button(
        "Descargar SVG procesado",
        data=output_bytes,
        file_name=_safe_output_name(uploaded.name),
        mime="image/svg+xml",
        use_container_width=True,
    )


if __name__ == "__main__":
    _run_streamlit_ui()
