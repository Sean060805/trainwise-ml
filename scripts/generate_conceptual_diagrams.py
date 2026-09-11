"""
Generates the Chapter 1/3 conceptual diagrams for the capstone paper,
reflecting the training-demand-aggregation pipeline that replaced the
old "recommend a free link -> employee sees it" design:

  Figure 1 - Conceptual Framework (Input-Process-Output)
  Figure 2 - System Architecture
  Figure 3 - System Flowchart (Employee / Dean / HR swimlanes)
  Figure 4 - Use Case Diagram

Revision 2 (2026-09-08): full visual redesign - drop shadows, elbow
(orthogonal) connectors, decision diamonds, flowchart terminators,
lane/section background bands, and a system font instead of the
default matplotlib sans - so the output reads like a diagram drafted
by a systems analyst in Visio/draw.io, not a quick AI plot. Same
LSPU-adjacent palette as the Chapter 4 ML figures.

    python scripts/generate_conceptual_diagrams.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse, Circle, Polygon
from matplotlib.lines import Line2D

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Segoe UI", "Calibri", "Verdana", "DejaVu Sans", "Arial"]

FIG_DIR = os.path.join("reports", "figures")

ROYAL = "#1A4B8C"
ROYAL_SOFT = "#EDF2F9"
GOLD = "#B9852F"
GOLD_SOFT = "#FBF1DC"
FOREST = "#0D6B4D"
FOREST_SOFT = "#EAF6F1"
INK = "#1B2A41"
MUTED = "#5B6B84"
GRID = "#E4D9C3"
WHITE = "#FFFFFF"
SHADOW = "#0A1220"


def shadow_patch(ax, path_patch_cls, *args, dx=0.055, dy=-0.055, alpha=0.12, **kwargs):
    kwargs = dict(kwargs)
    kwargs["facecolor"] = SHADOW
    kwargs["edgecolor"] = "none"
    kwargs["alpha"] = alpha
    kwargs["zorder"] = kwargs.get("zorder", 1) - 1
    return path_patch_cls(*args, **kwargs)


def box(ax, x, y, w, h, text, edge=ROYAL, fill=WHITE, fontsize=9.3, weight="normal",
        textcolor=INK, shadow=True, lw=1.7, align="center"):
    if shadow:
        sh = FancyBboxPatch((x + 0.06, y - 0.06), w, h,
                             boxstyle="round,pad=0.018,rounding_size=0.09",
                             linewidth=0, facecolor=SHADOW, alpha=0.10, zorder=1)
        ax.add_patch(sh)
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.018,rounding_size=0.09",
                            linewidth=lw, edgecolor=edge, facecolor=fill, zorder=2)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fontsize, color=textcolor, fontweight=weight, zorder=3, linespacing=1.35)
    return (x, y, w, h)


def pill(ax, x, y, w, h, text, fill=ROYAL, textcolor=WHITE, fontsize=9.5):
    sh = FancyBboxPatch((x + 0.05, y - 0.05), w, h, boxstyle="round,pad=0.02,rounding_size=0.5",
                         linewidth=0, facecolor=SHADOW, alpha=0.14, zorder=1)
    ax.add_patch(sh)
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.5",
                            linewidth=0, facecolor=fill, zorder=2)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            color=textcolor, fontweight="bold", zorder=3)


def diamond(ax, cx, cy, w, h, text, edge=GOLD, fill=GOLD_SOFT, fontsize=9.2, lw=1.7):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    sh = Polygon([(px + 0.06, py - 0.06) for px, py in pts], closed=True,
                 facecolor=SHADOW, edgecolor="none", alpha=0.10, zorder=1)
    ax.add_patch(sh)
    p = Polygon(pts, closed=True, edgecolor=edge, facecolor=fill, linewidth=lw, zorder=2)
    ax.add_patch(p)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, color=INK, zorder=3, linespacing=1.3)


def band(ax, x0, x1, y0, y1, fill):
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=fill, edgecolor="none", zorder=0))


def arrow(ax, p0, p1, color=INK, lw=1.5, style="-|>"):
    a = FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=13,
                         linewidth=lw, color=color, zorder=1, shrinkA=1, shrinkB=1,
                         capstyle="round", joinstyle="round")
    ax.add_patch(a)


def elbow(ax, p0, p1, color=INK, lw=1.5, first="v"):
    """Two-segment orthogonal connector with an arrowhead only on the final leg."""
    x0, y0 = p0
    x1, y1 = p1
    mid = (x0, y1) if first == "v" else (x1, y0)
    ax.plot([x0, mid[0]], [y0, mid[1]], color=color, linewidth=lw, zorder=1,
            solid_capstyle="round", solid_joinstyle="round")
    arrow(ax, mid, p1, color=color, lw=lw)


def route(ax, p0, p1, via_x, color=GOLD, lw=1.6):
    """Three-segment (horizontal-vertical-horizontal) connector along a
    dedicated vertical 'highway' at x=via_x that sits in a lane gap, so it
    never crosses through a box in an intervening lane."""
    x0, y0 = p0
    x1, y1 = p1
    ax.plot([x0, via_x], [y0, y0], color=color, linewidth=lw, zorder=1,
            solid_capstyle="round", solid_joinstyle="round")
    ax.plot([via_x, via_x], [y0, y1], color=color, linewidth=lw, zorder=1,
            solid_capstyle="round", solid_joinstyle="round")
    arrow(ax, (via_x, y1), p1, color=color, lw=lw)


def stick_actor(ax, x, y, label, color=ROYAL, scale=0.46):
    ax.add_patch(Circle((x + 0.03, y + scale * 1.6 - 0.03), scale * 0.32, facecolor=SHADOW,
                         edgecolor="none", alpha=0.12, zorder=2))
    head = Circle((x, y + scale * 1.6), scale * 0.32, edgecolor=color, facecolor=WHITE, linewidth=1.8, zorder=3)
    ax.add_patch(head)
    kw = dict(color=color, linewidth=1.8, zorder=3, solid_capstyle="round")
    ax.plot([x, x], [y + scale * 1.28, y + scale * 0.28], **kw)
    ax.plot([x - scale * 0.55, x + scale * 0.55], [y + scale * 0.9, y + scale * 0.9], **kw)
    ax.plot([x, x - scale * 0.5], [y + scale * 0.28, y - scale * 0.42], **kw)
    ax.plot([x, x + scale * 0.5], [y + scale * 0.28, y - scale * 0.42], **kw)
    ax.text(x, y - scale * 0.8, label, ha="center", va="top", fontsize=9.3, color=INK, fontweight="bold",
            linespacing=1.3)


def new_tag(ax, x, y):
    ax.text(x, y, "NEW", fontsize=7, color=WHITE, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.22", facecolor=GOLD, edgecolor="none"), zorder=4)


def line_label(ax, x, y, text, fontsize=8.2):
    """A small label meant to sit ON TOP of a connector line (e.g. a
    decision branch's yes/no) - carries its own opaque background so it
    stays legible regardless of exactly where the line falls under it,
    instead of relying on precise, fragile offset math."""
    ax.text(x, y, text, fontsize=fontsize, color=MUTED, style="italic", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none"), zorder=3)


def legend_swatches(ax, x, y, fontsize=9.8):
    items = [(ROYAL, WHITE, "Existing component"), (GOLD, GOLD_SOFT, "New / changed in this revision")]
    dx = 0
    for edge, fill, label in items:
        ax.add_patch(FancyBboxPatch((x + dx, y), 0.42, 0.28, boxstyle="round,pad=0.01,rounding_size=0.05",
                                     linewidth=1.4, edgecolor=edge, facecolor=fill, zorder=3))
        ax.text(x + dx + 0.56, y + 0.14, label, fontsize=fontsize, color=MUTED, va="center", zorder=3)
        dx += 0.56 + fontsize * 0.021 * len(label) + 0.55


# ---------------------------------------------------------------- Figure 1

def figure1_conceptual_framework():
    # Revision 3 (2026-09-08) - the adviser rejected the Input-Process-
    # Output framing outright. Rebuilt around General Systems Theory
    # (von Bertalanffy) instead: an Environment and a Knowledge Base
    # feed the system, the system is drawn as a black box (its internal
    # components are shown for clarity, but deliberately NOT chained
    # with arrows to each other - that would just be IPO again under a
    # different name), the system produces Outcomes, and a feedback
    # loop carries those outcomes back into the knowledge base. No box
    # anywhere is labeled Input, Process, or Output.
    fig, ax = plt.subplots(figsize=(11.8, 12))
    ax.set_xlim(-0.7, 11.5)
    ax.set_ylim(0, 19)
    ax.axis("off")

    band(ax, -0.7, 11.5, 14.7, 17.9, ROYAL_SOFT)
    band(ax, -0.7, 11.5, 7.7, 14.7, FOREST_SOFT)
    band(ax, -0.7, 11.5, 0.2, 7.7, GOLD_SOFT)

    ax.text(5.4, 18.55, "Figure 1. Conceptual Framework of TrainWise", ha="center",
            fontsize=18, color=INK, fontweight="bold")
    ax.text(5.4, 18.05, "General Systems Theory model - environment and knowledge base, a system boundary, outcomes, and feedback",
            ha="center", fontsize=10.5, color=MUTED, style="italic")

    # ---- Environment + Knowledge Base (what surrounds and feeds the system) ----
    pill(ax, 0.4, 16.95, 2.7, 0.62, "ENVIRONMENT", fill=ROYAL, fontsize=11)
    e1 = box(ax, 0.4, 14.85, 5.15, 1.8,
             "LSPU's 13 colleges and non-teaching\noffices  •  Dean / HR roles and policy\n"
             "•  Institutional training budget & real\npaid providers", fontsize=10.2)

    pill(ax, 6.35, 16.95, 3.1, 0.62, "KNOWLEDGE BASE", fill=FOREST, fontsize=11)
    e2 = box(ax, 6.05, 14.85, 5.05, 1.8,
             "Employee profile & assessment data\n•  Multi-year TNA records (2024, 2025,\n"
             "2027 - official + self-reported)  •\nTraining program catalog", fontsize=10.2, edge=FOREST)

    for b in (e1, e2):
        cx = b[0] + b[2] / 2
        elbow(ax, (cx, b[1]), (5.75, 14.0), first="v")

    # ---- The system, drawn as a labeled boundary (a "black box") ----
    ax.text(5.75, 13.5, "SYSTEM BOUNDARY", ha="center", fontsize=12, color=INK, fontweight="bold")
    sys_box = FancyBboxPatch((0.4, 8.0), 10.4, 5.0, boxstyle="round,pad=0.02,rounding_size=0.12",
                              linewidth=2.2, edgecolor=INK, facecolor="#FFFFFF", zorder=2)
    sh = FancyBboxPatch((0.47, 7.93), 10.4, 5.0, boxstyle="round,pad=0.02,rounding_size=0.12",
                         linewidth=0, facecolor=SHADOW, alpha=0.10, zorder=1)
    ax.add_patch(sh)
    ax.add_patch(sys_box)
    ax.text(5.6, 12.55, "THE TRAINWISE SYSTEM", ha="center", fontsize=13.5, color=INK, fontweight="bold")
    ax.text(5.6, 12.1, "(components shown for clarity - not a step-by-step sequence)",
            ha="center", fontsize=9.3, color=MUTED, style="italic")

    box(ax, 0.8, 9.85, 3.1, 1.75, "ML Recommendation\nEngine\n(XGBoost + SBERT\n+ TNA boost)", edge=FOREST, fontsize=9.6)
    box(ax, 4.1, 9.85, 3.1, 1.75, "Training Demand\nAggregation &\nSourcing", edge=GOLD, fontsize=9.6)
    box(ax, 7.4, 9.85, 3.1, 1.75, "Web & Mobile\nApplication", fontsize=9.6)
    ax.plot([0.8, 10.5], [9.55, 9.55], color=GRID, linewidth=1.0, zorder=1)
    ax.text(5.6, 8.7, "shared institutional database (profiles, assessments, demand, TNA records)",
            ha="center", fontsize=9.1, color=MUTED, style="italic")

    arrow(ax, (5.6, 8.0), (5.6, 3.75))

    # ---- Outcomes ----
    pill(ax, 4.55, 3.13, 1.8, 0.62, "OUTCOMES", fill=GOLD, fontsize=11)
    o1 = box(ax, 0.4, 1.2, 3.35, 1.55, "Institutional training\ndemand sourced &\nfulfilled", edge=GOLD, fontsize=9.8)
    o2 = box(ax, 4.075, 1.2, 3.35, 1.55, "Verified completions\non record\n(proof of attendance)", edge=GOLD, fontsize=9.8)
    o3 = box(ax, 7.75, 1.2, 3.35, 1.55, "A recommendation\nengine grounded in\nreal, current demand", edge=GOLD, fontsize=9.8)

    # ---- Feedback loop back into the Knowledge Base - routed entirely
    # outside the left edge of every box (x < 0.4) so it never crosses
    # through any box's own content, then in above the env/knowledge
    # boxes (in the gap between their top and the pills above them). ----
    fb_x = -0.35
    ax.plot([fb_x, fb_x], [1.95, 15.55], color=INK, linewidth=1.5, linestyle=(0, (5, 3)), zorder=1)
    # tail end at Outcomes - no arrowhead here, the loop originates from
    # this box; the only arrowhead is where it re-enters the Knowledge Base
    ax.plot([fb_x, 0.4], [1.95, 1.95], color=INK, linewidth=1.5, linestyle=(0, (5, 3)), zorder=1)
    ax.plot([fb_x, 8.6], [15.55, 15.55], color=INK, linewidth=1.5, linestyle=(0, (5, 3)), zorder=1)
    arrow(ax, (8.6, 15.55), (8.6, 14.85), color=INK, lw=1.5)
    ax.text(fb_x - 0.3, 8.7, "FEEDBACK", ha="center", va="center", fontsize=10, color=INK,
            fontweight="bold", rotation=90)

    legend_swatches(ax, 0.4, 0.4)

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig1_conceptual_framework.png")
    fig.savefig(out, dpi=230, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------- Figure 2

def figure2_system_architecture():
    fig, ax = plt.subplots(figsize=(11.5, 14))
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, 23)
    ax.axis("off")

    layer_bounds = [
        (20.6, 22.1, ROYAL_SOFT), (17.9, 20.2, ROYAL_SOFT),
        (13.7, 17.5, FOREST_SOFT), (10.0, 13.3, FOREST_SOFT),
        (7.0, 9.6, ROYAL_SOFT), (3.2, 6.6, GOLD_SOFT),
    ]
    for y0, y1, c in layer_bounds:
        band(ax, 0, 11.5, y0, y1, c)

    ax.text(5.75, 22.55, "Figure 2. System Architecture Diagram", ha="center",
            fontsize=18, color=INK, fontweight="bold")

    ax.text(0.35, 21.95, "USERS LAYER", fontsize=11, color=ROYAL, fontweight="bold")
    ux = [0.3, 4.1, 7.9]
    for i, label in enumerate(["Employee", "Dean / Evaluator", "HR Admin"]):
        box(ax, ux[i], 20.6, 3.1, 1.05, label, fontsize=10.5)
    for x in ux:
        arrow(ax, (x + 1.55, 20.6), (x + 1.55, 19.75))

    ax.text(0.35, 19.4, "FRONTEND LAYER  --  PHP views, Tailwind CSS", fontsize=11, color=ROYAL, fontweight="bold")
    box(ax, 0.3, 17.95, 10.9, 1.1,
        "Dashboard  |  Assessment Form  |  Training Recommendations  |  Training Demand Board  |  Admin Panel", fontsize=9.6)
    # Merge point kept well above the section label's baseline (including
    # descenders, e.g. the "y" in "mysqli") so the connectors never cross
    # through the header text on their way down to the box row.
    elbow(ax, (2.4, 17.95), (5.75, 17.7), first="v")
    elbow(ax, (9.1, 17.95), (5.75, 17.7), first="v")
    arrow(ax, (5.75, 17.7), (5.75, 16.9))

    ax.text(0.35, 17.25, "BACKEND SERVICES LAYER  --  PHP / mysqli", fontsize=11, color=FOREST, fontweight="bold")
    bw, bh = 2.55, 1.3
    bx = [0.3, 3.05, 5.8, 8.55]
    labels_row1 = ["Authentication", "Assessment\nProcessing", "Recommendation\nIntegration", "Notification &\nUser Management"]
    for i, lab in enumerate(labels_row1):
        box(ax, bx[i], 15.6, bw, bh, lab, fontsize=9.3)
    box(ax, 2.9, 14.05, 6.0, 1.25, "Training Demand Aggregation\n& Sourcing Module", edge=GOLD, fill=WHITE, fontsize=10.3)
    new_tag(ax, 9.15, 15.1)
    elbow(ax, (4.3, 15.6), (5.9, 15.3), first="v")
    arrow(ax, (5.9, 14.05), (5.9, 13.0))

    ax.text(0.35, 12.7, "ML ENGINE LAYER  --  FastAPI microservice (separate process)", fontsize=11, color=FOREST, fontweight="bold")
    mx = [0.3, 4.0, 7.7]
    ml_labels = ["XGBoost Relevance\nRegressors (14 categories)", "SBERT Text\nSimilarity Matcher", "TNA Boost Matcher\n(official + self-reported)"]
    for i, lab in enumerate(ml_labels):
        edge = GOLD if i == 2 else FOREST
        box(ax, mx[i], 10.9, 3.4, 1.4, lab, edge=edge, fill=WHITE, fontsize=9.5)
    new_tag(ax, 10.65, 12.0)
    arrow(ax, (5.9, 10.9), (5.9, 9.85))

    ax.text(0.35, 9.6, "DATABASE LAYER  --  shared MySQL instance", fontsize=11, color=ROYAL, fontweight="bold")
    box(ax, 0.3, 8.0, 10.9, 1.3,
        "users  |  assessments  |  training_recommendations  |  training_demand  |\n"
        "tna_2025_demand (2024 / 2025 / 2027)  |  training_history_log", fontsize=9.5)
    arrow(ax, (5.75, 8.0), (5.75, 6.9))

    ax.text(0.35, 6.55, "DEPLOYMENT LAYER", fontsize=11, color=GOLD, fontweight="bold")
    box(ax, 0.6, 4.8, 4.9, 1.3, "XAMPP\n(Apache + PHP), port 80", fontsize=9.8)
    box(ax, 6.0, 4.8, 4.9, 1.3, "Uvicorn (FastAPI, Python)\nport 8000", fontsize=9.8)
    arrow(ax, (5.5, 5.475), (6.0, 5.475))
    arrow(ax, (6.0, 5.15), (5.5, 5.15), style="-|>")

    legend_swatches(ax, 0.4, 1.6)

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig2_system_architecture.png")
    fig.savefig(out, dpi=230, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------- Figure 3

def figure3_system_flowchart():
    fig, ax = plt.subplots(figsize=(14.5, 15.5))
    ax.set_xlim(0, 14.5)
    ax.set_ylim(0, 22.6)
    ax.axis("off")

    lane_w = 4.15
    gap = 0.5
    lanes_x = [0.3, 0.3 + lane_w + gap, 0.3 + 2 * (lane_w + gap)]
    lane_fill = ["#F7F9FC", "#F5FAF7", "#FDF9F1"]
    lane_labels = ["EMPLOYEE", "DEAN / EVALUATOR", "HR ADMIN"]
    lane_top, lane_bottom = 20.6, 0.5
    for x, fill in zip(lanes_x, lane_fill):
        band(ax, x, x + lane_w, lane_bottom, lane_top, fill)

    ax.text(7.25, 22.15, "Figure 3. System Flowchart", ha="center", fontsize=17, color=INK, fontweight="bold")
    for x, lab in zip(lanes_x, lane_labels):
        pill(ax, x + lane_w / 2 - 1.5, lane_top + 0.15, 3.0, 0.55, lab, fill=INK, fontsize=10.5)

    def cx(col):
        return lanes_x[col] + lane_w / 2

    def lb(col, y, h, text, **kw):
        return box(ax, lanes_x[col] + 0.25, y, lane_w - 0.5, h, text, fontsize=9.5, **kw)

    def term(col, y, h, text, fill=INK, textcolor=WHITE):
        pill(ax, lanes_x[col] + 0.65, y, lane_w - 1.3, h, text, fill=fill, textcolor=textcolor, fontsize=10)

    # ---- Employee lane ----
    term(0, 19.3, 0.6, "START")
    arrow(ax, (cx(0), 19.3), (cx(0), 18.75))
    lb(0, 17.6, 1.1, "Login / Register")
    arrow(ax, (cx(0), 17.6), (cx(0), 17.05))
    lb(0, 15.95, 1.1, "Complete Profile\n& Assessment")
    arrow(ax, (cx(0), 15.95), (cx(0), 15.4))
    lb(0, 14.3, 1.1, "View AI-Generated\nRecommendations")
    arrow(ax, (cx(0), 14.3), (cx(0), 13.75))
    e_accept = lb(0, 12.65, 1.1, "Accept Recommendation\n(pools into shared demand)", edge=GOLD, fill=WHITE)
    new_tag(ax, lanes_x[0] + lane_w - 0.55, 13.55)
    lb(0, 11.15, 1.1, "Express Interest in a\nDean-Posted Opportunity", edge=GOLD, fill=WHITE)

    arrow(ax, (cx(0), 9.55), (cx(0), 9.0))
    lb(0, 7.85, 1.1, "Notified: Training\nAvailable / Confirmed")
    arrow(ax, (cx(0), 7.85), (cx(0), 7.3))
    lb(0, 6.2, 1.1, "Upload Proof of\nCompletion (4 items)", edge=GOLD, fill=WHITE)
    arrow(ax, (cx(0), 6.2), (cx(0), 5.65))
    lb(0, 4.55, 1.1, "Mark Training Complete\n(unlocked only once proof is on file)")
    arrow(ax, (cx(0), 4.55), (cx(0), 4.0))
    term(0, 3.4, 0.6, "END", fill=MUTED)

    # ---- Dean lane ----
    lb(1, 12.65, 1.1, "Receive Demand\nForwarded by HR", edge=GOLD, fill=WHITE)
    arrow(ax, (cx(1), 12.65), (cx(1), 12.1))
    lb(1, 11.0, 1.1, "Source a Real Paid\nTraining Provider")
    arrow(ax, (cx(1), 11.0), (cx(1), 10.3))
    diamond(ax, cx(1), 9.55, 3.1, 1.4, "Sourced a program\nready to report?")
    arrow(ax, (cx(1) - 1.0, 9.05), (lanes_x[1] + 0.65, 8.55))
    arrow(ax, (cx(1) + 1.0, 9.05), (lanes_x[1] + lane_w - 0.65, 8.55))
    line_label(ax, lanes_x[1] + 0.85, 8.9, "yes")
    line_label(ax, lanes_x[1] + lane_w - 1.05, 8.9, "no")
    # Two side-by-side boxes with a clean, deliberate gap between them
    # (each inset 0.25 from its own lane edge, 0.25 gap in between) -
    # widths recomputed from that budget so they never touch or overlap.
    d_bw = (lane_w - 0.5 - 0.25) / 2
    d_box1_x = lanes_x[1] + 0.25
    d_box2_x = d_box1_x + d_bw + 0.25
    box(ax, d_box1_x, 7.55, d_bw, 1.0, "Report\nTraining Found", edge=GOLD, fill=WHITE, fontsize=7.8)
    box(ax, d_box2_x, 7.55, d_bw, 1.0, "Post Training\nOpportunity Directly", edge=GOLD, fill=WHITE, fontsize=7.3)
    new_tag(ax, cx(1), 6.95)
    ax.text(d_box2_x + d_bw / 2, 7.35, "seen instantly by\nemployees", fontsize=6.3, color=MUTED,
            style="italic", ha="center", va="top", linespacing=1.2)

    # ---- HR lane ----
    lb(2, 15.95, 1.1, "Review Pooled\nTraining Demand", edge=GOLD, fill=WHITE)
    arrow(ax, (cx(2), 15.95), (cx(2), 15.4))
    diamond(ax, cx(2), 14.65, 3.3, 1.4, "A dean's college can\nsource this program?")
    arrow(ax, (cx(2) - 1.05, 14.15), (lanes_x[2] + 0.65, 13.6))
    arrow(ax, (cx(2) + 1.05, 14.15), (lanes_x[2] + lane_w - 0.65, 13.6))
    line_label(ax, lanes_x[2] + 0.9, 13.95, "yes")
    line_label(ax, lanes_x[2] + lane_w - 1.1, 13.95, "no")
    h_bw = (lane_w - 0.5 - 0.25) / 2
    h_box1_x = lanes_x[2] + 0.25
    h_box2_x = h_box1_x + h_bw + 0.25
    h_box1_cx = h_box1_x + h_bw / 2
    h_box2_cx = h_box2_x + h_bw / 2
    box(ax, h_box1_x, 12.6, h_bw, 1.0, "Forward to\nCollege Dean", edge=GOLD, fill=WHITE, fontsize=7.8)
    box(ax, h_box2_x, 12.6, h_bw, 1.0, "Source Training\nDirectly (HR)", edge=GOLD, fill=WHITE, fontsize=7.8)
    new_tag(ax, cx(2), 12.0)
    # Each branch lands on its own x on the box below (not both funneled
    # into the same point) - a straight vertical since the target sits
    # directly beneath, so no elbow bend is needed either.
    arrow(ax, (h_box1_cx, 12.6), (h_box1_cx, 11.5), color=GOLD)
    arrow(ax, (h_box2_cx, 12.6), (h_box2_cx, 11.5), color=GOLD)
    lb(2, 10.4, 1.1, "Receive Training Found\n/ HR Approve")
    arrow(ax, (cx(2), 10.4), (cx(2), 9.85))
    lb(2, 8.75, 1.1, "Review AI-Assisted\nShortlist", edge=GOLD, fill=WHITE)
    arrow(ax, (cx(2), 8.75), (cx(2), 8.2))
    lb(2, 7.1, 1.1, "Confirm Participants\n(within stated capacity)")

    # ---- cross-lane hand-offs ----
    # Each connector below is routed either as a direct same-y arrow between
    # adjacent lanes, or as a 3-segment route() through the empty vertical
    # "highway" that sits in a lane gap, chosen so the path never crosses a
    # box in a lane it only passes over.
    gapA_x = lanes_x[0] + lane_w + gap / 2   # gap between Employee | Dean
    gapB_x = lanes_x[1] + lane_w + gap / 2   # gap between Dean | HR

    # 1. Employee "Accept Recommendation" -> HR "Review Pooled Demand"
    #    (Dean lane is empty above y=13.75, so the crossing happens up there)
    route(ax, (lanes_x[0] + lane_w, 13.2), (lanes_x[2], 16.5), via_x=gapA_x)

    # 2. HR "Forward to College Dean" -> Dean "Receive Demand Forwarded"
    arrow(ax, (lanes_x[2], 13.15), (lanes_x[1] + lane_w, 13.15), color=GOLD)

    # 3. Dean "Report Training Found" -> HR "Receive Training Found / HR Approve"
    #    (from that box's own right edge, not the far lane edge - it used
    #    to start past "Post Training Opportunity Directly" and visibly
    #    cut across it)
    route(ax, (d_box1_x + d_bw, 8.05), (lanes_x[2], 10.95), via_x=gapB_x)

    # 4. HR "Confirm Participants" -> Employee "Notified: Training Available"
    #    Routed below the Dean lane's boxes entirely (y=7.0, clear of both
    #    "Report Training Found"/"Post Training Opportunity Directly" AND
    #    the decision diamond's branch lines above them) rather than
    #    through the y=8.7 gap, which used to cut across those lines.
    fb_y = 6.5
    ax.plot([lanes_x[2], lanes_x[2]], [7.65, fb_y], color=GOLD, linewidth=1.6, zorder=1,
            solid_capstyle="round", solid_joinstyle="round")
    ax.plot([lanes_x[2], lanes_x[0] + lane_w], [fb_y, fb_y], color=GOLD, linewidth=1.6, zorder=1,
            solid_capstyle="round", solid_joinstyle="round")
    arrow(ax, (lanes_x[0] + lane_w, fb_y), (lanes_x[0] + lane_w, 7.85), color=GOLD)

    legend_swatches(ax, 0.3, 0.65)

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig3_system_flowchart.png")
    fig.savefig(out, dpi=230, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------- Figure 4

def usecase(ax, cx_, cy_, text, w=3.5, h=0.92, new=False, fontsize=9.2):
    edge = GOLD if new else ROYAL
    sh_e = Ellipse((cx_ + 0.05, cy_ - 0.05), w, h, facecolor=SHADOW, edgecolor="none", alpha=0.10, zorder=1)
    ax.add_patch(sh_e)
    e = Ellipse((cx_, cy_), w, h, linewidth=1.7, edgecolor=edge, facecolor=WHITE, zorder=2)
    ax.add_patch(e)
    ax.text(cx_, cy_, text, ha="center", va="center", fontsize=fontsize, color=INK, zorder=3, linespacing=1.2)
    if new:
        new_tag(ax, cx_ + w / 2 - 0.05, cy_ + h / 2 - 0.02)
    return (cx_, cy_, w)


def uc_fan(ax, actor_xy, targets, color, from_right=False):
    ax_, ay_ = actor_xy
    for cx_, cy_, w in targets:
        edge_x = cx_ + w / 2 if from_right else cx_ - w / 2
        stub = ax_ - 0.4 if from_right else ax_ + 0.4
        ax.plot([stub, edge_x], [ay_, cy_], color=color, linewidth=1.1, alpha=0.5, zorder=1)


def stacked_ys(y_top, count, step, extra_gaps=None):
    extra_gaps = extra_gaps or {}
    ys = [y_top]
    for i in range(1, count):
        ys.append(ys[-1] - step - extra_gaps.get(i, 0))
    return ys


def uc_boundary(ax, bx0, by0, bw, bh):
    sh = FancyBboxPatch((bx0 + 0.07, by0 - 0.07), bw, bh, boxstyle="round,pad=0.02,rounding_size=0.14",
                         linewidth=0, facecolor=SHADOW, alpha=0.10, zorder=0)
    ax.add_patch(sh)
    boundary = FancyBboxPatch((bx0, by0), bw, bh, boxstyle="round,pad=0.02,rounding_size=0.14",
                               linewidth=1.8, edgecolor=INK, facecolor="#FCFCFB", zorder=1)
    ax.add_patch(boundary)
    ax.text(bx0 + bw / 2, by0 + bh - 0.45, "TrainWise", ha="center", fontsize=13, color=INK,
            fontweight="bold", style="italic")


def uc_legend(ax, y=-0.02):
    legend_elems = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=WHITE, markeredgecolor=GOLD,
               markersize=12, markeredgewidth=1.9, label="New use case in this revision"),
    ]
    ax.legend(handles=legend_elems, loc="lower center", bbox_to_anchor=(0.5, y), fontsize=10.5, frameon=False)


# Revision 4 (2026-09-08) - the single 15-inch-tall, 27-use-case version
# was accurate but unusable as a Word figure (it would either force a
# page break mid-diagram or get scaled down until the text was
# unreadable). Split into two right-sized figures instead of shrinking
# text to fit: 4a covers the employee side end to end (the actor with by
# far the most use cases, plus the Recommendation Engine, since its one
# use case is what the employee's own recommendations come from); 4b
# puts Dean and HR Admin on opposite sides of one shared boundary, since
# their own use cases were already the two groups most likely to be read
# and compared together (they're the two halves of the demand pipeline's
# review chain). Same non-crossing layout principle as before - each
# actor's own use cases stay in one contiguous, non-overlapping band -
# just applied twice at a page-appropriate size instead of once at a
# poster size.

def figure4a_use_case_diagram_employee():
    fig, ax = plt.subplots(figsize=(11, 12.2))
    ax.set_xlim(0, 13.6)
    ax.set_ylim(0, 15.4)
    ax.axis("off")

    ax.text(6.8, 14.9, "Figure 4a. Use Case Diagram - Employee", ha="center",
            fontsize=17, color=INK, fontweight="bold")

    uc_boundary(ax, 2.5, 1.1, 8.3, 12.5)

    step = 1.15
    col_x = 6.1
    eu_y = stacked_ys(12.6, 9, step)
    eu_actor_y = (eu_y[0] + eu_y[-1]) / 2
    stick_actor(ax, 1.1, eu_actor_y, "End User\n(Employee)")
    eu = [
        usecase(ax, col_x, eu_y[0], "Register / Login"),
        usecase(ax, col_x, eu_y[1], "Manage Profile"),
        usecase(ax, col_x, eu_y[2], "Take Assessment"),
        usecase(ax, col_x, eu_y[3], "Create & View\nIndividual Development Plan"),
        usecase(ax, col_x, eu_y[4], "View AI\nRecommendations"),
        usecase(ax, col_x, eu_y[5], "Accept\nRecommendation", new=True),
        usecase(ax, col_x, eu_y[6], "Express Interest in\nPosted Opportunity", new=True),
        usecase(ax, col_x, eu_y[7], "Upload Proof of\nCompletion", new=True),
        usecase(ax, col_x, eu_y[8], "Mark Training\nComplete"),
    ]
    uc_fan(ax, (1.1, eu_actor_y), eu, ROYAL)

    gen_y = eu_y[2]
    gen = usecase(ax, 9.9, gen_y, "Generate Ranked\nRecommendations", w=2.85, fontsize=8.8)
    stick_actor(ax, 12.9, gen_y, "Recommendation\nEngine")
    ax.plot([12.5, 9.9 + gen[2] / 2], [gen_y, gen_y], color=INK, linewidth=1.1, alpha=0.5, zorder=1)

    uc_legend(ax)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig4a_use_case_diagram_employee.png")
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


def figure4b_use_case_diagram_dean_hr():
    fig, ax = plt.subplots(figsize=(13.2, 14.2))
    ax.set_xlim(0, 15.4)
    ax.set_ylim(0, 16.3)
    ax.axis("off")

    ax.text(7.7, 15.8, "Figure 4b. Use Case Diagram - Dean and HR Admin", ha="center",
            fontsize=17, color=INK, fontweight="bold")

    uc_boundary(ax, 1.9, 0.6, 11.6, 14.3)

    step = 1.15
    sub_gap = 0.3
    y_top = 14.0

    # Dean's column sits on the LEFT side of the shared boundary, with
    # its actor further left still - this actor never needs a line that
    # reaches HR's side, so the two never cross regardless of how many
    # use cases either one has.
    dean_col_x = 5.1
    dean_y = stacked_ys(y_top, 6, step, {3: sub_gap})
    dean_actor_y = (dean_y[0] + dean_y[-1]) / 2
    stick_actor(ax, 0.85, dean_actor_y, "Dean /\nEvaluator")
    dean = [
        usecase(ax, dean_col_x, dean_y[0], "Review College\nAssessment Submissions", fontsize=8.7),
        usecase(ax, dean_col_x, dean_y[1], "Review College\nIDP Submissions", fontsize=8.7),
        usecase(ax, dean_col_x, dean_y[2], "Evaluate Faculty\nPerformance", fontsize=8.7),
        usecase(ax, dean_col_x, dean_y[3], "Review Training Demand\nForwarded by HR", new=True, fontsize=8.4),
        usecase(ax, dean_col_x, dean_y[4], "Report Training\nFound", new=True, fontsize=8.7),
        usecase(ax, dean_col_x, dean_y[5], "Post Training\nOpportunity Directly", new=True, fontsize=8.2),
    ]
    uc_fan(ax, (0.85, dean_actor_y), dean, FOREST)

    # HR's column mirrors this on the RIGHT side, actor further right,
    # fan lines pointing left into its own column only.
    hr_col_x = 10.2
    hr_y = stacked_ys(y_top, 11, step, {3: sub_gap, 6: sub_gap, 8: sub_gap})
    hr_actor_y = (hr_y[0] + hr_y[-1]) / 2
    stick_actor(ax, 14.55, hr_actor_y, "HR Admin")
    hr = [
        usecase(ax, hr_col_x, hr_y[0], "Approve / Decline\nRegistrations", fontsize=8.7),
        usecase(ax, hr_col_x, hr_y[1], "Manage User\nAccounts", fontsize=8.7),
        usecase(ax, hr_col_x, hr_y[2], "Set Assessment\nDeadline", fontsize=8.7),
        usecase(ax, hr_col_x, hr_y[3], "Review Assessment Forms\n(All Colleges)", fontsize=8.2),
        usecase(ax, hr_col_x, hr_y[4], "Review IDP Forms\n(All Colleges)", fontsize=8.4),
        usecase(ax, hr_col_x, hr_y[5], "Review Evaluation Forms\n(All Colleges)", fontsize=8.0),
        usecase(ax, hr_col_x, hr_y[6], "View Reports\n& Analytics", fontsize=8.7),
        usecase(ax, hr_col_x, hr_y[7], "View Audit Log", fontsize=8.7),
        usecase(ax, hr_col_x, hr_y[8], "Review Training\nDemand", new=True, fontsize=8.7),
        usecase(ax, hr_col_x, hr_y[9], "Forward to Dean /\nSource Directly", new=True, fontsize=8.4),
        usecase(ax, hr_col_x, hr_y[10], "Review AI-Assisted\nShortlist", new=True, fontsize=8.4),
    ]
    uc_fan(ax, (14.55, hr_actor_y), hr, GOLD, from_right=True)

    uc_legend(ax, y=-0.015)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig4b_use_case_diagram_dean_hr.png")
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    figure1_conceptual_framework()
    figure2_system_architecture()
    figure3_system_flowchart()
    figure4a_use_case_diagram_employee()
    figure4b_use_case_diagram_dean_hr()


if __name__ == "__main__":
    main()
