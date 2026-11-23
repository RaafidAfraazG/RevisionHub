"""Generate a small watertight ASCII cylinder; no CAD or mesh dependencies."""

from math import cos, pi, sin, sqrt
from pathlib import Path


def write_demo_stl(path: Path):
    triangles = []
    for i in range(32):
        a, b = 2 * pi * i / 32, 2 * pi * (i + 1) / 32
        p, q = (20 * cos(a), 20 * sin(a), 0), (20 * cos(b), 20 * sin(b), 0)
        r, s = (*p[:2], 8), (*q[:2], 8)
        triangles.extend([(p, q, s), (p, s, r), ((0, 0, 0), q, p), ((0, 0, 8), r, s)])
    lines = ["solid revisionhub_demo_cylinder"]
    for a, b, c in triangles:
        u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        length = sqrt(sum(n*n for n in normal))
        lines.append("  facet normal " + " ".join(f"{n / length:.6f}" for n in normal))
        lines.append("    outer loop")
        lines.extend("      vertex " + " ".join(f"{n:.6f}" for n in vertex) for vertex in (a, b, c))
        lines.extend(["    endloop", "  endfacet"])
    lines.append("endsolid revisionhub_demo_cylinder")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


if __name__ == "__main__":
    write_demo_stl(Path(__file__).resolve().parent / "uploads" / "rim-101-demo.stl")
