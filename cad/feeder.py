"""
Fuglekiggeren — a bird feeder that houses a eufyCam 2C Pro.

Parametric model written with build123d. All dimensions in millimetres.

World axes
  X  width  (left / right)
  Y  depth  (0 = back of the wall plate, the feeder opens towards -Y)
  Z  height (0 = underside of the floor)

Parts
  hood      ribbed, house-shaped shell (sand colour)
  base      wall plate + floor with tray rails, camera slot, keyholes, strap slots
  window    divider between the dry camera bay and the feeding area
  carriage  L-bracket holding the camera by its rear 1/4"-20 thread; slides in Y
  tray      removable seed tray with drain holes and a perch bar that doubles as handle
"""

from math import sqrt

from build123d import (
    Align, Axis, Box, Color, Compound, Cylinder, FilletPolyline, Plane, Polygon,
    Pos, Rectangle, RectangleRounded, Rot, SlotCenterToCenter, Circle, extrude, sweep,
)

# ---------------------------------------------------------------- parameters
CAM_W, CAM_H, CAM_D = 48.0, 80.6, 57.0   # eufyCam 2C Pro body
CAM_THREAD_Z = 40.0      # 1/4"-20 thread height above camera bottom (measure yours!)
USB_CLEAR = 35.0         # space under the camera for the micro-USB plug + cable bend

W = 130.0                # hood inner width
H = 135.0                # hood inner height at the eaves
RISE = 35.0              # roof rise from eaves to ridge
R_CORNER = 18.0          # inner fillet at eaves and ridge
T = 3.0                  # hood wall thickness
D = 220.0                # hood depth

RIB_R = 3.5              # rib tube radius (half sits proud of the shell)
RIB_PITCH = 12.0         # rib spacing
DRIP_R = 5.0             # bigger front rib = drip edge

PLATE_T = 5.0            # wall plate thickness
LIP_D = 8.0              # depth of the lip the hood slides over
FLOOR_T = 4.0            # floor thickness
RAIL_W, RAIL_H = 4.0, 10.0
FIT = 0.3                # sliding clearance

ADJUST = 40.0            # camera fore/aft adjustment travel
WINDOW_T = 3.0

TRAY_WALL = 2.0
TRAY_H = 12.0
PERCH_D = 8.0
PERCH_RAISE = 10.0

M5 = 5.4                 # carriage bolt clearance
QUARTER_20 = 6.8         # 1/4" camera screw clearance

# ---------------------------------------------------------------- derived
Y_HOOD_BACK = -PLATE_T                       # hood butts against the plate
Y_HOOD_FRONT = Y_HOOD_BACK - D
Z_CAM = FLOOR_T + USB_CLEAR                  # camera bottom
Z_THREAD = Z_CAM + CAM_THREAD_Z
# carriage plate front face (camera back) travels between these
YP_MAX = Y_HOOD_BACK - LIP_D - 1.0 - 5.0     # furthest back
YP_MIN = YP_MAX - ADJUST                     # furthest forward
Y_WINDOW = YP_MIN - CAM_D - 2.0 - WINDOW_T / 2
FLOOR_W = W - 2 * FIT

HEX = {
    "hood": 0xD8C8A6,      # sand / oat
    "base": 0x3B3E42,      # charcoal
    "window": 0x3B3E42,
    "carriage": 0x55595E,
    "tray": 0x2E3134,
    "camera": 0xF2F2F0,    # reference only, not printed
}
COLORS = {k: Color(v) for k, v in HEX.items()}


# ---------------------------------------------------------------- helpers
def house_pts(t: float, z0: float = 0.0):
    """Open U outline (bottom-left -> ridge -> bottom-right) of the inner house
    offset outward by t (negative = inward). Coordinates are (x, z)."""
    half = W / 2
    L = sqrt(RISE ** 2 + half ** 2)
    nx, nz = RISE / L, half / L
    c = (nx * half + nz * H) + t

    def roof_z(x):
        return (c - nx * x) / nz

    xo = half + t
    return [(-xo, z0), (-xo, roof_z(xo)), (0.0, roof_z(0.0)), (xo, roof_z(xo)), (xo, z0)]


def house_face(t: float, z0: float = 0.0):
    pts = house_pts(t, z0)
    face = Polygon(*pts, align=None).face()
    top = [v for v in face.vertices() if v.Y > z0 + 1]
    return face.fillet_2d(max(R_CORNER + t, 0.5), top)


def extrude_y(face, y: float, depth: float):
    """Place a 2D (x, z) face on the vertical plane at depth y and extrude it
    `depth` mm towards the front (-Y)."""
    return extrude(Plane.XZ.offset(-y) * face, amount=depth, dir=(0, -1, 0))


# ---------------------------------------------------------------- parts
def make_hood():
    outer = house_face(T)
    inner = house_face(0.0, z0=-5.0)
    shell = extrude_y(outer - inner, Y_HOOD_BACK, D)

    ribs = []
    n = int((D - 2 * RIB_PITCH) // RIB_PITCH)
    ys = [Y_HOOD_BACK - RIB_PITCH * (i + 1) for i in range(n)]
    for y in ys:
        ribs.append(_rib(y, RIB_R))
    ribs.append(_rib(Y_HOOD_FRONT + DRIP_R, DRIP_R))     # drip edge at the front
    ribs.append(_rib(Y_HOOD_BACK - RIB_R, RIB_R))         # neat back edge
    hood = shell
    for r in ribs:
        hood = hood + r

    # screw holes into the floor rails (M3 self-tapping)
    z = FLOOR_T + RAIL_H / 2
    for y in (Y_HOOD_BACK - 20, Y_HOOD_FRONT + 20):
        hood = hood - Pos(0, y, z) * Rot(0, 90, 0) * Cylinder(1.7, W + 4 * T + 20)
    return hood


def _rib(y: float, r: float):
    pts = [(x, y, z) for x, z in house_pts(T)]
    path = FilletPolyline(*pts, radius=R_CORNER + T)
    section = Plane(origin=pts[0], z_dir=(0, 0, 1)) * Circle(r)
    return sweep(section, path)


def make_base():
    rim = RIB_R + 1.0
    plate = extrude_y(house_face(T + rim), 0.0, PLATE_T)
    lip = extrude_y(house_face(-FIT) - house_face(-FIT - 3.0, z0=-5), Y_HOOD_BACK, LIP_D)
    floor = Pos(0, Y_HOOD_BACK, 0) * Box(FLOOR_W, D, FLOOR_T, align=(Align.CENTER, Align.MAX, Align.MIN))
    rails = [
        Pos(sx * (FLOOR_W / 2 - RAIL_W / 2), Y_HOOD_BACK, FLOOR_T)
        * Box(RAIL_W, D, RAIL_H, align=(Align.CENTER, Align.MAX, Align.MIN))
        for sx in (-1, 1)
    ]
    base = plate + lip + floor + rails[0] + rails[1]

    # groove for the window divider
    base -= Pos(0, Y_WINDOW, FLOOR_T - 2) * Box(W, WINDOW_T + 2 * FIT, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # camera carriage slot (two bolts ride in it)
    y0, y1 = YP_MIN - 30, YP_MAX - 10
    slot = SlotCenterToCenter(abs(y1 - y0), M5).rotate(Axis.Z, 90)
    base -= Pos(0, (y0 + y1) / 2, 0) * extrude(slot, amount=FLOOR_T)

    # drain holes in the feeding area floor
    for ix in range(-6, 7):
        for iy in range(1, 13):
            y = Y_WINDOW - 6 - iy * 7.5
            if y < Y_HOOD_FRONT + 6:
                continue
            base -= Pos(ix * 8, y, 0) * Cylinder(1.75, FLOOR_T, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # cable exit: notch through lip and plate, low on the right
    base -= Pos(40, 1, FLOOR_T) * Box(12, PLATE_T + LIP_D + 2, 10, align=(Align.CENTER, Align.MAX, Align.MIN))

    # keyholes for wall screws (head drops in the big hole, slides down)
    for sx in (-1, 1):
        x = sx * 35
        kh = Pos(x, 0, 112) * Cylinder(4.75, 30, rotation=(90, 0, 0)) \
            + Pos(x, 0, 104) * Box(4.6, 30, 16, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        base -= kh
    # strap slots for a tree strap (25 mm webbing)
    for sx in (-1, 1):
        base -= Pos(sx * (W / 2 - 14), 0, 70) * Box(4.5, 30, 30)
    return base


def make_window():
    divider = house_face(-0.4) - Rectangle(W * 2, 4, align=(Align.CENTER, Align.MAX))
    win = Pos(0, Z_CAM + CAM_H / 2) * RectangleRounded(CAM_W - 4, CAM_H - 6, 8)
    face = divider - win
    # sit 2 mm down in the floor groove
    face = Pos(0, FLOOR_T - 2) * (face - Rectangle(W * 2, 10, align=(Align.CENTER, Align.MAX)))
    return extrude_y(face, Y_WINDOW + WINDOW_T / 2, WINDOW_T)


def make_carriage(yp: float = YP_MAX):
    """yp = Y of the camera's back face; default = furthest back."""
    foot = Pos(0, yp + 5, FLOOR_T) * Box(40, 45, 5, align=(Align.CENTER, Align.MAX, Align.MIN))
    plate_h = Z_THREAD + 15 - FLOOR_T
    plate = Pos(0, yp, FLOOR_T) * Box(CAM_W, 5, plate_h, align=(Align.CENTER, Align.MIN, Align.MIN))
    gussets = [
        Pos(sx * 15, yp, FLOOR_T + 5) * _gusset() for sx in (-1, 1)
    ]
    c = foot + plate + gussets[0] + gussets[1]
    c -= Pos(0, yp, Z_THREAD) * Cylinder(QUARTER_20 / 2, 30, rotation=(90, 0, 0))
    for dy in (-10, -30):
        c -= Pos(0, yp + dy, 0) * Cylinder(M5 / 2, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return c


def _gusset():
    """Triangular brace in front of the carriage plate, under the camera."""
    tri = Polygon((0, 0), (0, 25), (-25, 0), align=None)    # local (y, z)
    return extrude(Plane.YZ * tri, amount=1.5, both=True)


def make_tray():
    inner_w = FLOOR_W - 2 * RAIL_W - 2 * 0.5
    y_back = Y_WINDOW - WINDOW_T / 2 - 0.5
    y_front = Y_HOOD_FRONT - 6
    length = y_back - y_front
    outer = Pos(0, y_back, FLOOR_T) * Box(inner_w, length, TRAY_H, align=(Align.CENTER, Align.MAX, Align.MIN))
    cavity = Pos(0, y_back - TRAY_WALL, FLOOR_T + 2) * Box(
        inner_w - 2 * TRAY_WALL, length - 2 * TRAY_WALL, TRAY_H, align=(Align.CENTER, Align.MAX, Align.MIN))
    tray = outer - cavity
    for ix in range(-6, 7):
        for iy in range(0, 14):
            y = y_back - 8 - iy * 7
            if y < y_front + 6:
                continue
            tray -= Pos(ix * 8, y, FLOOR_T) * Cylinder(1.5, 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # perch / handle across the front
    zp = FLOOR_T + TRAY_H + PERCH_RAISE
    yp = y_front + TRAY_WALL / 2
    for sx in (-1, 1):
        tray += Pos(sx * (inner_w / 2 - 6), yp, FLOOR_T + TRAY_H - 1) * Cylinder(
            3, PERCH_RAISE + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    tray += Pos(0, yp, zp) * Cylinder(PERCH_D / 2, inner_w - 4, rotation=(0, 90, 0))
    return tray


def make_camera_dummy(yp: float = YP_MAX):
    body = Pos(0, yp, Z_CAM) * Box(CAM_W, CAM_D, CAM_H, align=(Align.CENTER, Align.MAX, Align.MIN))
    lens = Pos(0, yp - CAM_D, Z_CAM + CAM_H - 22) * Cylinder(9, 2, rotation=(90, 0, 0))
    cam = body + lens
    return cam


def build_all():
    parts = {
        "hood": make_hood(),
        "base": make_base(),
        "window": make_window(),
        "carriage": make_carriage(),
        "tray": make_tray(),
    }
    for name, p in parts.items():
        p.color = COLORS[name]
        p.label = name
    return parts


if __name__ == "__main__":
    for name, p in build_all().items():
        bb = p.bounding_box()
        print(f"{name:9s} valid={p.is_valid} size={bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}")
