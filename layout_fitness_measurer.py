import json
import re
import time
import math
from base_chords import LEFT_CHORDS, RIGHT_CHORDS, LEFT_BANK_LEN, RIGHT_BANK_LEN
from find_implied_chords import generate_masks, mask_to_chords
from collections import defaultdict
from chord_frequency import *


# Choose which pronunciation file to use
PRON_FREQ_FILE = "pronunciation_frequency.json"           # merged vowels
#PRON_FREQ_FILE = "pronunciation_frequency_specific.json"   # specific vowels
with open(PRON_FREQ_FILE, "r", encoding="utf-8") as f:
    PRONUNCIATIONS = json.load(f)

# Detect whether we're using merged or specific vowels
# If any pronunciation contains "vowel", it's the merged dataset
sample_prons = list(PRONUNCIATIONS.keys())[:3] # 3 words tested because words like 'a' have no primary stress
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


# The genes are chords, I would like to generate the corresponding layout
def generate_bank_from_chords(chord_map):
    bank = defaultdict(list)
    for chord, mask in chord_map.items():
        bank[mask].append(chord)
    return dict(bank)


# Build banks automatically
LEFT_BANK = generate_bank_from_chords(LEFT_CHORDS)
RIGHT_BANK = generate_bank_from_chords(RIGHT_CHORDS)


# Build left bank masks with chord composition preserved
LEFT_BANK_MASKS = {}
for mask in generate_masks(LEFT_BANK_LEN):
    chord_compositions = mask_to_chords(mask, LEFT_BANK_LEN, LEFT_BANK)
    if chord_compositions:  # Only include if there are valid chord combinations
        LEFT_BANK_MASKS[mask] = chord_compositions


# Build right bank masks with some disallowed endings
DISALLOWED_ENDINGS = r'(1..1|11.)$'
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
    total_conflict_score, conflict_details, chord_conflict_scores, left_edge_conflicts, right_edge_conflicts = calculate_conflicts(
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
        "chord_conflict_scores": chord_conflict_scores,
        "left_edge_conflicts": left_edge_conflicts,
        "right_edge_conflicts": right_edge_conflicts
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

    print("\nAll valid mask combos with chord breakdown:")
    print_detailed_matches(matches, PRONUNCIATIONS)

    # Calculate chord frequencies
    left_freqs, right_freqs = calculate_chord_frequencies(matches, PRONUNCIATIONS)
    print_chord_frequencies(left_freqs, right_freqs)
    
    # Analyze edges/transitions
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

    print("\n--- Layout Scoring ---")
    print(f"Coverage (prob): {scores['coverage_prob']:.6f} (Zipf: {scores['coverage_zipf']:.2f})")
    print(f"Conflict (prob): {scores['conflict_prob']:.6f} (Zipf: {scores['conflict_zipf']:.2f})")
    print(f"Conflict ratio:  {scores['conflict_ratio']:.4%}")
    print(f"Overall fitness: {overall_fitness:,.4f}")
    
    # Print conflict summary
    if scores['conflict_details']:
        print("\n--- Mask Combo Conflicts Summary ---")
        print(f"{'Mask Combo':<30} {'Winner':<20} {'Losing Prob':<12} {'Collisions':<30}")
        print("-" * 92)
        for combo, details in sorted(scores['conflict_details'].items(), 
                                     key=lambda x: x[1]['losing_prob'], reverse=True)[:20]:
            collisions = []
            if details['colliding_chords']:
                collisions.extend(details['colliding_chords'])
            if details['colliding_left_edges']:
                collisions.extend([f"L:{e[0]}→{e[1]}" for e in details['colliding_left_edges']])
            if details['colliding_right_edges']:
                collisions.extend([f"R:{e[0]}→{e[1]}" for e in details['colliding_right_edges']])
            collisions_str = ', '.join(collisions[:4])
            print(f"{combo:<30} {details['winner_word']:<20} {details['losing_prob']:<12.6f} {collisions_str:<30}")
        
        # Show detailed example of the highest-conflict combo
        print("\n--- Detailed Example: Highest Conflict Combo ---")
        top_combo = max(scores['conflict_details'].items(), key=lambda x: x[1]['losing_prob'])
        print_conflict_detail(top_combo[0], top_combo[1])
    
    # Show chord conflict scores
    if scores['chord_conflict_scores']:
        print("\n--- Conflict Score by Chord ---")
        print(f"{'Chord':<8} {'Conflict Prob':<15} {'Conflict Zipf':<12}")
        print("-" * 35)
        for chord, prob in sorted(scores['chord_conflict_scores'].items(), 
                                  key=lambda x: x[1], reverse=True)[:15]:
            zipf = 6 + math.log10(prob) if prob > 0 else 0
            print(f"{chord:<8} {prob:<15.6f} {zipf:<12.2f}")
    
    # Show left hand edge conflict scores
    if scores['left_edge_conflicts']:
        print("\n--- Conflict Score by Left-Hand Edge ---")
        print(f"{'Edge':<12} {'Conflict Prob':<15} {'Conflict Zipf':<12}")
        print("-" * 39)
        for (from_chord, to_chord), prob in sorted(scores['left_edge_conflicts'].items(), 
                                                    key=lambda x: x[1], reverse=True)[:15]:
            zipf = 6 + math.log10(prob) if prob > 0 else 0
            print(f"L {from_chord}→{to_chord:<8} {prob:<15.6f} {zipf:<12.2f}")
    
    # Show right hand edge conflict scores
    if scores['right_edge_conflicts']:
        print("\n--- Conflict Score by Right-Hand Edge ---")
        print(f"{'Edge':<12} {'Conflict Prob':<15} {'Conflict Zipf':<12}")
        print("-" * 39)
        for (from_chord, to_chord), prob in sorted(scores['right_edge_conflicts'].items(), 
                                                    key=lambda x: x[1], reverse=True)[:15]:
            zipf = 6 + math.log10(prob) if prob > 0 else 0
            print(f"R {from_chord}→{to_chord:<8} {prob:<15.6f} {zipf:<12.2f}")

    elapsed = time.time() - start_time
    print(f"\nExecution time: {elapsed:.2f} seconds")
