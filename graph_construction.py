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
            'subset': subset,  # networkx uses 'subset' for multipartite
            'mask': mask,
            'probability': entry['probability'],
            'zipf': entry['zipf'],
            'conflict': 0.0  # Will be filled in next
        }
    return chord_info


def add_conflicts_to_chord_info(chord_info, conflict_list):
    """Add conflict probabilities to chord info"""
    conflict_map = {}
    for entry in conflict_list:
        conflict_map[entry['chord']] = entry['probability']
    
    for chord, info in chord_info.items():
        info['conflict'] = conflict_map.get(chord, 0.0)
    
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
            'conflict': 0.0  # Will be filled in next
        }
    return edge_info


def add_conflicts_to_edge_info(edge_info, conflict_list):
    """Add conflict probabilities to edge info"""
    conflict_map = {}
    for entry in conflict_list:
        key = (entry['from'], entry['to'])
        conflict_map[key] = entry['probability']
    
    for key, info in edge_info.items():
        info['conflict'] = conflict_map.get(key, 0.0)
    
    return edge_info


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
        # Only pass non-subset attributes to add_node
        node_attrs = {k: v for k, v in info.items() if k != 'subset'}
        G.add_node(chord, subset=subset, **node_attrs)
    
    # Sort subsets
    sorted_subsets = sorted(subsets.keys())
    num_subsets = len(sorted_subsets)
    
    # Add edges with significant probability
    for (from_chord, to_chord), info in edge_info.items():
        if info['probability'] >= min_edge_prob:
            if from_chord in chord_info and to_chord in chord_info:
                G.add_edge(from_chord, to_chord, **info)
    
    # Use networkx's built-in multipartite layout
    pos = nx.multipartite_layout(G, subset_key='subset', align='vertical')
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 12), 
                                    gridspec_kw={'width_ratios': [3, 1]})
    
    # Plot 1: Chord nodes with coverage and conflict
    ax1.set_title(f"{bank_name.capitalize()} Hand Chord Layout\n(Node size = coverage, Color intensity = conflict ratio)", 
                  fontsize=14, fontweight='bold')
    
    # Calculate node sizes based on probability (log scale for better visibility)
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
            # Size based on probability
            size = min_size + (info['probability'] / max_prob) * (max_size - min_size) if max_prob > 0 else min_size
            
            # Color based on conflict ratio (green = low conflict, red = high conflict)
            if info['probability'] > 0 and max_conflict_ratio > 0:
                conflict_ratio = info['conflict'] / info['probability']
                color_intensity = conflict_ratio / max_conflict_ratio
            else:
                color_intensity = 0
            
            # Green to red gradient
            color = (color_intensity, 1 - color_intensity, 0)
            
            ax1.scatter(pos[chord][0], pos[chord][1], s=size, c=[color], 
                       edgecolors='black', linewidth=1.5, zorder=3, alpha=0.8)
            
            # Label
            ax1.annotate(chord, pos[chord], textcoords="offset points", 
                        xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
    
    # Draw edges
    max_edge_prob = max(info['probability'] for info in edge_info.values()) if edge_info else 1
    
    for (from_chord, to_chord), info in edge_info.items():
        if info['probability'] >= min_edge_prob and from_chord in pos and to_chord in pos:
            # Edge width based on probability
            width = 0.5 + (info['probability'] / max_edge_prob) * 4
            
            # Edge color based on conflict ratio
            if info['probability'] > 0:
                conflict_ratio = info['conflict'] / info['probability']
                edge_color = (conflict_ratio, 1 - conflict_ratio, 0)  # green to red
            else:
                edge_color = (0, 1, 0)
            
            alpha = 0.3 + (info['probability'] / max_edge_prob) * 0.5
            
            # Draw curved edge
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
        # Find average x position for this subset
        nodes_in_subset = subsets[subset]
        x_positions = [pos[n][0] for n in nodes_in_subset if n in pos]
        if x_positions:
            avg_x = sum(x_positions) / len(x_positions)
            ax1.text(avg_x, max(pos[n][1] for n in nodes_in_subset if n in pos) + 0.5, 
                    f"Layer {subset}", ha='center', fontsize=10, fontweight='bold')
    
    ax1.axis('equal')
    ax1.axis('off')


    fig.patch.set_facecolor("#00478F")  # Light blue-gray background for entire figure
    ax1.set_facecolor('#D6EAF8')         # Slightly darker blue for the plot area
    ax2.set_facecolor('#E8F0F8')         # Match the figure background
    
    
    # Plot 2: Legend and statistics
    ax2.axis('off')
    ax2.set_title("Statistics & Legend", fontsize=14, fontweight='bold')
    
    # Legend
    legend_text = [
        "NODE LEGEND:",
        "○ Size: Coverage probability (frequency of use)",
        "○ Color: Green (low conflict) → Red (high conflict)",
        "",
        "EDGE LEGEND:",
        "→ Width: Transition probability (frequency of chord pair)",
        "→ Color: Blue (low conflict) → Red (high conflict)",
        "",
        "LAYERS:",
        "Based on position of first '1' in mask",
        "Leftmost 1 determines the layer",
        "",
        f"BANK: {bank_name.upper()} HAND",
        f"Total chords: {len(chord_info)}",
        f"Total edges shown: {sum(1 for e in edge_info.values() if e['probability'] >= min_edge_prob)}",
        "",
        f"Top 5 chords by coverage:"
    ]
    
    sorted_chords = sorted(chord_info.items(), key=lambda x: x[1]['probability'], reverse=True)
    for chord, info in sorted_chords[:5]:
        legend_text.append(f"  {chord}: prob={info['probability']:.4f}, conflict={info['conflict']:.4f}")
    
    legend_text.append("")
    legend_text.append("Top 5 chords by conflict ratio:")
    sorted_by_conflict = sorted(chord_info.items(), 
                                key=lambda x: x[1]['conflict']/x[1]['probability'] if x[1]['probability'] > 0 else 0, 
                                reverse=True)
    for chord, info in sorted_by_conflict[:5]:
        if info['probability'] > 0:
            ratio = info['conflict'] / info['probability']
            legend_text.append(f"  {chord}: ratio={ratio:.2%}")
    
    y_pos = 0.95
    for line in legend_text:
        if any(line.startswith(prefix) for prefix in ["NODE LEGEND", "EDGE LEGEND", "LAYERS", "BANK"]):
            ax2.text(0.05, y_pos, line, transform=ax2.transAxes, fontsize=11, fontweight='bold',
                    verticalalignment='top')
        else:
            ax2.text(0.05, y_pos, line, transform=ax2.transAxes, fontsize=9,
                    verticalalignment='top')
        y_pos -= 0.035
    
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
fig_left = plot_bank_layout(left_chord_info, left_edge_info, "left", min_edge_prob=0.0001)
plt.savefig("left_hand_layout.png", dpi=150, bbox_inches='tight')
print("Saved left_hand_layout.png")

print("Plotting right hand layout...")
fig_right = plot_bank_layout(right_chord_info, right_edge_info, "right", min_edge_prob=0.0001)
plt.savefig("right_hand_layout.png", dpi=150, bbox_inches='tight')
print("Saved right_hand_layout.png")

plt.show()
