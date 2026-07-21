import json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
from pathlib import Path

# Load your data
with open("analysis/chord_data/chord_frequencies.json", "r", encoding="utf-8") as f:
    chord_freqs = json.load(f)

with open("analysis/chord_data/edge_frequencies.json", "r", encoding="utf-8") as f:
    edge_freqs = json.load(f)

with open("analysis/chord_data/chord_conflicts.json", "r", encoding="utf-8") as f:
    chord_conflicts = json.load(f)

with open("analysis/chord_data/edge_conflicts.json", "r", encoding="utf-8") as f:
    edge_conflicts = json.load(f)

# If the folder doesn't exist, make it
Path("analysis/chord_analysis").mkdir(
    parents=True,
    exist_ok=True,
)

def analyze_hubs_clean(chord_freqs, chord_conflicts, edge_freqs, edge_conflicts, bank_name):
    """
    Clean degree distribution analysis focusing on:
    1. Structural degree (how many connections)
    2. Weighted degree by coverage (how much usage)
    3. Weighted degree by conflict (how much collision)
    """
    
    # === BUILD NETWORK ===
    # Nodes with coverage and conflict info
    nodes = {}
    for entry in chord_freqs:
        chord = entry['chord']
        nodes[chord] = {
            'coverage_prob': entry['probability'],
            'conflict_prob': 0.0
        }
    
    for entry in chord_conflicts:
        chord = entry['chord']
        if chord in nodes:
            nodes[chord]['conflict_prob'] = entry['probability']
    
    # Calculate conflict ratio for each node
    for chord in nodes:
        if nodes[chord]['coverage_prob'] > 0:
            nodes[chord]['conflict_ratio'] = nodes[chord]['conflict_prob'] / nodes[chord]['coverage_prob']
        else:
            nodes[chord]['conflict_ratio'] = 0
    
    # Build edges
    edges = {}
    for entry in edge_freqs:
        key = (entry['from'], entry['to'])
        edges[key] = {
            'coverage_prob': entry['probability'],
            'conflict_prob': 0.0
        }
    
    for entry in edge_conflicts:
        key = (entry['from'], entry['to'])
        if key in edges:
            edges[key]['conflict_prob'] = entry['probability']
    
    # Calculate THREE types of degree:
    # 1. Structural degree: number of connections (ignoring weight)
    structural_in = defaultdict(int)
    structural_out = defaultdict(int)
    
    # 2. Coverage-weighted degree: sum of edge coverage probabilities
    coverage_in = defaultdict(float)
    coverage_out = defaultdict(float)
    
    # 3. Conflict-weighted degree: sum of edge conflict probabilities
    conflict_in = defaultdict(float)
    conflict_out = defaultdict(float)
    
    # Also track which edges actually have conflicts
    edges_with_conflict = set()
    
    for (from_chord, to_chord), edge_info in edges.items():
        # Structural degree (just count connections)
        structural_out[from_chord] += 1
        structural_in[to_chord] += 1
        
        # Coverage-weighted degree
        coverage_out[from_chord] += edge_info['coverage_prob']
        coverage_in[to_chord] += edge_info['coverage_prob']
        
        # Conflict-weighted degree
        if edge_info['conflict_prob'] > 0:
            conflict_out[from_chord] += edge_info['conflict_prob']
            conflict_in[to_chord] += edge_info['conflict_prob']
            edges_with_conflict.add((from_chord, to_chord))
    
    # Total degrees per node
    structural_total = {}
    coverage_total = {}
    conflict_total = {}
    
    for chord in nodes:
        structural_total[chord] = structural_in.get(chord, 0) + structural_out.get(chord, 0)
        coverage_total[chord] = coverage_in.get(chord, 0) + coverage_out.get(chord, 0)
        conflict_total[chord] = conflict_in.get(chord, 0) + conflict_out.get(chord, 0)
    
    # === FIND HUBS ===
    # Coverage hubs: top nodes by coverage-weighted degree
    coverage_hubs = sorted(nodes.keys(), key=lambda c: coverage_total[c], reverse=True)[:10]
    
    # Conflict hubs: top nodes by conflict-weighted degree
    conflict_hubs = sorted(nodes.keys(), key=lambda c: conflict_total[c], reverse=True)[:10]
    
    # High conflict-ratio nodes (conflict per unit of coverage)
    # Only consider nodes with some minimum coverage to avoid division by tiny numbers
    min_coverage = np.median([coverage_total[c] for c in nodes if coverage_total[c] > 0])
    significant_nodes = [c for c in nodes if coverage_total[c] >= min_coverage]
    conflict_ratio_hubs = sorted(significant_nodes, 
                                 key=lambda c: nodes[c]['conflict_ratio'], 
                                 reverse=True)[:10]
    
    # === PLOT 1: Coverage vs Conflict Degree Scatter ===
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # Plot 1a: Coverage-weighted degree vs Conflict-weighted degree
    ax = axes[0]
    x_vals = [coverage_total[c] for c in nodes]
    y_vals = [conflict_total[c] for c in nodes]
    
    # Color by whether node has high conflict ratio
    colors = ['red' if nodes[c]['conflict_ratio'] > np.median([nodes[n]['conflict_ratio'] for n in nodes]) 
              else 'blue' for c in nodes]
    sizes = [max(50, coverage_total[c] * 50) for c in nodes]  # Size by coverage
    
    ax.scatter(x_vals, y_vals, c=colors, s=sizes, alpha=0.6, edgecolors='black', linewidth=0.5)
    
    # Label top coverage hubs
    for chord in coverage_hubs[:5]:
        ax.annotate(chord, (coverage_total[chord], conflict_total[chord]),
                   fontsize=11, fontweight='bold', color='darkblue',
                   xytext=(5, 5), textcoords='offset points')
    
    # Label top conflict hubs that aren't coverage hubs
    for chord in conflict_hubs[:5]:
        if chord not in coverage_hubs[:5]:
            ax.annotate(chord, (coverage_total[chord], conflict_total[chord]),
                       fontsize=11, fontweight='bold', color='darkred',
                       xytext=(5, -10), textcoords='offset points')
    
    # Correlation
    r, p = stats.pearsonr(x_vals, y_vals)
    ax.text(0.05, 0.95, f'Pearson r = {r:.3f}\np = {p:.4f}', 
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_xlabel('Coverage-Weighted Degree (sum of edge frequencies)', fontsize=11)
    ax.set_ylabel('Conflict-Weighted Degree (sum of edge conflicts)', fontsize=11)
    ax.set_title(f'{bank_name.upper()} Hand\nCoverage Hubs vs Conflict Hubs', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Low conflict ratio'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='High conflict ratio')
    ]
    ax.legend(handles=legend_elements)
    
    # Plot 1b: Structural degree distribution (log-log)
    ax = axes[1]
    struct_degrees = list(structural_total.values())
    struct_degrees_pos = [d for d in struct_degrees if d > 0]
    
    # Histogram with log bins
    bins = np.logspace(np.log10(min(struct_degrees_pos)), np.log10(max(struct_degrees_pos)), 20)
    ax.hist(struct_degrees_pos, bins=bins, alpha=0.7, color='green', edgecolor='black')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Structural Degree (number of connections)', fontsize=11)
    ax.set_ylabel('Number of Nodes', fontsize=11)
    ax.set_title(f'{bank_name.upper()} Hand\nStructural Degree Distribution', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    plt.savefig(f'analysis/chord_analysis/{bank_name}_hubs_clean.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    # === PLOT 2: Hub Comparison Bar Chart ===
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Compare top 10 chords by coverage degree
    top_10 = coverage_hubs[:10]
    x_pos = np.arange(len(top_10))
    width = 0.35
    
    coverage_vals = [coverage_total[c] for c in top_10]
    conflict_vals = [conflict_total[c] for c in top_10]
    
    # Normalize for comparison (as percentage of max)
    coverage_norm = [v / max(coverage_vals) * 100 for v in coverage_vals]
    conflict_norm = [v / max(coverage_vals) * 100 for v in conflict_vals]  # Same scale
    
    bars1 = ax.bar(x_pos - width/2, coverage_norm, width, label='Coverage Degree', color='blue', alpha=0.7)
    bars2 = ax.bar(x_pos + width/2, conflict_norm, width, label='Conflict Degree', color='red', alpha=0.7)
    
    ax.set_xlabel('Chords (sorted by coverage degree)', fontsize=11)
    ax.set_ylabel('Normalized Degree (% of max coverage)', fontsize=11)
    ax.set_title(f'{bank_name.upper()} Hand: Top 10 Coverage Hubs\nCoverage vs Conflict Contribution', fontsize=13, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(top_10, fontsize=10)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(f'analysis/chord_analysis/{bank_name}_hub_comparison_bars.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    # === PLOT 3: Conflict Ratio Analysis ===
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Only nodes with meaningful coverage
    significant = [(c, nodes[c]['conflict_ratio'], coverage_total[c]) 
                   for c in significant_nodes]
    significant.sort(key=lambda x: x[1], reverse=True)
    
    top_conflict_ratio = significant[:15]
    chords_cr = [x[0] for x in top_conflict_ratio]
    ratios = [x[1] for x in top_conflict_ratio]
    coverages = [x[2] for x in top_conflict_ratio]
    
    # Bar chart of conflict ratios
    ax = axes[0]
    colors = ['darkred' if r > np.median(ratios) else 'orange' for r in ratios]
    bars = ax.bar(range(len(chords_cr)), ratios, color=colors, alpha=0.7, edgecolor='black')
    ax.set_xticks(range(len(chords_cr)))
    ax.set_xticklabels(chords_cr, rotation=45, ha='right', fontsize=10)
    ax.set_ylabel('Conflict Ratio (conflict/coverage)', fontsize=11)
    ax.set_title(f'{bank_name.upper()} Hand\nNodes with Highest Conflict Ratio', fontsize=13, fontweight='bold')
    ax.axhline(y=np.median(ratios), color='blue', linestyle='--', alpha=0.5, label=f'Median ratio')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Scatter: Coverage vs Conflict Ratio
    ax = axes[1]
    all_coverages = [coverage_total[c] for c in significant_nodes]
    all_ratios = [nodes[c]['conflict_ratio'] for c in significant_nodes]
    
    ax.scatter(all_coverages, all_ratios, alpha=0.6, c='purple', edgecolors='black', linewidth=0.5)
    
    # Label interesting points
    for chord in chords_cr[:5]:
        ax.annotate(chord, (coverage_total[chord], nodes[chord]['conflict_ratio']),
                   fontsize=9, fontweight='bold')
    
    ax.set_xlabel('Coverage-Weighted Degree', fontsize=11)
    ax.set_ylabel('Conflict Ratio (conflict/coverage)', fontsize=11)
    ax.set_title(f'{bank_name.upper()} Hand\nCoverage vs Conflict Efficiency', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Correlation between coverage and conflict ratio
    r_cr, p_cr = stats.pearsonr(all_coverages, all_ratios)
    ax.text(0.05, 0.95, f'Correlation: r={r_cr:.3f}\n(p={p_cr:.4f})', 
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(f'analysis/chord_analysis/{bank_name}_conflict_ratio.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    # === SUMMARY ===
    print(f"\n{'='*60}")
    print(f"HUB ANALYSIS SUMMARY - {bank_name.upper()} HAND")
    print(f"{'='*60}")
    
    print(f"\nNETWORK OVERVIEW:")
    print(f"  Total nodes: {len(nodes)}")
    print(f"  Total edges: {len(edges)}")
    print(f"  Edges with conflicts: {len(edges_with_conflict)} ({len(edges_with_conflict)/len(edges)*100:.1f}%)")
    
    print(f"\nCOVERAGE HUBS (Top 5 most-used chords):")
    for i, chord in enumerate(coverage_hubs[:5], 1):
        print(f"  {i}. {chord}: coverage_degree={coverage_total[chord]:.4f}, "
              f"structural_connections={structural_total[chord]}, "
              f"conflict_ratio={nodes[chord]['conflict_ratio']:.4f}")
    
    print(f"\nCONFLICT HUBS (Top 5 most-conflicted chords):")
    for i, chord in enumerate(conflict_hubs[:5], 1):
        print(f"  {i}. {chord}: conflict_degree={conflict_total[chord]:.4f}, "
              f"coverage_degree={coverage_total[chord]:.4f}, "
              f"ratio={nodes[chord]['conflict_ratio']:.4f}")
    
    print(f"\nINEFFICIENT CHORDS (High conflict per usage):")
    for i, chord in enumerate(conflict_ratio_hubs[:5], 1):
        print(f"  {i}. {chord}: ratio={nodes[chord]['conflict_ratio']:.4f}, "
              f"coverage={coverage_total[chord]:.4f}, "
              f"conflict={conflict_total[chord]:.4f}")
    
    # Overlap analysis
    coverage_set = set(coverage_hubs[:5])
    conflict_set = set(conflict_hubs[:5])
    overlap = coverage_set & conflict_set
    print(f"\nOVERLAP: {len(overlap)}/5 of top coverage hubs are also top conflict hubs")
    print(f"  Shared: {overlap}")
    print(f"  Coverage-only: {coverage_set - conflict_set}")
    print(f"  Conflict-only: {conflict_set - coverage_set}")
    
    # Network science interpretation
    r, p = stats.pearsonr([coverage_total[c] for c in nodes], 
                          [conflict_total[c] for c in nodes])
    print(f"\nCORRELATION: r={r:.3f}, p={p:.4f}")
    if r > 0.7:
        print("  → Strong positive correlation: More usage = More conflicts")
        print("  → Implication: Design flaw - can't increase coverage without increasing conflicts")
    elif r > 0.4:
        print("  → Moderate correlation: Usage and conflicts are related but not identical")
        print("  → Implication: Some highly-used chords manage to avoid conflicts")
    else:
        print("  → Weak correlation: Conflicts are distributed differently from usage")
        print("  → Implication: The layout successfully isolates conflicts away from common chords")
    
    return {
        'nodes': nodes,
        'coverage_hubs': coverage_hubs,
        'conflict_hubs': conflict_hubs,
        'conflict_ratio_hubs': conflict_ratio_hubs,
        'overlap': overlap,
        'correlation': r
    }


# Run for both hands
print("\n" + "="*60)
print("LEFT HAND ANALYSIS")
print("="*60)
left_results = analyze_hubs_clean(
    chord_freqs['left_chords'], chord_conflicts['left_chords'],
    edge_freqs['left_edges'], edge_conflicts['left_edges'], "left"
)

print("\n" + "="*60)
print("RIGHT HAND ANALYSIS")
print("="*60)
right_results = analyze_hubs_clean(
    chord_freqs['right_chords'], chord_conflicts['right_chords'],
    edge_freqs['right_edges'], edge_conflicts['right_edges'], "right"
)
