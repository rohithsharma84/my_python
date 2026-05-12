"""
Programmatic icon generation using QPainter.
All functions return QPixmap drawn on a transparent background.
"""
from PyQt6.QtCore import Qt, QLineF, QPointF, QRectF
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QPixmap, QBrush, QPainterPath, QFont, QPolygonF
)

# ── LiquidState integer constants (mirrors ember_mug.consts.LiquidState) ──
LS_STANDBY = 0
LS_EMPTY = 1
LS_FILLING = 2
LS_COLD = 3
LS_COOLING = 4
LS_HEATING = 5
LS_PERFECT = 6
LS_WARM = 7

STATE_LABELS = {
    LS_STANDBY: "Standby",
    LS_EMPTY: "Empty",
    LS_FILLING: "Filling",
    LS_COLD: "Cold",
    LS_COOLING: "Cooling",
    LS_HEATING: "Heating",
    LS_PERFECT: "Perfect",
    LS_WARM: "Warm",
}

# Colour palette
COL_BT_ON = QColor("#00AAFF")
COL_BT_OFF = QColor("#666666")
COL_BAT_BODY = QColor("#CCCCCC")
COL_BAT_FILL_OK = QColor("#44CC44")
COL_BAT_FILL_LOW = QColor("#FF4444")
COL_BAT_CHARGE = QColor("#FFD700")
COL_COOLING = QColor("#55AAFF")
COL_HEATING = QColor("#FF7722")
COL_PERFECT = QColor("#44DD44")
COL_STANDBY = QColor("#AAAAAA")
COL_EMPTY = QColor("#FF5555")
COL_FILLING = QColor("#55AAFF")
COL_WARM = QColor("#FFCC55")
COL_LEVEL = QColor("#55AAEE")
COL_CUP = QColor("#BBBBBB")


def _new_pixmap(size: int) -> tuple[QPixmap, QPainter]:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return px, p


def _scale(val: float, size: int) -> float:
    return val * size


def bluetooth_icon(size: int, connected: bool) -> QPixmap:
    px, p = _new_pixmap(size)
    color = COL_BT_ON if connected else COL_BT_OFF
    w = max(1.5, size * 0.07)
    pen = QPen(color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    s = float(size)
    cx = s * 0.50   # center x for spine

    # Vertical spine
    p.drawLine(QLineF(cx, s * 0.04, cx, s * 0.96))

    # Upper right wing: top → right-upper → center
    p.drawLine(QLineF(cx, s * 0.04, s * 0.85, s * 0.30))
    p.drawLine(QLineF(s * 0.85, s * 0.30, cx, s * 0.50))

    # Lower right wing: center → right-lower → bottom
    p.drawLine(QLineF(cx, s * 0.50, s * 0.85, s * 0.70))
    p.drawLine(QLineF(s * 0.85, s * 0.70, cx, s * 0.96))

    # Left stubs: extensions of the inner triangle sides from the center junction.
    # Upper inner side direction: (0.85,0.30)→(0.50,0.50), i.e. Δ(-0.35,+0.20).
    # Extended past center → goes left-downward.
    p.drawLine(QLineF(cx, s * 0.50, s * 0.20, s * 0.63))
    # Lower inner side direction: (0.50,0.50)→(0.85,0.70), reversed Δ(-0.35,-0.20).
    # Extended past center → goes left-upward.
    p.drawLine(QLineF(cx, s * 0.50, s * 0.20, s * 0.37))

    p.end()
    return px


def battery_icon(size: int, level: float, charging: bool) -> QPixmap:
    """level: 0.0–100.0"""
    px, p = _new_pixmap(size)
    s = float(size)

    body_x = s * 0.05
    body_y = s * 0.22
    body_w = s * 0.78
    body_h = s * 0.56

    term_x = s * 0.84
    term_y = s * 0.38
    term_w = s * 0.11
    term_h = s * 0.24

    # Battery terminal (positive nub)
    p.setBrush(QBrush(COL_BAT_BODY))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(term_x, term_y, term_w, term_h), 2, 2)

    # Battery body outline
    outline_pen = QPen(COL_BAT_BODY, max(1.0, s * 0.05))
    p.setPen(outline_pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(body_x, body_y, body_w, body_h), 3, 3)

    # Fill
    inset = max(1.5, s * 0.07)
    fill_x = body_x + inset
    fill_y = body_y + inset
    fill_h = body_h - 2 * inset
    max_fill_w = body_w - 2 * inset
    fill_w = max_fill_w * (max(0.0, min(100.0, level)) / 100.0)

    fill_color = COL_BAT_FILL_LOW if level < 20 else COL_BAT_FILL_OK
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(fill_color))
    if fill_w > 0:
        p.drawRoundedRect(QRectF(fill_x, fill_y, fill_w, fill_h), 2, 2)

    # Lightning bolt when charging
    if charging:
        bolt = QPainterPath()
        cx = body_x + body_w * 0.5
        cy = body_y + body_h * 0.5
        bw = body_w * 0.28
        bh = body_h * 0.78
        bolt.moveTo(cx + bw * 0.15, cy - bh * 0.5)
        bolt.lineTo(cx - bw * 0.20, cy + bh * 0.05)
        bolt.lineTo(cx + bw * 0.10, cy + bh * 0.05)
        bolt.lineTo(cx - bw * 0.15, cy + bh * 0.5)
        bolt.lineTo(cx + bw * 0.30, cy - bh * 0.05)
        bolt.lineTo(cx - bw * 0.05, cy - bh * 0.05)
        bolt.closeSubpath()
        p.setBrush(QBrush(COL_BAT_CHARGE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(bolt)

    p.end()
    return px


def _draw_snowflake(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    w = max(1.0, r * 0.18)
    pen = QPen(color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    import math
    for angle_deg in [0, 60, 120]:
        rad = math.radians(angle_deg)
        dx, dy = math.cos(rad) * r, math.sin(rad) * r
        p.drawLine(QLineF(cx - dx, cy - dy, cx + dx, cy + dy))
        # Small crossbars at 60% along each arm
        for sign in [1, -1]:
            ax = cx + sign * dx * 0.55
            ay = cy + sign * dy * 0.55
            perp_rad = math.radians(angle_deg + 90)
            pb = r * 0.22
            pdx, pdy = math.cos(perp_rad) * pb, math.sin(perp_rad) * pb
            p.drawLine(QLineF(ax - pdx, ay - pdy, ax + pdx, ay + pdy))


def _draw_flame(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    path = QPainterPath()
    # Flame: upward teardrop with wavy base
    path.moveTo(cx, cy - r * 0.9)
    path.cubicTo(cx + r * 0.6, cy - r * 0.3, cx + r * 0.5, cy + r * 0.4, cx, cy + r * 0.9)
    path.cubicTo(cx - r * 0.5, cy + r * 0.4, cx - r * 0.6, cy - r * 0.3, cx, cy - r * 0.9)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(color))
    p.drawPath(path)

    # Inner highlight
    inner = QPainterPath()
    inner.moveTo(cx, cy - r * 0.45)
    inner.cubicTo(cx + r * 0.22, cy, cx + r * 0.18, cy + r * 0.35, cx, cy + r * 0.55)
    inner.cubicTo(cx - r * 0.18, cy + r * 0.35, cx - r * 0.22, cy, cx, cy - r * 0.45)
    lighter = QColor(color)
    lighter.setAlpha(120)
    p.setBrush(QBrush(QColor("#FFEE99")))
    p.drawPath(inner)


def _draw_checkmark(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    pen = QPen(color, max(2.0, r * 0.28), Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(QLineF(cx - r * 0.7, cy, cx - r * 0.1, cy + r * 0.6))
    p.drawLine(QLineF(cx - r * 0.1, cy + r * 0.6, cx + r * 0.7, cy - r * 0.6))


def _draw_moon(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    path = QPainterPath()
    path.moveTo(cx - r * 0.1, cy - r)
    path.arcTo(QRectF(cx - r, cy - r, 2 * r, 2 * r), 80, -220)
    path.cubicTo(cx - r * 0.8, cy + r * 0.3, cx - r * 0.8, cy - r * 0.6, cx - r * 0.1, cy - r)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(color))
    p.drawPath(path)


def _draw_empty_cup_x(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    pen = QPen(color, max(1.5, r * 0.18), Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    # Cup outline (trapezoid)
    top_w = r * 0.9
    bot_w = r * 0.55
    top_y = cy - r * 0.7
    bot_y = cy + r * 0.8
    p.drawLine(QLineF(cx - top_w, top_y, cx - bot_w, bot_y))
    p.drawLine(QLineF(cx + top_w, top_y, cx + bot_w, bot_y))
    p.drawLine(QLineF(cx - bot_w, bot_y, cx + bot_w, bot_y))
    # X mark
    xr = r * 0.35
    xc_y = cy - r * 0.05
    p.drawLine(QLineF(cx - xr, xc_y - xr, cx + xr, xc_y + xr))
    p.drawLine(QLineF(cx + xr, xc_y - xr, cx - xr, xc_y + xr))


def _draw_steam(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    pen = QPen(color, max(1.5, r * 0.18), Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    for i, offset in enumerate([-0.35, 0.0, 0.35]):
        x = cx + offset * r
        y_start = cy + r * 0.5
        path = QPainterPath()
        path.moveTo(x, y_start)
        path.cubicTo(x + r * 0.2, y_start - r * 0.3,
                     x - r * 0.2, y_start - r * 0.6,
                     x, y_start - r * 0.9)
        p.drawPath(path)


def liquid_state_icon(size: int, state: int) -> QPixmap:
    px, p = _new_pixmap(size)
    s = float(size)
    cx, cy, r = s * 0.5, s * 0.5, s * 0.38

    if state == LS_COOLING or state == LS_COLD:
        _draw_snowflake(p, cx, cy, r, COL_COOLING)
    elif state == LS_HEATING:
        _draw_flame(p, cx, cy, r, COL_HEATING)
    elif state == LS_PERFECT:
        _draw_checkmark(p, cx, cy, r, COL_PERFECT)
    elif state == LS_STANDBY:
        _draw_moon(p, cx, cy, r, COL_STANDBY)
    elif state == LS_EMPTY:
        _draw_empty_cup_x(p, cx, cy, r, COL_EMPTY)
    elif state == LS_FILLING:
        # Cup with upward arrow
        _draw_empty_cup_x(p, cx, cy + r * 0.3, r * 0.6, COL_FILLING)
        pen = QPen(COL_FILLING, max(1.5, s * 0.07),
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        ar = r * 0.4
        p.drawLine(QLineF(cx, cy - r * 0.9, cx, cy - r * 0.1))
        p.drawLine(QLineF(cx, cy - r * 0.9, cx - ar * 0.5, cy - r * 0.9 + ar * 0.5))
        p.drawLine(QLineF(cx, cy - r * 0.9, cx + ar * 0.5, cy - r * 0.9 + ar * 0.5))
    elif state == LS_WARM:
        _draw_steam(p, cx, cy, r, COL_WARM)
    else:
        # Fallback: question mark
        font = QFont("Arial", int(s * 0.5), QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QPen(COL_STANDBY))
        p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "?")

    p.end()
    return px


def liquid_level_icon(size: int, level: float) -> QPixmap:
    """level: 0.0–100.0"""
    px, p = _new_pixmap(size)
    s = float(size)

    top_w = s * 0.44
    bot_w = s * 0.27
    top_y = s * 0.08
    bot_y = s * 0.92
    cx = s * 0.50
    cup_h = bot_y - top_y

    # Compute fill height
    clamped = max(0.0, min(100.0, level))
    fill_ratio = clamped / 100.0

    # Build cup polygon for clipping
    cup_path = QPainterPath()
    cup_path.moveTo(cx - top_w, top_y)
    cup_path.lineTo(cx - bot_w, bot_y)
    cup_path.lineTo(cx + bot_w, bot_y)
    cup_path.lineTo(cx + top_w, top_y)
    cup_path.closeSubpath()

    p.setClipPath(cup_path)

    # Fill (from bottom)
    if fill_ratio > 0:
        fill_top_y = bot_y - cup_h * fill_ratio
        t = fill_ratio                    # interpolation factor
        fill_top_w = bot_w + (top_w - bot_w) * (1.0 - t)
        fill_poly = QPolygonF([
            QPointF(cx - fill_top_w, fill_top_y),
            QPointF(cx - bot_w, bot_y),
            QPointF(cx + bot_w, bot_y),
            QPointF(cx + fill_top_w, fill_top_y),
        ])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(COL_LEVEL))
        p.drawPolygon(fill_poly)

    p.setClipping(False)

    # Cup outline on top
    pen = QPen(COL_CUP, max(1.5, s * 0.06),
               Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(cx - top_w, top_y, cx - bot_w, bot_y))
    p.drawLine(QLineF(cx + top_w, top_y, cx + bot_w, bot_y))
    p.drawLine(QLineF(cx - bot_w, bot_y, cx + bot_w, bot_y))

    p.end()
    return px


def temp_icon(size: int) -> QPixmap:
    """A simple thermometer icon."""
    px, p = _new_pixmap(size)
    s = float(size)
    cx = s * 0.50

    bulb_r = s * 0.18
    bulb_cx = cx
    bulb_cy = s * 0.78
    tube_w = s * 0.14
    tube_top = s * 0.10
    tube_bot = bulb_cy - bulb_r * 0.6

    # Bulb
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor("#FF5555")))
    p.drawEllipse(QRectF(bulb_cx - bulb_r, bulb_cy - bulb_r, bulb_r * 2, bulb_r * 2))

    # Tube fill
    p.setBrush(QBrush(QColor("#FF5555")))
    p.drawRoundedRect(QRectF(cx - tube_w * 0.5, tube_top, tube_w, tube_bot - tube_top), tube_w * 0.4, tube_w * 0.4)

    # Tube outline
    pen = QPen(QColor("#CCCCCC"), max(1.0, s * 0.04))
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(cx - tube_w * 0.5, tube_top, tube_w, tube_bot - tube_top), tube_w * 0.4, tube_w * 0.4)
    p.drawEllipse(QRectF(bulb_cx - bulb_r, bulb_cy - bulb_r, bulb_r * 2, bulb_r * 2))

    p.end()
    return px
