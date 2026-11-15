#!/usr/bin/env python3
"""Inspect and render an AP214 STEP file with the standard library only.

The point of this tool is to answer "what are the real dimensions?" without a
CAD kernel or a GUI, so a design can be reconstructed from an exported model
rather than from memory. It is deliberately small: it reads the STEP text,
tabulates the circles and planes, and rasterises the faces into PNGs with a
z-buffer.

Subcommands
    summary  entity counts, solid count, exact vertex bounding box
    features circles (holes and rounds) and planes (flat faces), with extents
    render   top / front / side / isometric PNGs

Examples
    python3 tools/cad/step_inspect.py summary part.step
    python3 tools/cad/step_inspect.py features part.step
    python3 tools/cad/step_inspect.py render part.step --out /tmp/part

Known limits, which matter when reading the output:
  * A STEP circle is a face boundary, not necessarily a hole. Two concentric
    circles usually mean a counterbore; a single one may be an outer round.
  * Cylindrical faces are tessellated from their own edge loops, so a fillet
    shows as a band, not as a mathematically exact surface.
  * Nothing here computes volume. Use a CAD kernel for that.
"""
import argparse
import math
import re
import sys
from collections import Counter, defaultdict

STATEMENT = re.compile(r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.S)


class Step:
    def __init__(self, path):
        raw = open(path, "r", errors="replace").read()
        self.ents = {}
        for m in STATEMENT.finditer(raw):
            self.ents[int(m.group(1))] = (m.group(2), m.group(3))
        self.points = {}
        for i, (t, b) in self.ents.items():
            if t == "CARTESIAN_POINT":
                v = self.nums(b)
                if len(v) >= 3:
                    self.points[i] = tuple(v[:3])
        self._axis = {}
        self._faces = None

    # -- parsing helpers -----------------------------------------------------
    @staticmethod
    def refs(body):
        return [int(x) for x in re.findall(r"#(\d+)", body)]

    @staticmethod
    def nums(body):
        return [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", body)]

    def axis(self, pid):
        if pid in self._axis:
            return self._axis[pid]
        t, b = self.ents.get(pid, (None, ""))
        out = None
        if t == "AXIS2_PLACEMENT_3D":
            r = self.refs(b)
            loc = self.points.get(r[0]) if r else None
            direction = (0.0, 0.0, 1.0)
            if len(r) > 1:
                t2, b2 = self.ents.get(r[1], (None, ""))
                if t2 == "DIRECTION":
                    v = self.nums(b2)
                    if len(v) >= 3:
                        direction = tuple(v[:3])
            out = (loc, direction)
        self._axis[pid] = out
        return out

    def vertices(self):
        out = {}
        for i, (t, b) in self.ents.items():
            if t == "VERTEX_POINT":
                r = self.refs(b)
                if r and r[0] in self.points:
                    out[i] = self.points[r[0]]
        return out

    # -- edges and faces -----------------------------------------------------
    def edge_polyline(self, ec_id, forward, samples=24):
        t, b = self.ents.get(ec_id, (None, ""))
        if t != "EDGE_CURVE":
            return []
        r = self.refs(b)
        if len(r) < 2:
            return []

        def vertex(vid):
            tv, bv = self.ents.get(vid, (None, ""))
            if tv == "VERTEX_POINT":
                rv = self.refs(bv)
                if rv and rv[0] in self.points:
                    return self.points[rv[0]]
            return None

        p1, p2 = vertex(r[0]), vertex(r[1])
        if p1 is None or p2 is None:
            return []
        ctype, cbody = self.ents.get(r[2], (None, "")) if len(r) > 2 else (None, "")
        pts = [p1, p2]
        if ctype in ("CIRCLE", "ELLIPSE"):
            a = self.axis(self.refs(cbody)[0])
            if a and a[0]:
                radius = (self.nums(cbody)[-1] if ctype == "CIRCLE"
                          else math.dist(a[0], p1))
                pts = self._arc(a[0], a[1], p1, p2, radius, samples)
        elif ctype and ctype.startswith("B_SPLINE"):
            control = [self.points[x] for x in self.refs(cbody) if x in self.points]
            if len(control) >= 2:
                pts = control
        return list(reversed(pts)) if not forward else pts

    @staticmethod
    def _arc(centre, axis, p1, p2, radius, samples):
        n = _norm(axis)
        u = _norm(_sub(p1, centre))
        v = _norm(_cross(n, u))
        a2 = math.atan2(_dot(_sub(p2, centre), v), _dot(_sub(p2, centre), u))
        if a2 < 0:
            a2 += 2 * math.pi
        steps = max(4, int(abs(a2) / (math.pi / samples)) + 1)
        return [_add(centre, _add(_mul(u, radius * math.cos(a2 * k / steps)),
                                  _mul(v, radius * math.sin(a2 * k / steps))))
                for k in range(steps + 1)]

    def loop_points(self, loop_id):
        t, b = self.ents.get(loop_id, (None, ""))
        if t in ("FACE_BOUND", "FACE_OUTER_BOUND"):
            r = self.refs(b)
            return self.loop_points(r[0]) if r else []
        if t != "EDGE_LOOP":
            return []
        out = []
        for oe in self.refs(b):
            t2, b2 = self.ents.get(oe, (None, ""))
            if t2 != "ORIENTED_EDGE":
                continue
            forward = b2.rstrip().rstrip(")").endswith(".T.")
            r = self.refs(b2)
            if not r:
                continue
            for p in self.edge_polyline(r[-1], forward):
                if not out or math.dist(out[-1], p) > 1e-6:
                    out.append(p)
        return out

    def faces(self):
        """[(surface type, [bound, ...])] where bound 0 is the outer loop."""
        if self._faces is not None:
            return self._faces
        out = []
        for i, (t, b) in self.ents.items():
            if t != "ADVANCED_FACE":
                continue
            r = self.refs(b)
            surface = self.ents.get(r[-1], (None, ""))[0] if r else None
            bounds = [self.loop_points(x) for x in r[:-1]]
            bounds = [x for x in bounds if len(x) >= 3]
            if bounds:
                out.append((surface, bounds))
        self._faces = out
        return out

    # -- reports -------------------------------------------------------------
    def bbox(self):
        v = self.vertices().values()
        lo = [min(p[i] for p in v) for i in range(3)]
        hi = [max(p[i] for p in v) for i in range(3)]
        return lo, hi

    def solids(self):
        return [i for i, (t, _) in self.ents.items() if t == "MANIFOLD_SOLID_BREP"]

    def circles(self):
        found = defaultdict(int)
        for i, (t, b) in self.ents.items():
            if t != "CIRCLE":
                continue
            r = self.refs(b)
            a = self.axis(r[0]) if r else None
            if not a or not a[0]:
                continue
            loc, direction = a
            ax = max(range(3), key=lambda k: abs(direction[k]))
            key = (round(self.nums(b)[-1], 2), "XYZ"[ax] + ("+" if direction[ax] >= 0 else "-"),
                   round(loc[0], 2), round(loc[1], 2), round(loc[2], 2))
            found[key] += 1
        return found

    def planes(self):
        out = []
        for surface, bounds in self.faces():
            if surface != "PLANE":
                continue
            for bound in bounds:
                out.append(bound)
        rows = []
        for i, (t, b) in self.ents.items():
            if t != "PLANE":
                continue
            a = self.axis(self.refs(b)[0]) if self.refs(b) else None
            if a and a[0]:
                loc, direction = a
                ax = max(range(3), key=lambda k: abs(direction[k]))
                rows.append((round(loc[ax], 2), "XYZ"[ax] + ("+" if direction[ax] >= 0 else "-")))
        return rows


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    length = math.sqrt(_dot(a, a)) or 1.0
    return _mul(a, 1.0 / length)


def cmd_summary(step, args):
    print("entities:", len(step.ents))
    print("top types:")
    for name, count in Counter(t for t, _ in step.ents.values()).most_common(8):
        print(f"  {count:7d}  {name}")
    print("solids:", len(step.solids()))
    print("vertices:", len(step.vertices()), " faces:", len(step.faces()))
    lo, hi = step.bbox()
    print("bbox min:", [round(v, 3) for v in lo])
    print("bbox max:", [round(v, 3) for v in hi])
    print("bbox size:", [round(hi[i] - lo[i], 3) for i in range(3)])


def cmd_features(step, args):
    print("=== circles: radius, axis, centre ===")
    for (radius, axis, x, y, z), count in sorted(step.circles().items()):
        print(f"  d={2 * radius:7.2f}  axis={axis}  centre=({x:8.2f},{y:7.2f},{z:8.2f})  arcs={count}")
    print("\n=== plane offsets by normal ===")
    by_normal = defaultdict(list)
    for offset, normal in step.planes():
        by_normal[normal].append(offset)
    for normal in sorted(by_normal):
        values = sorted(Counter(by_normal[normal]).items())
        print(f"  {normal}: " + ", ".join(f"{o:g}x{n}" for o, n in values))


def cmd_render(step, args):
    from PIL import Image, ImageDraw  # noqa: F401  (import here so summary needs no Pillow)

    faces = step.faces()
    size = args.size
    views = {
        "top": (lambda p: (p[0], p[2]), lambda p: p[1]),
        "front": (lambda p: (p[0], p[1]), lambda p: p[2]),
        "side": (lambda p: (p[2], p[1]), lambda p: p[0]),
    }
    right = (1 / math.sqrt(2), 0.0, -1 / math.sqrt(2))
    up = (-1 / math.sqrt(6), 2 / math.sqrt(6), -1 / math.sqrt(6))
    view = (1 / math.sqrt(3),) * 3
    views["iso"] = (lambda p: (_dot(p, right), _dot(p, up)), lambda p: _dot(p, view))

    for name, (project, nearness) in views.items():
        _raster(faces, project, nearness, size, args.cut, f"{args.out}_{name}.png")


def _raster(faces, project, nearness, size, cut, path):
    from PIL import Image

    if cut is not None:
        faces = [(s, b) for s, b in faces
                 if min(p[1] for bound in b for p in bound) <= cut]
    projected = [[[project(p) for p in bound] for bound in bounds] for _, bounds in faces]
    us = [p[0] for f in projected for b in f for p in b]
    vs = [p[1] for f in projected for b in f for p in b]
    if not us:
        print("nothing to draw for", path)
        return
    scale = (size - 80) / max(max(us) - min(us), max(vs) - min(vs), 1e-9)
    ox = 40 + (size - 80 - (max(us) - min(us)) * scale) / 2 - min(us) * scale
    oy = 40 + (size - 80 - (max(vs) - min(vs)) * scale) / 2 - min(vs) * scale
    px = [[[(p[0] * scale + ox, size - (p[1] * scale + oy)) for p in bound]
           for bound in f] for f in projected]

    values = [nearness(p) for _, bounds in faces for bound in bounds for p in bound]
    lo, span = min(values), (max(values) - min(values)) or 1.0

    img = Image.new("RGB", (size, size), "white")
    pixels = img.load()
    zbuf = [[None] * size for _ in range(size)]

    for index, (surface, bounds) in enumerate(faces):
        near = sum(nearness(p) for bound in bounds for p in bound) / sum(len(b) for b in bounds)
        base = {"PLANE": 170, "CYLINDRICAL_SURFACE": 205,
                "CONICAL_SURFACE": 215}.get(surface, 225)
        shade = max(50, min(245, int(base - 40 + (near - lo) / span * 60)))
        rings = px[index]
        outer = rings[0]
        xs = [p[0] for p in outer]
        ys = [p[1] for p in outer]
        x0, x1 = max(0, int(min(xs))), min(size - 1, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys))), min(size - 1, int(max(ys)) + 1)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if not _inside(outer, x + 0.5, y + 0.5):
                    continue
                if any(_inside(ring, x + 0.5, y + 0.5) for ring in rings[1:]):
                    continue
                current = zbuf[y][x]
                if current is None or near > current:
                    zbuf[y][x] = near
                    pixels[x, y] = (shade, shade, shade)
    img.save(path)
    print("wrote", path)


def _inside(polygon, x, y):
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("summary", help="entity counts and the exact bounding box")
    p.add_argument("step")
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("features", help="circles and plane offsets")
    p.add_argument("step")
    p.set_defaults(func=cmd_features)

    p = sub.add_parser("render", help="top/front/side/isometric PNGs")
    p.add_argument("step")
    p.add_argument("--out", required=True, help="output path prefix")
    p.add_argument("--size", type=int, default=900)
    p.add_argument("--cut", type=float, default=None,
                   help="skip faces entirely above this Y, to read a plan at one level")
    p.set_defaults(func=cmd_render)

    args = parser.parse_args(argv)
    step = Step(args.step)
    args.func(step, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
