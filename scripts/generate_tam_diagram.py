"""
Generates Figure 8 (Technology Acceptance Model diagram) for the capstone
paper, replacing the old hand-made version.

2026-09-15 - the old diagram's final box was labeled "Actual System Use"
and every box carried explanatory subtext. Rebuilt to (a) use only the
five real TAM constructs actually measured by the current instrument
(Sean_TAM-Edited.docx) and Chapter 4's Tables 17-21 - Perceived Usefulness,
Perceived Ease-of-Use, Attitude, Behavior, Actual Usage - with box labels
matching those table captions exactly for internal consistency across the
paper, and (b) drop all in-box subtext per explicit instruction, main
construct word only. Same LSPU-adjacent palette/box style as the Chapter
1/3 conceptual diagrams (generate_conceptual_diagrams.py) so it reads as
part of the same figure set, not a mismatched import.

    python scripts/generate_tam_diagram.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Segoe UI", "Calibri", "Verdana", "DejaVu Sans", "Arial"]

FIG_DIR = os.path.join("reports", "figures")

ROYAL = "#1A4B8C"
ROYAL_SOFT = "#EDF2F9"
GOLD = "#B9852F"
GOLD_SOFT = "#FBF1DC"
FOREST = "#0D6B4D"
FOREST_SOFT = "#EAF6F1"
ORANGE = "#C4581E"
ORANGE_SOFT = "#FBEAE0"
INK = "#1B2A41"
MUTED = "#5B6B84"
WHITE = "#FFFFFF"
SHADOW = "#0A1220"


def box(ax, x, y, w, h, text, edge=ROYAL, fill=WHITE, fontsize=11.5, weight="bold",
        textcolor=INK, shadow=True, lw=1.8):
    if shadow:
        sh = FancyBboxPatch((x + 0.06, y - 0.06), w, h,
                             boxstyle="round,pad=0.02,rounding_size=0.1",
                             linewidth=0, facecolor=SHADOW, alpha=0.12, zorder=1)
        ax.add_patch(sh)
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                            linewidth=lw, edgecolor=edge, facecolor=fill, zorder=2)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, fontweight=weight, zorder=3)
    return (x, y, w, h)


def center_right(b):
    x, y, w, h = b
    return (x + w, y + h / 2)


def center_left(b):
    x, y, w, h = b
    return (x, y + h / 2)


def center_top(b):
    x, y, w, h = b
    return (x + w / 2, y + h)


def center_bottom(b):
    x, y, w, h = b
    return (x + w / 2, y)


def center(b):
    x, y, w, h = b
    return (x + w / 2, y + h / 2)


def arrow(ax, p0, p1, color=INK, lw=1.8):
    a = FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=16,
                         linewidth=lw, color=color, zorder=1, shrinkA=2, shrinkB=2,
                         capstyle="round", joinstyle="round")
    ax.add_patch(a)


def figure_tam_model():
    # 2026-09-15 rev.2 - rebuilt to match the user's explicit reference
    # template: no External Variables box (the instrument doesn't measure
    # one), a title banner, an enclosing frame, and full construct names
    # in each box (not single-word shorthand - "only the main word" meant
    # no added explanatory subtext, not truncating the construct's own
    # proper name). Same LSPU palette as the rest of the paper's figures
    # rather than the reference's arbitrary blue/purple/red/teal, for
    # visual consistency across the whole figure set.
    fig, ax = plt.subplots(figsize=(12.6, 4.4))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 4.8)
    ax.axis("off")

    # ---- boxes -------------------------------------------------------
    pu = box(ax, 0.75, 2.55, 2.45, 1.25, "Perceived\nUsefulness", edge=ROYAL, fill=ROYAL_SOFT, fontsize=11)
    peou = box(ax, 0.75, 0.35, 2.45, 1.25, "Perceived\nEase of Use", edge=ROYAL, fill=ROYAL_SOFT, fontsize=11)

    attitude = box(ax, 4.35, 1.85, 2.45, 1.25, "Attitude\nToward Usage", edge=GOLD, fill=GOLD_SOFT, fontsize=10.5)
    intention = box(ax, 7.75, 1.85, 2.5, 1.25, "Behavioral\nIntention to Use", edge=ORANGE, fill=ORANGE_SOFT, fontsize=10.2)
    actual = box(ax, 11.25, 1.85, 1.75, 1.25, "Actual\nUsage", edge=FOREST, fill=FOREST_SOFT, fontsize=10.8)

    # ---- connectors ----------------------------------------------------
    # PEOU -> PU
    arrow(ax, center_top(peou), center_bottom(pu))

    # PU / PEOU -> Attitude, converging onto two distinct points on
    # Attitude's actual left edge.
    att_x, att_y, att_w, att_h = attitude
    arrow(ax, center_right(pu), (att_x, att_y + att_h * 0.78))
    arrow(ax, center_right(peou), (att_x, att_y + att_h * 0.22))

    # Attitude -> Behavioral Intention -> Actual Usage
    arrow(ax, center_right(attitude), center_left(intention))
    arrow(ax, center_right(intention), center_left(actual))

    # PU also feeds Behavioral Intention directly (classic TAM: usefulness
    # has a direct path to intention, not only through attitude) - routed
    # as a right-angle elbow along the top of the frame, matching the
    # reference template, rather than a curved arc.
    pu_x, pu_y, pu_w, pu_h = pu
    in_x, in_y, in_w, in_h = intention
    elbow_y = 4.15
    top_mid_x = pu_x + pu_w * 0.75
    land_x = in_x + in_w * 0.35
    ax.plot([top_mid_x, top_mid_x], [pu_y + pu_h, elbow_y], color=MUTED, linewidth=1.6, zorder=1,
            solid_capstyle="round")
    ax.plot([top_mid_x, land_x], [elbow_y, elbow_y], color=MUTED, linewidth=1.6, zorder=1,
            solid_capstyle="round")
    arrow(ax, (land_x, elbow_y), (land_x, in_y + in_h), color=MUTED, lw=1.6)

    ax.text(0.1, 4.6, "Figure 8. Technology Acceptance Model Applied to TrainWise",
            ha="left", fontsize=14.5, color=INK, fontweight="bold")

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig8_tam_model.png")
    fig.savefig(out, dpi=230, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == "__main__":
    os.makedirs(FIG_DIR, exist_ok=True)
    figure_tam_model()
