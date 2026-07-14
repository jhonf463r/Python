
#!/usr/bin/env python3
"""
SVG Laser Optimizer v2
- Path-level routing only
- Preserves geometry and colors
- Reorders contiguous <path> runs
- Optionally reverses whole PATHs when it reduces travel
- Includes basic audit helpers and an optional Streamlit UI

Dependencies:
    pip install lxml
Optional:
    pip install cairosvg pillow streamlit
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"
DEFAULT_UNITS_PER_MM = 96.0 / 25.4
EPS = 1e-9

try:
    import cairosvg  # type: ignore
except Exception:
    cairosvg = None  # type: ignore

try:
    from PIL import Image, ImageChops  # type: ignore
except Exception:
    Image = None  # type: ignore
    ImageChops = None  # type: ignore

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

Affine = Tuple[float, float, float, float, float, float]
IDENTITY: Affine = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

_TRANSFORM_FN_RE = re.compile(r"([a-zA-Z]+)\s*\(([^)]*)\)")
_NUM_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
_LENGTH_RE = re.compile(r"^\s*([0-9.+eE-]+)\s*([a-zA-Z%]*)\s*$")
_HEX_RE = re.compile(r"^#([0-9a-f]{3}|[0-9a-f]{6})$", re.I)
_RGB_RE = re.compile(r"^rgba?\(([^)]*)\)$", re.I)

Point = complex


# -----------------------------------------------------------------------------
# Affine transforms
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
    return f"matrix({a:.12g},{b:.12g},{c:.12g},{d:.12g},{e:.12g},{f:.12g})"


def _round_matrix(m: Affine, digits: int = 6) -> Tuple[float, ...]:
    return tuple(round(v, digits) for v in m)


def _parse_numbers(s: str) -> List[float]:
    return [float(x) for x in _NUM_RE.findall(s)]


def _matrix_from_transform(transform: Optional[str]) -> Affine:
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


def _effective_matrix(node: etree._Element) -> Affine:
    total = IDENTITY
    cur: Optional[etree._Element] = node
    while cur is not None:
        total = _compose(_matrix_from_transform(cur.get("transform")), total)
        cur = cur.getparent()
    return total


# -----------------------------------------------------------------------------
# SVG lengths / colors / styles
# -----------------------------------------------------------------------------

def _length_to_mm(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    m = _LENGTH_RE.match(value.strip())
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


def _parse_viewbox(vb: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not vb:
        return None
    parts = re.split(r"[\s,]+", vb.strip())
    if len(parts) != 4:
        return None
    try:
        return tuple(float(x) for x in parts)  # type: ignore[return-value]
    except Exception:
        return None


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


def _parse_style(style: Optional[str]) -> Dict[str, str]:
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


def _apply_style(el: etree._Element, style_map: Dict[str, str]) -> None:
    existing = _parse_style(el.get("style"))
    existing.update(style_map)
    if existing:
        el.set("style", ";".join(f"{k}:{v}" for k, v in existing.items()))
    for k in list(style_map.keys()):
        if k in el.attrib:
            del el.attrib[k]


def _norm_color(v: Optional[str]) -> str:
    if not v:
        return "none"
    return v.strip().lower() or "none"


def _color_to_rgb(v: Optional[str]) -> Optional[Tuple[int, int, int]]:
    v = _norm_color(v)
    if v in ("none", "transparent", ""):
        return None
    m = _HEX_RE.match(v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            r, g, b = (int(ch * 2, 16) for ch in h)
        else:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
        return (r, g, b)
    m = _RGB_RE.match(v)
    if m:
        nums = [x.strip() for x in m.group(1).split(",")]
        if len(nums) >= 3:
            try:
                r = int(float(nums[0]))
                g = int(float(nums[1]))
                b = int(float(nums[2]))
                return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            except Exception:
                return None
    return None


def _visible_stroke(el: etree._Element) -> bool:
    s = _norm_color(_style_value(el, "stroke", "none"))
    return s not in ("none", "transparent")


def _extract_render_color(el: etree._Element, mode: str = "auto") -> str:
    stroke = _norm_color(_style_value(el, "stroke", "none"))
    fill = _norm_color(_style_value(el, "fill", "none"))
    if mode == "stroke":
        return stroke
    if mode == "fill":
        return fill
    if mode == "exact":
        return f"{stroke}|{fill}"
    return stroke if _visible_stroke(el) else fill


def _style_signature(el: etree._Element) -> Tuple[str, ...]:
    keys = (
        "stroke",
        "fill",
        "stroke-width",
        "stroke-opacity",
        "fill-opacity",
        "opacity",
        "stroke-linecap",
        "stroke-linejoin",
        "fill-rule",
        "stroke-dasharray",
    )
    return tuple(_style_value(el, k, "") for k in keys)


def _has_visible_fill(el: etree._Element) -> bool:
    fill = _norm_color(_style_value(el, "fill", "none"))
    if fill in ("none", "transparent", ""):
        return False
    try:
        op = float(_style_value(el, "fill-opacity", "1") or "1")
        if op <= 0:
            return False
    except Exception:
        pass
    return True


def _has_visible_stroke(el: etree._Element) -> bool:
    stroke = _norm_color(_style_value(el, "stroke", "none"))
    if stroke in ("none", "transparent", ""):
        return False
    try:
        op = float(_style_value(el, "stroke-opacity", "1") or "1")
        if op <= 0:
            return False
    except Exception:
        pass
    return True


# -----------------------------------------------------------------------------
# Path parsing / flattening
# -----------------------------------------------------------------------------

Segment = Dict[str, object]
SubPath = Dict[str, object]


def _tokenize_path(d: str) -> List[str]:
    parts = re.split(r"([MmZzLlHhVvCcSsQqTtAa])", d)
    return [p for p in parts if p and p.strip()]


def _reflect(p: Point, about: Point) -> Point:
    return about + (about - p)


def _segment_start(seg: Segment) -> Point:
    return seg["start"]  # type: ignore[return-value]


def _segment_end(seg: Segment) -> Point:
    return seg["end"]  # type: ignore[return-value]


def _parse_path_exact(d: str) -> List[SubPath]:
    tokens = _tokenize_path(d)
    if not tokens:
        return []
    subpaths: List[SubPath] = []
    cur = complex(0.0, 0.0)
    start: Optional[Point] = None
    curr_subpath: Optional[SubPath] = None
    prev_cmd: Optional[str] = None
    prev_cubic_ctrl: Optional[Point] = None
    prev_quad_ctrl: Optional[Point] = None

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

        def ensure_subpath() -> SubPath:
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
                c1 = _reflect(prev_cubic_ctrl, cur) if prev_cmd and prev_cmd.upper() in ("C", "S") and prev_cubic_ctrl is not None else cur
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
                c = _reflect(prev_quad_ctrl, cur) if prev_cmd and prev_cmd.upper() in ("Q", "T") and prev_quad_ctrl is not None else cur
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


def _flatten_subpath(sp: SubPath, curve_steps: int = 20, arc_steps: int = 20) -> List[Point]:
    pts: List[Point] = [sp["start"]]  # type: ignore[list-item]
    cur = sp["start"]
    for seg in sp["segments"]:
        t = seg["type"]
        if t == "L":
            cur = seg["end"]  # type: ignore[assignment]
            pts.append(cur)
        elif t == "Q":
            p0 = cur
            p1 = seg["c"]  # type: ignore[assignment]
            p2 = seg["end"]  # type: ignore[assignment]
            for i in range(1, curve_steps + 1):
                u = i / curve_steps
                p = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u ** 2 * p2
                pts.append(p)
            cur = p2
        elif t == "C":
            p0 = cur
            p1 = seg["c1"]  # type: ignore[assignment]
            p2 = seg["c2"]  # type: ignore[assignment]
            p3 = seg["end"]  # type: ignore[assignment]
            for i in range(1, curve_steps + 1):
                u = i / curve_steps
                p = ((1 - u) ** 3) * p0 + 3 * ((1 - u) ** 2) * u * p1 + 3 * (1 - u) * (u ** 2) * p2 + (u ** 3) * p3
                pts.append(p)
            cur = p3
        elif t == "A":
            pts.extend(_arc_points(cur, seg, arc_steps)[1:])
            cur = seg["end"]  # type: ignore[assignment]
    return pts


def _arc_points(start: complex, seg: Segment, steps: int = 20) -> List[Point]:
    # SVG arc conversion based on the endpoint parameterization from the SVG spec.
    # This is an approximation suitable for bbox/length/audit.
    rx = float(seg["rx"])
    ry = float(seg["ry"])
    phi = math.radians(float(seg["phi"]))
    large_arc = int(seg["laf"])
    sweep = int(seg["swf"])
    x1, y1 = start.real, start.imag
    x2, y2 = seg["end"].real, seg["end"].imag

    if abs(rx) < EPS or abs(ry) < EPS or (abs(x1 - x2) < EPS and abs(y1 - y2) < EPS):
        return [start, seg["end"]]  # type: ignore[list-item]

    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    dx2 = (x1 - x2) / 2.0
    dy2 = (y1 - y2) / 2.0

    x1p = cos_phi * dx2 + sin_phi * dy2
    y1p = -sin_phi * dx2 + cos_phi * dy2

    rx_sq = rx * rx
    ry_sq = ry * ry
    x1p_sq = x1p * x1p
    y1p_sq = y1p * y1p

    radicant = max(0.0, (rx_sq * ry_sq - rx_sq * y1p_sq - ry_sq * x1p_sq) / (rx_sq * y1p_sq + ry_sq * x1p_sq + EPS))
    coef = math.sqrt(radicant)
    if large_arc == sweep:
        coef = -coef

    cxp = coef * (rx * y1p) / (ry + EPS)
    cyp = coef * -(ry * x1p) / (rx + EPS)

    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2.0

    def angle(u: Tuple[float, float], v: Tuple[float, float]) -> float:
        dot = u[0] * v[0] + u[1] * v[1]
        det = u[0] * v[1] - u[1] * v[0]
        return math.atan2(det, dot)

    ux = (x1p - cxp) / (rx + EPS)
    uy = (y1p - cyp) / (ry + EPS)
    vx = (-x1p - cxp) / (rx + EPS)
    vy = (-y1p - cyp) / (ry + EPS)
    theta1 = angle((1, 0), (ux, uy))
    delta = angle((ux, uy), (vx, vy))
    if sweep == 0 and delta > 0:
        delta -= 2 * math.pi
    elif sweep == 1 and delta < 0:
        delta += 2 * math.pi

    pts: List[Point] = [start]
    for i in range(1, steps + 1):
        t = theta1 + delta * (i / steps)
        ct = math.cos(t)
        st = math.sin(t)
        x = cx + cos_phi * rx * ct - sin_phi * ry * st
        y = cy + sin_phi * rx * ct + cos_phi * ry * st
        pts.append(complex(x, y))
    return pts


def _subpath_length(sp: SubPath) -> float:
    pts = _flatten_subpath(sp)
    return sum(abs(pts[i] - pts[i - 1]) for i in range(1, len(pts)))


def _subpath_bbox(sp: SubPath) -> Tuple[float, float, float, float]:
    pts = _flatten_subpath(sp)
    xs = [p.real for p in pts]
    ys = [p.imag for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _subpath_centroid(sp: SubPath) -> Point:
    pts = _flatten_subpath(sp)
    return sum(pts, complex(0.0, 0.0)) / max(1, len(pts))


def _subpath_start(sp: SubPath) -> Point:
    return sp["start"]  # type: ignore[return-value]


def _subpath_end(sp: SubPath) -> Point:
    if not sp["segments"]:
        return sp["start"]  # type: ignore[return-value]
    return sp["segments"][-1]["end"]  # type: ignore[return-value]


def _reverse_segment(seg: Segment) -> Segment:
    t = seg["type"]
    if t == "L":
        return {"type": "L", "start": seg["end"], "end": seg["start"]}
    if t == "Q":
        return {"type": "Q", "start": seg["end"], "c": seg["c"], "end": seg["start"]}
    if t == "C":
        return {"type": "C", "start": seg["end"], "c1": seg["c2"], "c2": seg["c1"], "end": seg["start"]}
    if t == "A":
        return {
            "type": "A",
            "start": seg["end"],
            "rx": seg["rx"],
            "ry": seg["ry"],
            "phi": seg["phi"],
            "laf": seg["laf"],
            "swf": 1 - int(seg["swf"]),
            "end": seg["start"],
        }
    raise ValueError(f"Unsupported segment type: {t}")


def _reverse_subpath(sp: SubPath) -> SubPath:
    rev = [_reverse_segment(seg) for seg in reversed(sp["segments"])]
    start = rev[0]["start"] if rev else sp["start"]
    return {"start": start, "segments": rev, "closed": bool(sp.get("closed", False))}


def _serialize_subpath(sp: SubPath, include_moveto: bool = True, include_close: bool = True) -> str:
    parts: List[str] = []
    start = _subpath_start(sp)
    if include_moveto:
        parts.append(f"M {start.real:.6f},{start.imag:.6f}")
    for seg in sp["segments"]:
        t = seg["type"]
        if t == "L":
            e = seg["end"]
            parts.append(f"L {e.real:.6f},{e.imag:.6f}")
        elif t == "Q":
            c = seg["c"]; e = seg["end"]
            parts.append(f"Q {c.real:.6f},{c.imag:.6f} {e.real:.6f},{e.imag:.6f}")
        elif t == "C":
            c1 = seg["c1"]; c2 = seg["c2"]; e = seg["end"]
            parts.append(f"C {c1.real:.6f},{c1.imag:.6f} {c2.real:.6f},{c2.imag:.6f} {e.real:.6f},{e.imag:.6f}")
        elif t == "A":
            e = seg["end"]
            parts.append(f"A {seg['rx']:.6f},{seg['ry']:.6f} {seg['phi']:.6f} {int(seg['laf'])} {int(seg['swf'])} {e.real:.6f},{e.imag:.6f}")
    if include_close and sp.get("closed", False):
        parts.append("Z")
    return " ".join(parts)


def _path_signature(subpaths: List[SubPath], digits: int = 3) -> str:
    flat: List[Tuple[float, float]] = []
    for sp in subpaths:
        pts = _flatten_subpath(sp)
        sig = _canonical_points_signature(pts, digits=digits)
        flat.extend(sig)
        flat.append((999999.0, 999999.0))
    return repr(flat)


def _canonical_points_signature(pts: List[Point], digits: int = 3) -> Tuple[Tuple[float, float], ...]:
    fwd = tuple((round(p.real, digits), round(p.imag, digits)) for p in pts)
    rev = tuple((round(p.real, digits), round(p.imag, digits)) for p in reversed(pts))
    return min(fwd, rev)


def _path_geometry_signature(el: etree._Element) -> str:
    m = _effective_matrix(el)
    sigs = []
    for sp in _parse_path_exact(el.get("d") or ""):
        pts = [_apply(m, p) for p in _flatten_subpath(sp)]
        sigs.append(_canonical_points_signature(pts))
    return repr(sigs)


# -----------------------------------------------------------------------------
# Route items and optimization
# -----------------------------------------------------------------------------

@dataclass
class RouteItem:
    element: etree._Element
    parent: etree._Element
    original_index: int
    subpaths: List[SubPath]
    matrix: Affine
    style_sig: Tuple[str, ...]
    path_sig: str
    centroid: Point
    bbox: Tuple[float, float, float, float]
    length: float
    is_closed_like: bool
    start: Point
    end: Point
    has_visible_fill: bool
    has_visible_stroke: bool

    def entry_point(self, reversed_: bool = False) -> Point:
        if self.is_closed_like:
            return self.centroid
        return self.end if reversed_ else self.start

    def exit_point(self, reversed_: bool = False) -> Point:
        if self.is_closed_like:
            return self.centroid
        return self.start if reversed_ else self.end


def _route_item_from_path(el: etree._Element, parent: etree._Element, original_index: int) -> Optional[RouteItem]:
    d = el.get("d") or ""
    if not d:
        return None
    try:
        subpaths = _parse_path_exact(d)
    except Exception:
        return None
    if not subpaths:
        return None
    m = _effective_matrix(el)
    world_subpaths: List[SubPath] = []
    world_pts: List[Point] = []
    total_len = 0.0
    for sp in subpaths:
        wsp = {"start": _apply(m, _subpath_start(sp)), "segments": [], "closed": bool(sp.get("closed", False))}
        for seg in sp["segments"]:
            t = seg["type"]
            if t == "L":
                wsp["segments"].append({"type": "L", "start": _apply(m, seg["start"]), "end": _apply(m, seg["end"])})
            elif t == "Q":
                wsp["segments"].append({"type": "Q", "start": _apply(m, seg["start"]), "c": _apply(m, seg["c"]), "end": _apply(m, seg["end"])})
            elif t == "C":
                wsp["segments"].append({"type": "C", "start": _apply(m, seg["start"]), "c1": _apply(m, seg["c1"]), "c2": _apply(m, seg["c2"]), "end": _apply(m, seg["end"])})
            elif t == "A":
                scale_x = math.hypot(m[0], m[1])
                scale_y = math.hypot(m[2], m[3])
                wsp["segments"].append({
                    "type": "A",
                    "start": _apply(m, seg["start"]),
                    "rx": float(seg["rx"]) * scale_x,
                    "ry": float(seg["ry"]) * scale_y,
                    "phi": float(seg["phi"]),
                    "laf": int(seg["laf"]),
                    "swf": int(seg["swf"]),
                    "end": _apply(m, seg["end"]),
                })
        world_subpaths.append(wsp)
        pts = _flatten_subpath(wsp)
        world_pts.extend(pts)
        total_len += sum(abs(pts[i] - pts[i - 1]) for i in range(1, len(pts)))
    xs = [p.real for p in world_pts]
    ys = [p.imag for p in world_pts]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    centroid = sum(world_pts, complex(0.0, 0.0)) / max(1, len(world_pts))
    start = _subpath_start(world_subpaths[0])
    end = _subpath_end(world_subpaths[-1])
    closed_like = all(abs(_subpath_start(sp) - _subpath_end(sp)) <= EPS for sp in world_subpaths if sp["segments"])
    return RouteItem(
        element=el,
        parent=parent,
        original_index=original_index,
        subpaths=world_subpaths,
        matrix=m,
        style_sig=_style_signature(el),
        path_sig=_path_signature(world_subpaths),
        centroid=centroid,
        bbox=bbox,
        length=total_len,
        is_closed_like=closed_like,
        start=start,
        end=end,
        has_visible_fill=_has_visible_fill(el),
        has_visible_stroke=_has_visible_stroke(el),
    )


def _transition_cost(a: RouteItem, b: RouteItem, b_reversed: bool) -> float:
    return abs(a.exit_point() - b.entry_point(b_reversed))


def _should_optimize_group(items: List[RouteItem], preserve_render: bool = True) -> bool:
    # Aggressive routing mode: any multi-path run can be optimized.
    # Geometry is preserved because we only reorder / reverse whole paths.
    return len(items) > 1


def _seed_keys(items: List[RouteItem]) -> List[int]:
    if not items:
        return []

    idxs = set()

    # Extremes by centroid.
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].centroid.imag, 3), round(items[i].centroid.real, 3), items[i].original_index)))
    idxs.add(max(range(len(items)), key=lambda i: (round(items[i].centroid.imag, 3), round(items[i].centroid.real, 3), -items[i].original_index)))

    # Extremes by bbox corners.
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].bbox[0], 3), round(items[i].bbox[1], 3), items[i].original_index)))
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].bbox[1], 3), round(items[i].bbox[0], 3), items[i].original_index)))
    idxs.add(max(range(len(items)), key=lambda i: (round(items[i].bbox[2], 3), round(items[i].bbox[3], 3), -items[i].original_index)))
    idxs.add(max(range(len(items)), key=lambda i: (round(items[i].bbox[3], 3), round(items[i].bbox[2], 3), -items[i].original_index)))

    # Extremes by endpoints.
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].start.real, 3), round(items[i].start.imag, 3), items[i].original_index)))
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].start.imag, 3), round(items[i].start.real, 3), items[i].original_index)))
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].end.real, 3), round(items[i].end.imag, 3), items[i].original_index)))
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].end.imag, 3), round(items[i].end.real, 3), items[i].original_index)))

    # Extremes by length and index anchors.
    idxs.add(min(range(len(items)), key=lambda i: (round(items[i].length, 3), items[i].original_index)))
    idxs.add(max(range(len(items)), key=lambda i: (round(items[i].length, 3), -items[i].original_index)))
    idxs.add(0)
    idxs.add(len(items) // 2)
    idxs.add(len(items) - 1)

    return [i for i in dict.fromkeys(i for i in idxs if 0 <= i < len(items))]


def _greedy_route(items: List[RouteItem], seed_index: int, allow_reverse: bool = True) -> List[Tuple[RouteItem, bool]]:
    remaining = items[:]
    seed = remaining.pop(seed_index)
    seed_options = [False, True] if (allow_reverse and not seed.is_closed_like) else [False]
    best_route: Optional[List[Tuple[RouteItem, bool]]] = None
    best_cost = float("inf")

    for seed_rev in seed_options:
        route: List[Tuple[RouteItem, bool]] = [(seed, seed_rev)]
        current_point = seed.exit_point(seed_rev)
        rest = remaining[:]
        while rest:
            best_i = 0
            best_rev = False
            best_c = float("inf")
            best_tie = (0.0, 0.0, 0)
            for i, cand in enumerate(rest):
                rev_options = [False] if (cand.is_closed_like or not allow_reverse) else [False, True]
                for rev in rev_options:
                    c = abs(current_point - cand.entry_point(rev))
                    tie = (round(cand.centroid.imag, 3), round(cand.centroid.real, 3), cand.original_index)
                    if (c < best_c - 1e-12) or (abs(c - best_c) <= 1e-12 and tie < best_tie):
                        best_c = c
                        best_i = i
                        best_rev = rev
                        best_tie = tie
            chosen = rest.pop(best_i)
            route.append((chosen, best_rev))
            current_point = chosen.exit_point(best_rev)
        cost = _route_cost(route)
        if cost < best_cost:
            best_cost = cost
            best_route = route

    return best_route if best_route is not None else [(items[seed_index], False)]


def _route_cost(route: List[Tuple[RouteItem, bool]]) -> float:
    if len(route) <= 1:
        return 0.0
    total = 0.0
    for i in range(1, len(route)):
        prev_item, prev_rev = route[i - 1]
        cur_item, cur_rev = route[i]
        total += abs(prev_item.exit_point(prev_rev) - cur_item.entry_point(cur_rev))
    return total


def _two_opt(route: List[Tuple[RouteItem, bool]], allow_reverse: bool = True, max_iter: int = 5) -> List[Tuple[RouteItem, bool]]:
    # Fast local improvement: keep it light so large SVGs still finish quickly.
    best = route[:]
    best_cost = _route_cost(best)
    n = len(best)
    if n < 3:
        return best

    for _ in range(max_iter):
        improved = False
        for i in range(n):
            item = best.pop(i)
            for j in range(n):
                trial = best[:]
                trial.insert(j, item)
                c = _route_cost(trial)
                if c + 1e-12 < best_cost:
                    best = trial
                    best_cost = c
                    improved = True
                    break
            else:
                best.insert(i, item)
                continue
            break
        if not improved:
            break
    return best


def _optimize_route_items(items: List[RouteItem], allow_reverse: bool = True) -> List[Tuple[RouteItem, bool]]:
    if len(items) <= 1:
        return [(items[0], False)] if items else []

    seeds = _seed_keys(items)
    if not seeds:
        seeds = [0]

    best_route: Optional[List[Tuple[RouteItem, bool]]] = None
    best_cost = float("inf")
    for seed in seeds:
        route = _greedy_route(items, seed_index=seed, allow_reverse=allow_reverse)
        route = _two_opt(route, allow_reverse=allow_reverse)
        c = _route_cost(route)
        if c < best_cost:
            best_cost = c
            best_route = route
    return best_route if best_route is not None else [(items[0], False)]


# -----------------------------------------------------------------------------
# SVG traversal / rewrite
# -----------------------------------------------------------------------------

def _all_path_elements(root: etree._Element) -> List[etree._Element]:
    return [el for el in root.iter() if el.tag == f"{{{SVG_NS}}}path"]


def _contiguous_path_runs(parent: etree._Element) -> List[List[etree._Element]]:
    runs: List[List[etree._Element]] = []
    current: List[etree._Element] = []
    for child in parent:
        if child.tag == f"{{{SVG_NS}}}path":
            current.append(child)
        else:
            if current:
                runs.append(current)
                current = []
    if current:
        runs.append(current)
    return runs


def _split_run_by_style(run: List[etree._Element]) -> List[List[etree._Element]]:
    if len(run) <= 1:
        return [run]
    groups: List[List[etree._Element]] = []
    current = [run[0]]
    current_sig = _style_signature(run[0])
    for el in run[1:]:
        sig = _style_signature(el)
        if sig == current_sig:
            current.append(el)
        else:
            groups.append(current)
            current = [el]
            current_sig = sig
    if current:
        groups.append(current)
    return groups


def _serialize_svg(tree: etree._ElementTree) -> bytes:
    out = io.BytesIO()
    tree.write(out, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return out.getvalue()


def _clone_element(el: etree._Element) -> etree._Element:
    return etree.fromstring(etree.tostring(el))


def _reverse_path_element(el: etree._Element) -> etree._Element:
    clone = _clone_element(el)
    d = clone.get("d") or ""
    subpaths = _parse_path_exact(d)
    rev_subpaths = [_reverse_subpath(sp) for sp in reversed(subpaths)]
    clone.set("d", " ".join(_serialize_subpath(sp, True, True) for sp in rev_subpaths).strip())
    return clone


def _rewrite_parent_with_run(parent: etree._Element, run: List[etree._Element], allow_reverse: bool = True, preserve_render: bool = True, original_svg_bytes: Optional[bytes] = None) -> Tuple[int, float, float, int]:
    """
    Replace a contiguous run of <path> with an optimized ordering.
    Returns: (paths_out, travel_before, travel_after, reversed_count)
    
    Aggressive mode: paths are reordered / reversed to reduce travel.
    Render preservation is optional and disabled by default.
    """
    if len(run) <= 1:
        return (len(run), 0.0, 0.0, 0)

    items: List[RouteItem] = []
    for idx, el in enumerate(run):
        item = _route_item_from_path(el, parent, idx)
        if item is not None:
            items.append(item)

    if len(items) <= 1 or not _should_optimize_group(items, preserve_render=preserve_render):
        return (len(run), 0.0, 0.0, 0)

    optimized = _optimize_route_items(items, allow_reverse=allow_reverse)
    travel_before = _route_cost([(it, False) for it in items])
    travel_after = _route_cost(optimized)

    # Replace original nodes with optimized clones in the same parent.
    first_pos = list(parent).index(run[0])
    original_clone_nodes = [_clone_element(el) for el in run]
    original_positions = [list(parent).index(el) for el in run]

    for el in run:
        parent.remove(el)

    reversed_count = 0
    insert_at = first_pos
    for item, rev in optimized:
        node = _clone_element(item.element)
        if rev and not item.is_closed_like:
            node = _reverse_path_element(node)
            reversed_count += 1
        parent.insert(insert_at, node)
        insert_at += 1

    if preserve_render and original_svg_bytes is not None and cairosvg is not None and Image is not None and ImageChops is not None:
        candidate_svg = _serialize_svg(parent.getroottree())
        identical, _diff_pixels = _render_compare(original_svg_bytes, candidate_svg)
        if identical is False:
            # rollback
            for el in list(parent)[first_pos:first_pos + len(optimized)]:
                parent.remove(el)
            for pos, orig in sorted(zip(original_positions, original_clone_nodes), key=lambda t: t[0]):
                parent.insert(pos, orig)
            return (len(run), 0.0, 0.0, 0)

    return (len(optimized), travel_before, travel_after, reversed_count)


def optimize_svg_bytes(
    svg_bytes: bytes,
    allow_reverse: bool = True,
    preserve_style_groups: bool = False,
    preserve_render: bool = False,
) -> Tuple[bytes, Dict[str, object]]:
    parser = etree.XMLParser(remove_blank_text=False, recover=True, huge_tree=True)
    tree = etree.parse(io.BytesIO(svg_bytes), parser)
    root = tree.getroot()

    stats = {
        "paths_in": 0,
        "paths_out": 0,
        "runs": 0,
        "travel_before": 0.0,
        "travel_after": 0.0,
        "travel_saved": 0.0,
        "travel_saved_pct": 0.0,
        "reversed_paths": 0,
        "style_groups": 0,
        "groups_skipped_for_render": 0,
    }

    def walk(parent: etree._Element) -> None:
        runs = _contiguous_path_runs(parent)
        for run in runs:
            stats["runs"] += 1
            stats["paths_in"] += len(run)
            subruns = _split_run_by_style(run) if preserve_style_groups else [run]
            stats["style_groups"] += len(subruns)
            for sub in subruns:
                if len(sub) <= 1:
                    stats["paths_out"] += len(sub)
                    continue
                out_count, before, after, reversed_count = _rewrite_parent_with_run(
                    parent,
                    sub,
                    allow_reverse=allow_reverse,
                    preserve_render=preserve_render,
                    original_svg_bytes=svg_bytes,
                )
                if before == 0.0 and after == 0.0 and len(sub) > 1:
                    stats["groups_skipped_for_render"] += 1
                stats["paths_out"] += out_count
                stats["travel_before"] += before
                stats["travel_after"] += after
                stats["reversed_paths"] += reversed_count
        for child in list(parent):
            if child.tag != f"{{{SVG_NS}}}path":
                walk(child)

    walk(root)
    stats["travel_saved"] = stats["travel_before"] - stats["travel_after"]
    if stats["travel_before"] > EPS:
        stats["travel_saved_pct"] = 100.0 * stats["travel_saved"] / stats["travel_before"]
    else:
        stats["travel_saved_pct"] = 0.0

    return _serialize_svg(tree), stats


# -----------------------------------------------------------------------------
# Audit / comparison
# -----------------------------------------------------------------------------

def _document_path_bbox(root: etree._Element) -> Optional[Tuple[float, float, float, float]]:
    pts: List[Point] = []
    for el in _all_path_elements(root):
        d = el.get("d") or ""
        try:
            subpaths = _parse_path_exact(d)
        except Exception:
            continue
        m = _effective_matrix(el)
        for sp in subpaths:
            for p in _flatten_subpath(sp):
                pts.append(_apply(m, p))
    if not pts:
        return None
    xs = [p.real for p in pts]
    ys = [p.imag for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _fmt_bbox(bbox: Optional[Tuple[float, float, float, float]]) -> str:
    if bbox is None:
        return "N/D"
    a, b, c, d = bbox
    return f"({a:.3f}, {b:.3f}) → ({c:.3f}, {d:.3f})"


def _render_png(svg_bytes: bytes, out_png: Optional[Path] = None, scale: float = 2.0) -> Optional[Path]:
    if cairosvg is None:
        return None
    if out_png is None:
        fd, name = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        out_png = Path(name)
    cairosvg.svg2png(bytestring=svg_bytes, write_to=str(out_png), scale=scale)
    return out_png


def _render_compare(a: bytes, b: bytes) -> Tuple[Optional[bool], Optional[int]]:
    if cairosvg is None or Image is None or ImageChops is None:
        return (None, None)
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.png"
        p2 = Path(td) / "b.png"
        cairosvg.svg2png(bytestring=a, write_to=str(p1))
        cairosvg.svg2png(bytestring=b, write_to=str(p2))
        img1 = Image.open(p1).convert("RGBA")
        img2 = Image.open(p2).convert("RGBA")
        diff = ImageChops.difference(img1, img2)
        bbox = diff.getbbox()
        pixel_diff = 0 if bbox is None else sum(1 for px in diff.getdata() if any(ch != 0 for ch in px))
        return (bbox is None, pixel_diff)


def audit_compare(original_svg: bytes, optimized_svg: bytes) -> Dict[str, object]:
    parser = etree.XMLParser(remove_blank_text=False, recover=True, huge_tree=True)
    org = etree.parse(io.BytesIO(original_svg), parser).getroot()
    opt = etree.parse(io.BytesIO(optimized_svg), parser).getroot()

    org_paths = _all_path_elements(org)
    opt_paths = _all_path_elements(opt)

    org_bbox = _document_path_bbox(org)
    opt_bbox = _document_path_bbox(opt)

    org_sig = sorted(_path_geometry_signature(el) for el in org_paths)
    opt_sig = sorted(_path_geometry_signature(el) for el in opt_paths)

    # Path-level multiset of canonical subpath signatures, order-independent within a path.
    def path_multiset(root_el: etree._Element) -> List[str]:
        out: List[str] = []
        for el in _all_path_elements(root_el):
            try:
                subpaths = _parse_path_exact(el.get("d") or "")
            except Exception:
                continue
            m = _effective_matrix(el)
            sub_sigs = []
            for sp in subpaths:
                pts = [_apply(m, p) for p in _flatten_subpath(sp)]
                sub_sigs.append(_canonical_points_signature(pts))
            out.append(repr(sorted(sub_sigs)))
        return sorted(out)

    org_path_multiset = path_multiset(org)
    opt_path_multiset = path_multiset(opt)

    render_identical = None
    pixel_diff = None
    if cairosvg is not None and Image is not None and ImageChops is not None:
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "org.png"
            p2 = Path(td) / "opt.png"
            cairosvg.svg2png(bytestring=original_svg, write_to=str(p1))
            cairosvg.svg2png(bytestring=optimized_svg, write_to=str(p2))
            img1 = Image.open(p1).convert("RGBA")
            img2 = Image.open(p2).convert("RGBA")
            diff = ImageChops.difference(img1, img2)
            bbox = diff.getbbox()
            pixel_diff = 0 if bbox is None else sum(1 for px in diff.getdata() if any(ch != 0 for ch in px))
            render_identical = bbox is None

    return {
        "original": {
            "path_count": len(org_paths),
            "bbox": org_bbox,
            "bbox_text": _fmt_bbox(org_bbox),
        },
        "optimized": {
            "path_count": len(opt_paths),
            "bbox": opt_bbox,
            "bbox_text": _fmt_bbox(opt_bbox),
        },
        "geometry_same_multiset": (org_sig == opt_sig) and (org_path_multiset == opt_path_multiset),
        "render_identical": render_identical,
        "pixel_diff_count": pixel_diff,
    }


# -----------------------------------------------------------------------------
# Streamlit UI
# -----------------------------------------------------------------------------

def _run_streamlit_ui() -> None:
    if st is None:
        return
    st.set_page_config(page_title="SVG Laser Optimizer v2", layout="wide")
    st.title("SVG Laser Optimizer v2")
    st.caption("Optimización de recorrido a nivel PATH completo, con auditoría de geometría y render.")

    with st.sidebar:
        st.header("Opciones")
        allow_reverse = st.checkbox("Permitir reverse de PATH completo", value=True)
        preserve_style_groups = st.checkbox("Preservar grupos contiguos por estilo", value=True)
        show_audit = st.checkbox("Mostrar auditoría", value=True)

    files = st.file_uploader("Sube uno o varios SVG", type=["svg"], accept_multiple_files=True)
    run = st.button("Optimizar", type="primary", use_container_width=True)

    if not run:
        return
    if not files:
        st.warning("Carga al menos un SVG.")
        return

    for uploaded in files:
        svg_bytes = uploaded.getvalue()
        opt_bytes, stats = optimize_svg_bytes(
            svg_bytes,
            allow_reverse=allow_reverse,
            preserve_style_groups=preserve_style_groups,
            preserve_render=True,
        )
        audit = audit_compare(svg_bytes, opt_bytes)
        st.subheader(uploaded.name)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Paths in", str(stats["paths_in"]))
        c2.metric("Paths out", str(stats["paths_out"]))
        c3.metric("Travel saved", f"{stats['travel_saved']:.3f}")
        c4.metric("Travel saved %", f"{stats['travel_saved_pct']:.2f}%")
        st.download_button(
            "Descargar SVG optimizado",
            data=opt_bytes,
            file_name=Path(uploaded.name).stem + "_optimized.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )
        if show_audit:
            st.write(
                {
                    "stats": stats,
                    "audit": audit,
                }
            )


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None and st is not None:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
            if get_script_run_ctx() is not None:
                _run_streamlit_ui()
                return 0
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="svg_laser_optimizer_v2.py",
        description="Path-level SVG optimizer with travel reduction and audit helpers.",
    )
    parser.add_argument("input", nargs="?", help="Input SVG path. Use '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output optimized SVG path.")
    parser.add_argument("--no-reverse", action="store_true", help="Disable PATH reverse decisions.")
    parser.add_argument("--no-style-groups", action="store_true", help="Ignore contiguous style grouping.")
    parser.add_argument("--report-json", help="Write audit report as JSON.")
    parser.add_argument("--compare", action="store_true", help="Print original vs optimized comparison.")
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        return 2

    if args.input == "-":
        svg_bytes = sys.stdin.buffer.read()
        input_name = "stdin.svg"
    else:
        input_path = Path(args.input)
        svg_bytes = input_path.read_bytes()
        input_name = input_path.name

    optimized_bytes, stats = optimize_svg_bytes(
        svg_bytes,
        allow_reverse=not args.no_reverse,
        preserve_style_groups=not args.no_style_groups,
    )

    output_path = Path(args.output) if args.output else Path(input_name).with_name(Path(input_name).stem + "_optimized.svg")
    output_path.write_bytes(optimized_bytes)

    print(f"OK: {input_name} -> {output_path}")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    if args.compare:
        cmp_data = audit_compare(svg_bytes, optimized_bytes)
        print(json.dumps(cmp_data, indent=2, ensure_ascii=False))

    if args.report_json:
        rep = {
            "stats": stats,
            "comparison": audit_compare(svg_bytes, optimized_bytes),
        }
        Path(args.report_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
