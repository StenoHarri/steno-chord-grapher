import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from collections import defaultdict
import math

# Input files
CHORD_FREQS_FILE = "chord_frequencies.json"
EDGE_FREQS_FILE = "edge_frequencies.json"
CHORD_CONFLICTS_FILE = "chord_conflicts.json"
EDGE_CONFLICTS_FILE = "edge_conflicts.json"

# Load data
with open(CHORD_FREQS_FILE, "r", encoding="utf-8") as f:
    chord_freqs = json.load(f)

with open(EDGE_FREQS_FILE, "r", encoding="utf-8") as f:
    edge_freqs = json.load(f)

with open(CHORD_CONFLICTS_FILE, "r", encoding="utf-8") as f:
    chord_conflicts = json.load(f)

with open(EDGE_CONFLICTS_FILE, "r", encoding="utf-8") as f:
    edge_conflicts = json.load(f)


def get_layer_from_mask(mask):
    """Get the layer number from a mask string (0-indexed position of first '1')"""
    return mask.rindex('1')


def build_chord_info(chord_list):
    """Build a dict of chord -> {subset, mask, probability, conflict} info"""
    chord_info = {}
    for entry in chord_list:
        chord = entry['chord']
        mask = entry['mask']
        subset = get_layer_from_mask(mask)
        chord_info[chord] = {
            'subset': subset,
            'mask': mask,
            'probability': entry['probability'],
            'zipf': entry['zipf'],
            'conflict': 0.0,
            'collisions': []
        }
    return chord_info


def add_conflicts_to_chord_info(chord_info, conflict_list):
    """Add conflict probabilities and collision details to chord info"""
    conflict_lookup = {}
    for entry in conflict_list:
        chord = entry['chord']
        conflict_lookup[chord] = {
            'conflict_prob': entry.get('probability', 0.0),
            'collisions': entry.get('top_collisions', [])
        }
    
    for chord, info in chord_info.items():
        if chord in conflict_lookup:
            info['conflict'] = conflict_lookup[chord]['conflict_prob']
            info['collisions'] = conflict_lookup[chord]['collisions']
        else:
            info['conflict'] = 0.0
            info['collisions'] = []
    
    return chord_info


def build_edge_info(edge_list):
    """Build a dict of (from_chord, to_chord) -> {probability, conflict} info"""
    edge_info = {}
    for entry in edge_list:
        key = (entry['from'], entry['to'])
        edge_info[key] = {
            'probability': entry['probability'],
            'zipf': entry['zipf'],
            'from_mask': entry['from_mask'],
            'to_mask': entry['to_mask'],
            'conflict': 0.0,
            'collisions': []
        }
    return edge_info


def add_conflicts_to_edge_info(edge_info, conflict_list):
    """Add conflict probabilities and collision details to edge info"""
    conflict_lookup = {}
    for entry in conflict_list:
        key = (entry['from'], entry['to'])
        conflict_lookup[key] = {
            'conflict_prob': entry.get('probability', 0.0),
            'collisions': entry.get('top_collisions', [])
        }
    
    for key, info in edge_info.items():
        if key in conflict_lookup:
            info['conflict'] = conflict_lookup[key]['conflict_prob']
            info['collisions'] = conflict_lookup[key]['collisions']
        else:
            info['conflict'] = 0.0
            info['collisions'] = []
    
    return edge_info


def format_collision_display(collisions, max_display=3):
    """Format collision list - show total count but only display top 'max_display' examples"""
    if not collisions:
        return ["    (no collisions)"]
    
    displays = []
    total = len(collisions)
    
    # Show top examples
    for i, coll in enumerate(collisions[:max_display]):
        word1 = coll['colliding_word'][:15] + '..' if len(coll['colliding_word']) > 15 else coll['colliding_word']
        word2 = coll['colliding_with_word'][:15] + '..' if len(coll['colliding_with_word']) > 15 else coll['colliding_with_word']
        displays.append(f"    {i+1}. '{word1}' ↔ '{word2}'")
    
    return displays


def plot_bank_layout(chord_info, edge_info, bank_name, min_edge_prob=0.001):
    """
    Plot a multipartite layout for one bank (left or right).
    """
    # Create graph
    G = nx.DiGraph()
    
    # Group chords by subset (layer)
    subsets = defaultdict(list)
    for chord, info in chord_info.items():
        subset = info['subset']
        subsets[subset].append(chord)
        node_attrs = {k: v for k, v in info.items() if k != 'subset'}
        G.add_node(chord, subset=subset, **node_attrs)
    
    # Sort subsets
    sorted_subsets = sorted(subsets.keys())
    
    # Add edges with significant probability
    for (from_chord, to_chord), info in edge_info.items():
        if info['probability'] >= min_edge_prob:
            if from_chord in chord_info and to_chord in chord_info:
                G.add_edge(from_chord, to_chord, **info)
    
    # Use networkx's built-in multipartite layout
    pos = nx.multipartite_layout(G, subset_key='subset', align='vertical')
    
    # Create figure with 2 columns: network (60%), stats (40%)
    # Stats will be split into chords (left side of stats) and edges (right side of stats)
    fig = plt.figure(figsize=(28, 16))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.5, 0.5, 0.5])
    
    ax1 = fig.add_subplot(gs[0])  # Network graph
    ax2 = fig.add_subplot(gs[1])  # Chord Statistics
    ax3 = fig.add_subplot(gs[2])  # Edge Statistics
    
    # Plot 1: Chord nodes with coverage and conflict
    ax1.set_title(f"{bank_name.capitalize()} Hand Chord Layout\n(Node size = Coverage, Color intensity = Conflict ratio)", 
                  fontsize=14, fontweight='bold')
    
    # Calculate node sizes based on probability
    max_prob = max(info['probability'] for info in chord_info.values())
    min_size = 300
    max_size = 3000
    
    # Calculate node colors based on conflict ratio
    max_conflict_ratio = 0
    for info in chord_info.values():
        if info['probability'] > 0:
            ratio = info['conflict'] / info['probability']
            max_conflict_ratio = max(max_conflict_ratio, ratio)
    
    # Draw nodes
    for chord, info in chord_info.items():
        if chord in pos:
            size = min_size + (info['probability'] / max_prob) * (max_size - min_size) if max_prob > 0 else min_size
            
            if info['probability'] > 0 and max_conflict_ratio > 0:
                conflict_ratio = info['conflict'] / info['probability']
                color_intensity = conflict_ratio / max_conflict_ratio
            else:
                color_intensity = 0
            
            adjusted_intensity = color_intensity ** 0.5
            red = adjusted_intensity
            green = max(0, min(1, 1 - adjusted_intensity * 1.2))
            blue = 0
            color = (red, green, blue)
            
            ax1.scatter(pos[chord][0], pos[chord][1], s=size, c=[color], 
                       edgecolors='black', linewidth=1.5, zorder=3, alpha=0.8)
            
            ax1.annotate(chord, pos[chord], textcoords="offset points", 
                        xytext=(0, 0), ha='center', fontsize=9, fontweight='bold')
    
    # Draw edges
    max_edge_prob = max(info['probability'] for info in edge_info.values()) if edge_info else 1
    min_edge_width = 2.0
    max_edge_width = 10
    
    for (from_chord, to_chord), info in edge_info.items():
        if info['probability'] >= min_edge_prob and from_chord in pos and to_chord in pos:
            width = min_edge_width + (info['probability'] / max_edge_prob) * (max_edge_width - min_edge_width)
            alpha = 1.0

            if info['probability'] > 0:
                conflict_ratio = info['conflict'] / info['probability']
                edge_max_conflict = max((e['conflict'] / e['probability'] if e['probability'] > 0 else 0) 
                                       for e in edge_info.values()) if edge_info else 1
                if edge_max_conflict > 0:
                    edge_color_intensity = conflict_ratio / edge_max_conflict
                else:
                    edge_color_intensity = 0
            else:
                edge_color_intensity = 0
            
            adjusted_edge_intensity = edge_color_intensity ** 0.5
            edge_red = adjusted_edge_intensity
            edge_green = max(0, min(1, 1 - adjusted_edge_intensity * 1.2))
            edge_blue = 0
            edge_color = (edge_red, edge_green, edge_blue)
            
            rad = 0.1 if abs(pos[from_chord][1] - pos[to_chord][1]) < 0.1 else 0
            
            ax1.annotate("",
                        xy=pos[to_chord], xycoords='data',
                        xytext=pos[from_chord], textcoords='data',
                        arrowprops=dict(arrowstyle="->",
                                       color=edge_color,
                                       lw=width,
                                       alpha=alpha,
                                       connectionstyle=f"arc3,rad={rad}"),
                        zorder=1)
    
    # Add subset labels
    for subset in sorted_subsets:
        nodes_in_subset = subsets[subset]
        x_positions = [pos[n][0] for n in nodes_in_subset if n in pos]
        if x_positions:
            avg_x = sum(x_positions) / len(x_positions)
            ax1.text(avg_x, max(pos[n][1] for n in nodes_in_subset if n in pos) + 0.5, 
                    f"Layer {subset}", ha='center', fontsize=10, fontweight='bold')
    
    ax1.axis('equal')
    ax1.axis('off')
    
    # Set background colors
    fig.patch.set_facecolor("#5D6872")
    ax1.set_facecolor('#D6EAF8')
    ax2.set_facecolor('#E8F0F8')
    ax3.set_facecolor('#E8F0F8')
    
    # Sort data
    sorted_chords = sorted(chord_info.items(), key=lambda x: x[1]['probability'], reverse=True)
    chords_by_conflict = sorted(chord_info.items(), key=lambda x: x[1]['conflict'], reverse=True)
    sorted_edges = sorted(edge_info.items(), key=lambda x: x[1]['probability'], reverse=True)
    edges_by_conflict = sorted(edge_info.items(), key=lambda x: x[1]['conflict'], reverse=True)
    
    # ========== LEFT STATS PANEL (CHORDS) ==========
    ax2.axis('off')
    ax2.set_title("CHORD STATISTICS", fontsize=12, fontweight='bold', color='#2C3E50')
    
    chord_lines = []
    
    # Most frequent chords
    chord_lines.append("MOST FREQUENT:")
    chord_lines.append("")
    for chord, info in sorted_chords[:5]:
        chord_lines.append(f"  {chord}: {info['probability']:.6f}")
    
    chord_lines.append("")
    chord_lines.append("─" * 35)
    chord_lines.append("")
    
    # Most conflictful chords
    chord_lines.append("MOST CONFLICTFUL (by collision amount):")
    chord_lines.append("")
    for chord, info in chords_by_conflict[:5]:
        num_collisions = len(info['collisions'])
        chord_lines.append(f"  {chord}: {info['conflict']:.6f} ({num_collisions} total collisions)")
        collision_displays = format_collision_display(info['collisions'], max_display=3)
        for display in collision_displays:
            chord_lines.append(display)
        chord_lines.append("")
    
    chord_text = "\n".join(chord_lines)
    ax2.text(0.05, 0.98, chord_text, transform=ax2.transAxes, fontsize=8.5,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.95))
    
    # ========== RIGHT STATS PANEL (EDGES) ==========
    ax3.axis('off')
    ax3.set_title("EDGE STATISTICS", fontsize=12, fontweight='bold', color='#2C3E50')
    
    edge_lines = []
    
    # Most frequent edges
    edge_lines.append("MOST FREQUENT:")
    edge_lines.append("")
    for (from_chord, to_chord), info in sorted_edges[:5]:
        if info['probability'] >= min_edge_prob:
            edge_lines.append(f"  {from_chord}→{to_chord}: {info['probability']:.6f}")
    
    edge_lines.append("")
    edge_lines.append("─" * 35)
    edge_lines.append("")
    
    # Most conflictful edges
    edge_lines.append("MOST CONFLICTFUL (by collision amount):")
    edge_lines.append("")
    for (from_chord, to_chord), info in edges_by_conflict[:5]:
        num_collisions = len(info['collisions'])
        edge_lines.append(f"  {from_chord}→{to_chord}: {info['conflict']:.6f} ({num_collisions} total collisions)")
        collision_displays = format_collision_display(info['collisions'], max_display=3)
        for display in collision_displays:
            edge_lines.append(display)
        edge_lines.append("")
    
    # Add legend at bottom of edges panel
    edge_lines.append("─" * 35)
    edge_lines.append("")
    edge_lines.append("LEGEND:")
    edge_lines.append("  Node size = Coverage")
    edge_lines.append("  Color = Conflict ratio")
    edge_lines.append(f"  Total chords: {len(chord_info)}")
    edge_lines.append(f"  Total edges: {sum(1 for e in edge_info.values() if e['probability'] >= min_edge_prob)}")
    
    edge_text = "\n".join(edge_lines)
    ax3.text(0.05, 0.98, edge_text, transform=ax3.transAxes, fontsize=8.5,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.95))
    
    plt.tight_layout()
    return fig


# Process left hand
left_chord_info = build_chord_info(chord_freqs['left_chords'])
left_chord_info = add_conflicts_to_chord_info(left_chord_info, chord_conflicts['left_chords'])
left_edge_info = build_edge_info(edge_freqs['left_edges'])
left_edge_info = add_conflicts_to_edge_info(left_edge_info, edge_conflicts['left_edges'])

# Process right hand
right_chord_info = build_chord_info(chord_freqs['right_chords'])
right_chord_info = add_conflicts_to_chord_info(right_chord_info, chord_conflicts['right_chords'])
right_edge_info = build_edge_info(edge_freqs['right_edges'])
right_edge_info = add_conflicts_to_edge_info(right_edge_info, edge_conflicts['right_edges'])

# Plot both banks
print("Plotting left hand layout...")
fig_left = plot_bank_layout(left_chord_info, left_edge_info, "left", min_edge_prob=0.01)
plt.savefig("left_hand_layout.png", dpi=150, bbox_inches='tight')
print("Saved left_hand_layout.png")

print("Plotting right hand layout...")
fig_right = plot_bank_layout(right_chord_info, right_edge_info, "right", min_edge_prob=0.01)
plt.savefig("right_hand_layout.png", dpi=150, bbox_inches='tight')
print("Saved right_hand_layout.png")

plt.show()
