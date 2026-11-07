"""Bland–Altman plotting without optional plotting libraries."""
from __future__ import annotations

from html import escape
from pathlib import Path


def plot_bland_altman(pairs: list[dict], output_svg: str | Path) -> Path:
    """Write a self-contained Bland–Altman SVG (difference vs pair mean)."""
    if not pairs:
        raise ValueError("At least one matched pair is required")
    errors = [pair["error_bpm"] for pair in pairs]
    means = [(pair["wifi_bpm"] + pair["reference_bpm"]) / 2 for pair in pairs]
    bias = sum(errors) / len(errors)
    sd = (sum((error - bias) ** 2 for error in errors) / (len(errors) - 1)) ** 0.5 if len(errors) > 1 else 0.0
    lo, hi = min(errors + [bias - 1.96 * sd]), max(errors + [bias + 1.96 * sd])
    if hi == lo:
        hi += 1
        lo -= 1
    xmin, xmax = min(means), max(means)
    if xmax == xmin:
        xmin -= 1
        xmax += 1
    width, height = 900, 560
    left, right, top, bottom = 85, 30, 60, 75
    plot_w, plot_h = width - left - right, height - top - bottom
    x = lambda val: left + (val - xmin) / (xmax - xmin) * plot_w
    y = lambda val: top + (hi - val) / (hi - lo) * plot_h
    def line(val: float, color: str, dash: str = "") -> str:
        pattern = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<line x1="{left}" y1="{y(val):.2f}" x2="{width-right}" y2="{y(val):.2f}" stroke="{color}"{pattern}/>'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="Arial, sans-serif" fill="#222">',
             '<text x="450" y="30" text-anchor="middle" font-size="20">Bland–Altman: Wi-Fi BPM vs pulse-oximeter</text>',
             f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
             f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>']
    for i in range(6):
        value = lo + (hi-lo) * i/5
        yy = y(value)
        parts.extend([f'<line x1="{left-5}" y1="{yy:.2f}" x2="{width-right}" y2="{yy:.2f}" stroke="#ddd"/>',
                      f'<text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" font-size="12">{value:.1f}</text>'])
    for val, color, dash in [(bias, "#e87500", ""), (bias + 1.96*sd, "#c33434", "7 5"), (bias - 1.96*sd, "#c33434", "7 5")]:
        parts.append(line(val, color, dash))
    for mx, err in zip(means, errors):
        parts.append(f'<circle cx="{x(mx):.2f}" cy="{y(err):.2f}" r="4" fill="#2878b5" fill-opacity="0.75"/>')
    parts.extend([f'<text x="{left+plot_w/2:.1f}" y="{height-20}" text-anchor="middle" font-size="14">Mean BPM of each matched pair</text>',
                  f'<text x="20" y="{top+plot_h/2:.1f}" transform="rotate(-90 20 {top+plot_h/2:.1f})" text-anchor="middle" font-size="14">Wi-Fi − reference (BPM)</text>',
                  f'<text x="{width-right-5}" y="{y(bias)-7:.1f}" text-anchor="end" font-size="12" fill="#e87500">Bias {bias:.2f} BPM</text>',
                  '<text x="450" y="52" text-anchor="middle" font-size="12" fill="#c33434">Dashed lines: 95% limits of agreement</text>',
                  '</g></svg>'])
    output = Path(output_svg)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
    return output