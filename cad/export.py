"""Export every part for printing / editing and render preview images.

Outputs (relative to repo root):
  models/step/<part>.step        editable CAD (open in Layerling, Fusion, FreeCAD …)
  models/step/assembly.step      everything in place
  models/stl/<part>.stl          print-ready, already oriented for the bed
  models/3mf/<part>.3mf          same as STL, in 3MF (Bambu Studio friendly)
  models/3mf/all-parts.3mf       every part in one 3MF project
  models/web/assembly.glb        coloured assembly for the website 3D viewer
  models/web/<part>.glb          single parts for the website viewer
  img/render-*.png               preview renders
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from build123d import Compound, Mesher, Pos, Rot, export_gltf, export_step, export_stl
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import feeder as f

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "models"
IMG = ROOT / "img"

WEB_MESH = dict(linear_deflection=0.15, angular_deflection=0.4)

# how each part sits on the print bed
PRINT_ROT = {
    "hood": Rot(-90, 0, 0),      # stands on its back edge, ribs printed as rings
    "base": Rot(-90, 0, 0),      # wall plate flat on the bed
    "window": Rot(-90, 0, 0),    # flat
    "carriage": Rot(0, 0, 0),    # foot down
    "tray": Rot(0, 0, 0),        # bottom down
}


def on_bed(shape):
    bb = shape.bounding_box()
    return Pos(-bb.center().X, -bb.center().Y, -bb.min.Z) * shape


def tri_mesh(shape, tol=0.4):
    verts, tris = shape.tessellate(tol, 0.3)
    v = np.array([[p.X, p.Y, p.Z] for p in verts])
    return v[np.array(tris)]


def render(shapes_colors, path, elev=22, azim=-58, title=None):
    polys, cols = [], []
    light = np.array([-0.4, -0.7, 0.8])
    light /= np.linalg.norm(light)
    for shape, rgb in shapes_colors:
        t = tri_mesh(shape)
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        shade = 0.45 + 0.55 * np.clip(n @ light, 0, 1)
        polys.append(t)
        cols.append(np.clip(np.outer(shade, rgb), 0, 1))
    polys = np.concatenate(polys)
    cols = np.concatenate(cols)
    fig = plt.figure(figsize=(8, 8), dpi=110)
    ax = fig.add_subplot(projection="3d")
    ax.add_collection3d(Poly3DCollection(polys, facecolors=cols, edgecolors="none"))
    pts = polys.reshape(-1, 3)
    lo, hi = pts.min(0), pts.max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    if title:
        ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, transparent=True)
    plt.close(fig)


def rgb(name):
    h = f.HEX[name]
    return np.array([(h >> 16) & 255, (h >> 8) & 255, h & 255]) / 255


def main():
    for d in ("step", "stl", "3mf", "web"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    IMG.mkdir(exist_ok=True)

    parts = f.build_all()
    camera = f.make_camera_dummy()
    camera.color, camera.label = f.COLORS["camera"], "camera (reference only)"

    everything = Mesher()
    for name, part in parts.items():
        export_step(part, OUT / "step" / f"{name}.step")
        printable = on_bed(PRINT_ROT[name] * part)
        printable.color, printable.label = part.color, name
        export_stl(printable, OUT / "stl" / f"{name}.stl", tolerance=0.02, angular_tolerance=0.2)
        m = Mesher()
        m.add_shape(printable, linear_deflection=0.02, angular_deflection=0.2)
        m.write(str(OUT / "3mf" / f"{name}.3mf"))
        everything.add_shape(printable, linear_deflection=0.02, angular_deflection=0.2)
        export_gltf(part, str(OUT / "web" / f"{name}.glb"), binary=True, **WEB_MESH)
        bb = printable.bounding_box().size
        print(f"{name:9s} print size {bb.X:6.1f} x {bb.Y:6.1f} x {bb.Z:6.1f} mm")
    everything.write(str(OUT / "3mf" / "all-parts.3mf"))

    assembly = Compound(label="fuglekiggeren", children=list(parts.values()) + [camera])
    export_step(assembly, OUT / "step" / "assembly.step")
    export_gltf(assembly, str(OUT / "web" / "assembly.glb"), binary=True, **WEB_MESH)

    # renders
    render([(p, rgb(n)) for n, p in parts.items()] + [(camera, rgb("camera"))],
           IMG / "render-assembly.png")
    explode = {
        "hood": Pos(0, 0, 120), "base": Pos(0, 0, 0), "window": Pos(0, -40, 0),
        "carriage": Pos(0, 0, 0), "tray": Pos(0, -170, 0),
    }
    render([(explode[n] * p, rgb(n)) for n, p in parts.items()] + [(camera, rgb("camera"))],
           IMG / "render-exploded.png", elev=26)
    render([(p, rgb(n)) for n, p in parts.items() if n != "hood"] + [(camera, rgb("camera"))],
           IMG / "render-inside.png", elev=30, azim=-35)
    render([(parts["base"], rgb("base"))], IMG / "render-back.png", elev=15, azim=125)


if __name__ == "__main__":
    main()
