import json
import re
import time
import math
from layouts.base_chords import LEFT_CHORDS, RIGHT_CHORDS, LEFT_BANK_LEN, RIGHT_BANK_LEN, DISALLOWED_ENDINGS, DISALLOWED_STARTINGS
from chord_tracking.find_implied_chords import generate_masks, mask_to_chords
from collections import defaultdict
from chord_tracking.chord_frequency import *
from chord_tracking.export_chords import *

# Choose which pronunciation file to use
#PRON_FREQ_FILE = "pronunciation_frequency.json"           # merged vowels
PRON_FREQ_FILE = "pronunciation_frequency_specific.json"   # specific vowels
with open(PRON_FREQ_FILE, "r", encoding="utf-8") as f:
    PRONUNCIATIONS = json.load(f)

# Detect whether we're using merged or specific vowels
# Sample multiple pronunciations to catch "vowel" reliably
sample_prons = list(PRONUNCIATIONS.keys())[:3]
if any("vowel" in p for p in sample_prons):
    VOWELS = {"vowel"}
else:
    # Specific vowel dataset - collect all unique vowel labels that appear
    VOWELS = set()
    for pron in PRONUNCIATIONS:
        for phone in pron.split():
            if phone[:2] in {"AA", "AE", "AH", "AO", "AW", "AY",
                             "EH", "ER", "EY", "IH", "IY",
                             "OW", "OY", "UH", "UW"}:
                VOWELS.add(phone)

print(f"Using vowel set: {VOWELS}")

# Output files
MATCHES_FILE = "layout_matches.json"
CONFLICTS_FILE = "layout_conflicts.json"
CHORD_FREQS_FILE = "chord_frequencies.json"
CHORD_CONFLICTS_FILE = "chord_conflicts.json"
EDGE_FREQS_FILE = "edge_frequencies.json"
EDGE_CONFLICTS_FILE = "edge_conflicts.json"
SCORES_FILE = "layout_scores.json"


# The genes are chords, I would like to generate the corresponding layout
def generate_bank_from_chords(chord_map):
    bank = defaultdict(list)
    for chord, mask in chord_map.items():
        bank[mask].append(chord.replace("_",""))
    return dict(bank)


# Build banks automatically
LEFT_BANK = generate_bank_from_chords(LEFT_CHORDS)
RIGHT_BANK = generate_bank_from_chords(RIGHT_CHORDS)


# Build left bank masks with chord composition preserved
LEFT_BANK_MASKS = {}
for mask in generate_masks(LEFT_BANK_LEN):
    # Skip masks with disallowed starts
    if re.search(DISALLOWED_STARTINGS, mask) is not None:
        continue
    chord_compositions = mask_to_chords(mask, LEFT_BANK_LEN, LEFT_BANK)
    if chord_compositions:  # Only include if there are valid chord combinations
        LEFT_BANK_MASKS[mask] = chord_compositions


# Build right bank masks with some disallowed endings
RIGHT_BANK_MASKS = {}
for mask in generate_masks(RIGHT_BANK_LEN):
    # Skip masks with disallowed endings
    if re.search(DISALLOWED_ENDINGS, mask) is not None:
        continue
    chord_compositions = mask_to_chords(mask, RIGHT_BANK_LEN, RIGHT_BANK)
    if chord_compositions:  # Only include if there are valid chord combinations
        RIGHT_BANK_MASKS[mask] = chord_compositions


def find_vowel_split_matches(pronunciations, vowels, left_masks, right_masks):
    """
    Find matches between pronunciations and mask combinations.
    Now preserves which specific chords form each match.
    """
    matches = {}
    
    # find the blank masks
    blank_left = "0" * len(next(iter(left_masks)))
    blank_right = "0" * len(next(iter(right_masks)))
    
    for pron, data in pronunciations.items():
        phonemes = pron.split()
        
        # Find all vowels in the pronunciation
        for i, ph in enumerate(phonemes):
            if ph not in vowels:
                continue  # Only split at vowels
            
            left_part = " ".join(phonemes[:i])
            right_part = " ".join(phonemes[i + 1:])
            
            # left masks - find matches with chord composition preserved
            if left_part == "":
                possible_left = [(blank_left, [[]])]  # blank with empty chord list
            else:
                possible_left = []
                for lm, chord_compositions in left_masks.items():
                    # chord_compositions is a dict: {pron_string: [[chord1, chord2], ...]}
                    if left_part in chord_compositions:
                        # Get all the ways to form this sound with these chords
                        for chord_combo in chord_compositions[left_part]:
                            possible_left.append((lm, chord_combo))
            
            # right masks - find matches with chord composition preserved
            if right_part == "":
                possible_right = [(blank_right, [[]])]
            else:
                possible_right = []
                for rm, chord_compositions in right_masks.items():
                    if right_part in chord_compositions:
                        for chord_combo in chord_compositions[right_part]:
                            possible_right.append((rm, chord_combo))
            
            # Record all valid mask combos for this pronunciation with chord breakdown
            for lm, left_chords in possible_left:
                for rm, right_chords in possible_right:
                    combo = f"{lm}-{ph}-{rm}"
                    
                    # Create the detailed entry with exact chord composition
                    match_detail = {
                        'full_match': pron,
                        'left_chords': left_chords if left_part != "" else [],
                        'vowel': [ph],
                        'right_chords': right_chords if right_part != "" else [],
                        'left_mask': lm,
                        'right_mask': rm
                    }
                    
                    if combo not in matches:
                        matches[combo] = []
                    
                    # Avoid exact duplicates
                    if match_detail not in matches[combo]:
                        matches[combo].append(match_detail)
    
    # Now check for conflicts (same combo matches multiple pronunciations)
    conflicts = {}
    for combo, match_list in matches.items():
        unique_prons = set(m['full_match'] for m in match_list)
        if len(unique_prons) > 1:
            conflicts[combo] = list(unique_prons)
    
    return matches, conflicts


def zipf_to_prob(zipf):
    """Convert Zipf frequency to relative probability."""
    return 10 ** (zipf - 6)


def score_layout(matches, conflicts, pron_freqs):
    coverage_score = 0.0

    # Coverage: sum of all probabilities
    # Remember not to double-count words
    seen_prons = set()
    for combo, match_list in matches.items():
        for match_detail in match_list:
            pron = match_detail['full_match']
            if pron in seen_prons:
                continue
            seen_prons.add(pron)

            if pron not in pron_freqs:
                continue

            word_freqs = pron_freqs[pron]
            total_pron_prob = sum(zipf_to_prob(z) for z in word_freqs.values())
            coverage_score += total_pron_prob

    # Calculate conflicts (collisions)
    (total_conflict_score, conflict_details, 
     left_chord_conflicts, right_chord_conflicts, 
     left_edge_conflicts, right_edge_conflicts,
     left_chord_collisions, right_chord_collisions,
     left_edge_collisions, right_edge_collisions) = calculate_conflicts(
        matches, conflicts, pron_freqs
    )

    def prob_to_zipf(p):
        return 6 + math.log10(p) if p > 0 else 0

    # Ensure ratio is properly bounded
    conflict_ratio = total_conflict_score / coverage_score if coverage_score > 0 else 0
    conflict_ratio = min(conflict_ratio, 1.0)

    return {
        "coverage_prob": coverage_score,
        "conflict_prob": total_conflict_score,
        "coverage_zipf": prob_to_zipf(coverage_score),
        "conflict_zipf": prob_to_zipf(total_conflict_score),
        "conflict_ratio": conflict_ratio,
        "conflict_details": conflict_details,
        "left_chord_conflicts": left_chord_conflicts,
        "right_chord_conflicts": right_chord_conflicts,
        "left_edge_conflicts": left_edge_conflicts,
        "right_edge_conflicts": right_edge_conflicts,
        "left_chord_collisions": left_chord_collisions,
        "right_chord_collisions": right_chord_collisions,
        "left_edge_collisions": left_edge_collisions,
        "right_edge_collisions": right_edge_collisions
    }


if __name__ == "__main__":
    with open(PRON_FREQ_FILE, "r", encoding="utf-8") as f:
        PRONUNCIATIONS = json.load(f)

    start_time = time.time()

    matches, conflicts = find_vowel_split_matches(
        PRONUNCIATIONS,
        VOWELS,
        LEFT_BANK_MASKS,
        RIGHT_BANK_MASKS
    )

    # Calculate chord frequencies (coverage)
    left_freqs, right_freqs = calculate_chord_frequencies(matches, PRONUNCIATIONS)
    
    # Analyze edges/transitions (coverage)
    transitions = print_edge_frequencies(matches, PRONUNCIATIONS)

    # Compute coverage and conflicts
    scores = score_layout(matches, conflicts, PRONUNCIATIONS)

    alpha = 10.0
    beta = 1.0
    
    # Safely compute fitness avoiding complex numbers
    coverage_term = scores["coverage_prob"]**alpha if scores["coverage_prob"] > 0 else 0
    conflict_term = max(0, (1 - scores["conflict_ratio"]))**beta
    
    product = coverage_term * conflict_term
    
    if product > 0:
        overall_fitness = math.log10(product)
    else:
        overall_fitness = float('-inf')  # Worst possible fitness

    # Export all data to JSON files
    print("\n--- Exporting Data ---")
    
    # Export matches
    matches_export = serialize_matches_for_export(matches, PRONUNCIATIONS)
    with open(MATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(matches_export, f, indent=2)
    print(f"Exported {len(matches_export)} mask combos to {MATCHES_FILE}")
    
    # Export conflicts
    conflicts_export = serialize_conflicts_for_export(conflicts, scores['conflict_details'])
    with open(CONFLICTS_FILE, "w", encoding="utf-8") as f:
        json.dump(conflicts_export, f, indent=2)
    print(f"Exported {len(conflicts_export)} conflicts to {CONFLICTS_FILE}")
    
    # Export chord frequencies (coverage)
    chord_freqs_export = {
        'left_chords': serialize_frequencies_for_export(left_freqs, 'left'),
        'right_chords': serialize_frequencies_for_export(right_freqs, 'right')
    }
    with open(CHORD_FREQS_FILE, "w", encoding="utf-8") as f:
        json.dump(chord_freqs_export, f, indent=2)
    print(f"Exported chord frequencies to {CHORD_FREQS_FILE}")
    
    # Export chord conflicts with detailed collisions
    chord_conflicts_export = {
        'left_chords': serialize_frequencies_with_collisions_for_export(
            scores['left_chord_conflicts'], scores['left_chord_collisions'], 'left'
        ),
        'right_chords': serialize_frequencies_with_collisions_for_export(
            scores['right_chord_conflicts'], scores['right_chord_collisions'], 'right'
        )
    }
    with open(CHORD_CONFLICTS_FILE, "w", encoding="utf-8") as f:
        json.dump(chord_conflicts_export, f, indent=2)
    print(f"Exported chord conflicts to {CHORD_CONFLICTS_FILE}")
    
    # Export edge frequencies (coverage)
    edge_freqs_export = {
        'left_edges': serialize_frequencies_for_export(transitions['left_transitions'], 'left'),
        'right_edges': serialize_frequencies_for_export(transitions['right_transitions'], 'right')
    }
    with open(EDGE_FREQS_FILE, "w", encoding="utf-8") as f:
        json.dump(edge_freqs_export, f, indent=2)
    print(f"Exported edge frequencies to {EDGE_FREQS_FILE}")
    
    # Export edge conflicts with detailed collisions
    edge_conflicts_export = {
        'left_edges': serialize_frequencies_with_collisions_for_export(
            scores['left_edge_conflicts'], scores['left_edge_collisions'], 'left'
        ),
        'right_edges': serialize_frequencies_with_collisions_for_export(
            scores['right_edge_conflicts'], scores['right_edge_collisions'], 'right'
        )
    }
    with open(EDGE_CONFLICTS_FILE, "w", encoding="utf-8") as f:
        json.dump(edge_conflicts_export, f, indent=2)
    print(f"Exported edge conflicts to {EDGE_CONFLICTS_FILE}")
    
    # Export scores summary
    scores_export = {
        'coverage_prob': scores['coverage_prob'],
        'coverage_zipf': scores['coverage_zipf'],
        'conflict_prob': scores['conflict_prob'],
        'conflict_zipf': scores['conflict_zipf'],
        'conflict_ratio': scores['conflict_ratio'],
        'overall_fitness': overall_fitness
    }
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores_export, f, indent=2)
    print(f"Exported layout scores to {SCORES_FILE}")

    # Print summary
    print("\n--- Layout Scoring ---")
    print(f"Coverage (prob): {scores['coverage_prob']:.6f} (Zipf: {scores['coverage_zipf']:.2f})")
    print(f"Conflict (prob): {scores['conflict_prob']:.6f} (Zipf: {scores['conflict_zipf']:.2f})")
    print(f"Conflict ratio:  {scores['conflict_ratio']:.4%}")
    print(f"Overall fitness: {overall_fitness:,.4f}")

    elapsed = time.time() - start_time
    print(f"\nExecution time: {elapsed:.2f} seconds")
