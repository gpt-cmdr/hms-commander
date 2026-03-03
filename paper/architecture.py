"""Generate architecture diagram for JOSS paper using matplotlib."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(1, 1, figsize=(10, 7))
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.5)
ax.axis('off')

# Color palette
blue = '#4472C4'
green = '#548235'
orange = '#C55A11'
gray = '#808080'
light_blue = '#D6E4F0'
light_green = '#E2EFDA'
light_orange = '#FCE4D6'
light_gray = '#F2F2F2'

def add_box(ax, x, y, w, h, text, facecolor, edgecolor, fontsize=9, bold=False):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                         facecolor=facecolor, edgecolor=edgecolor, linewidth=1.5)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=weight, wrap=True)

def add_arrow(ax, x1, y1, x2, y2, color='#444444'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))

# Title
ax.text(5, 7.2, 'HMS-Commander Architecture', ha='center', va='center',
        fontsize=14, fontweight='bold')

# --- Layer 1: User Interface (top) ---
add_box(ax, 0.3, 6.2, 2.8, 0.7, 'Python Script /\nJupyter Notebook', light_gray, gray, 10, True)
add_box(ax, 3.6, 6.2, 2.8, 0.7, 'init_hms_project()\nhms.basin_df, hms.run_df', light_blue, blue, 8)
add_box(ax, 6.9, 6.2, 2.8, 0.7, 'HmsPrj\n(Project State Manager)', light_blue, blue, 9, True)

# --- Layer 2: File Operations ---
ax.text(0.15, 5.6, 'File Operations', fontsize=10, fontweight='bold', color=blue)
boxes_l2 = ['HmsBasin\n.basin', 'HmsMet\n.met', 'HmsControl\n.control',
            'HmsGage\n.gage', 'HmsRun\n.run']
for i, label in enumerate(boxes_l2):
    add_box(ax, 0.3 + i*1.9, 4.8, 1.7, 0.7, label, light_blue, blue, 8)

# --- Layer 3: Execution & Results ---
ax.text(0.15, 4.2, 'Execution & Results', fontsize=10, fontweight='bold', color=green)
add_box(ax, 0.3, 3.4, 2.2, 0.7, 'HmsCmdr\nSimulation Execution', light_green, green, 9, True)
add_box(ax, 2.8, 3.4, 2.2, 0.7, 'HmsJython\nScript Generation', light_green, green, 9)
add_box(ax, 5.3, 3.4, 2.2, 0.7, 'HmsDss\nDSS Read/Write', light_green, green, 9)
add_box(ax, 7.8, 3.4, 1.9, 0.7, 'HmsResults\nPeak Flows', light_green, green, 9)

# --- Layer 4: Storm Generation & GIS ---
ax.text(0.15, 2.8, 'Storm Generation & GIS', fontsize=10, fontweight='bold', color=orange)
add_box(ax, 0.3, 2.0, 2.0, 0.7, 'Atlas14Storm\nNOAA Atlas 14', light_orange, orange, 8)
add_box(ax, 2.55, 2.0, 2.0, 0.7, 'FrequencyStorm\nTP-40/Hydro-35', light_orange, orange, 8)
add_box(ax, 4.8, 2.0, 2.0, 0.7, 'ScsTypeStorm\nSCS I/IA/II/III', light_orange, orange, 8)
add_box(ax, 7.05, 2.0, 2.7, 0.7, 'HmsGeo / HmsHuc\nGIS Export & HUC', light_orange, orange, 8)

# --- Layer 5: External Systems (bottom) ---
ax.text(0.15, 1.4, 'External Systems', fontsize=10, fontweight='bold', color=gray)
add_box(ax, 0.3, 0.5, 2.5, 0.7, 'HEC-HMS\n(via Jython scripts)', light_gray, gray, 9, True)
add_box(ax, 3.1, 0.5, 2.5, 0.7, 'HEC-DSS Files\n(via HEC Monolith)', light_gray, gray, 9)
add_box(ax, 5.9, 0.5, 3.8, 0.7, 'ras-commander / HEC-RAS\n(HMS\u2192RAS boundary conditions)', light_gray, gray, 9)

# --- Arrows ---
# User to HmsPrj
add_arrow(ax, 3.1, 6.55, 3.6, 6.55, blue)
add_arrow(ax, 6.4, 6.55, 6.9, 6.55, blue)

# HmsPrj to File Operations
for i in range(5):
    x = 0.3 + i*1.9 + 0.85
    add_arrow(ax, x, 6.2, x, 5.5, blue)

# File ops to Execution
add_arrow(ax, 2.0, 4.8, 1.4, 4.1, green)
add_arrow(ax, 5.0, 4.8, 4.5, 4.1, green)

# Execution to external
add_arrow(ax, 1.4, 3.4, 1.4, 1.2, gray)
add_arrow(ax, 6.4, 3.4, 5.0, 1.2, gray)
add_arrow(ax, 8.7, 3.4, 8.0, 1.2, gray)

plt.tight_layout()
plt.savefig('/home/user/hms-commander/paper/architecture.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print("Architecture diagram saved to paper/architecture.png")
