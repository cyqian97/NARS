"""LaTeX/TikZ utilities: generate standalone sensor-HUD figures."""

import numbers
import math

# Single sensor colour matching svg_utils.COLOR_SENSOR_DEFAULT (#1a5fb4)
_SENSOR_RGB = (26, 95, 180)

# Proportional constants shared with generate_sensor_svg() in svg_utils.py
#   tick_frac  = radius * 0.2   (inward tick length)
#   dot_frac   = radius * 0.05  (centre-dot radius)
#   ring_lw    = radius * 0.015 (ring stroke, matching size*0.006 / radius)
#   tick_lw    = ring_lw * 2    (tick stroke, matching svg stroke_w*2)
_TICK_FRAC   = 0.20
_DOT_FRAC    = 0.05
_RING_LW_FRAC = 0.015
_MARGIN_FRAC  = 0.15


def generate_sensor_tex(gaps, radius_cm: float = 3.5) -> str:
    """Return a standalone LaTeX document with a TikZ gap-sensor figure.

    The output mirrors ``generate_sensor_svg`` exactly:
      - White background square.
      - Thin ring of *radius_cm* centred at the origin.
      - Filled dot at the origin.
      - One inward tick per gap (no colour distinction, no labels).

    Gap direction vectors are in SVG screen-space (Y down); Y is negated
    before use so ticks appear at the same visual angle in both outputs.

    Parameters
    ----------
    gaps:
        Iterable of Gap objects (need ``.dir``).
    radius_cm:
        Radius of the sensor ring in centimetres (default 3.5 cm).
    """
    tick_cm    = radius_cm * _TICK_FRAC
    dot_r_cm   = radius_cm * _DOT_FRAC
    ring_lw_pt = radius_cm * _RING_LW_FRAC * 28.3465   # cm → pt
    tick_lw_pt = ring_lw_pt * 2
    canvas_cm  = radius_cm * (1.0 + _MARGIN_FRAC)

    r, g, b = _SENSOR_RGB

    lines = [
        r'\documentclass{standalone}',
        r'\usepackage{tikz}',
        r'\usepackage{xcolor}',
        rf'\definecolor{{sensorblue}}{{RGB}}{{{r},{g},{b}}}',
        r'\begin{document}',
        r'\begin{tikzpicture}',
        f'  \\fill[white]'
        f' ({-canvas_cm:.4f}cm,{-canvas_cm:.4f}cm)'
        f' rectangle ({canvas_cm:.4f}cm,{canvas_cm:.4f}cm);',
        f'  \\draw[sensorblue, line width={ring_lw_pt:.2f}pt]'
        f' (0,0) circle ({radius_cm:.4f}cm);',
        f'  \\fill[sensorblue] (0,0) circle ({dot_r_cm:.4f}cm);',
    ]

    for gap in gaps:
        if hasattr(gap, 'dir'):
            dx =  float(gap.dir[0])
            dy = -float(gap.dir[1])   # flip Y: SVG screen-space → TikZ math-space
        else:
            dx = math.cos(float(gap)/180.0*math.pi)
            dy = -math.sin(float(gap)/180.0*math.pi)

        x1 = radius_cm * dx
        y1 = radius_cm * dy
        x2 = (radius_cm - tick_cm) * dx
        y2 = (radius_cm - tick_cm) * dy

        lines.append(
            f'  \\draw[sensorblue, line width={tick_lw_pt:.2f}pt]'
            f' ({x1:.4f}cm,{y1:.4f}cm) -- ({x2:.4f}cm,{y2:.4f}cm);'
        )

    lines += [
        r'\end{tikzpicture}',
        r'\end{document}',
    ]
    return '\n'.join(lines)

if __name__ == "__main__":
    # Example usage: python utils/tex_utils.py 0 30 60
    import argparse

    parser = argparse.ArgumentParser(description="Generate a standalone LaTeX document with a TikZ sensor figure.")
    parser.add_argument("gaps", nargs="+", help="Gap directions (degrees)")
    parser.add_argument("--radius", type=float, default=3.5, help="Sensor ring radius in cm (default 3.5)")
    parser.add_argument("--output", type=str, default="sensor.tex", help="Output file path")
    args = parser.parse_args()
    tex_code = generate_sensor_tex(args.gaps, radius_cm=args.radius)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(tex_code)