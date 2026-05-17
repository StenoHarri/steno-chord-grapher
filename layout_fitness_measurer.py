import json
import re
import time
import math
from base_chords import LEFT_CHORDS, RIGHT_CHORDS, LEFT_BANK_LEN, RIGHT_BANK_LEN
from find_implied_chords import generate_masks, mask_to_chords
from collections import defaultdict


PRON_FREQ_FILE = "pronunciation_frequency.json"
with open(PRON_FREQ_FILE, "r", encoding="utf-8") as f:
    PRONUNCIATIONS = json.load(f)

VOWELS = {"vowel"}


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
                        'right_chords': right_chords if right_part != "" else []
                    }
                    
                    if combo not in matches:
                        matches[combo] = []
                    
                    # Avoid exact duplicates
                    if match_detail not in matches[combo]:
                        matches[combo].append(match_detail)
    
    # Now check for ambiguity (same combo matches multiple pronunciations)
    ambiguous = {}
    for combo, match_list in matches.items():
        unique_prons = set(m['full_match'] for m in match_list)
        if len(unique_prons) > 1:
            ambiguous[combo] = list(unique_prons)
    
    return matches, ambiguous


def zipf_to_prob(zipf):
    """Convert Zipf frequency to relative probability."""
    return 10 ** (zipf - 6)


def score_layout(matches, ambiguous, pron_freqs):
    coverage_score = 0.0
    conflict_score = 0.0

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

    # Conflict: sum probabilities of "losing" words
    for combo, prons in ambiguous.items():
        word_prob_list = []
        for pron in prons:
            if pron in pron_freqs:
                word_prob_list.extend((w, zipf_to_prob(z)) for w, z in pron_freqs[pron].items())

        if not word_prob_list:
            continue

        max_prob = max(p for _, p in word_prob_list)
        for _, p in word_prob_list:
            if p < max_prob:
                conflict_score += p

    def prob_to_zipf(p):
        return 6 + math.log10(p) if p > 0 else 0

    return {
        "coverage_prob": coverage_score,
        "conflict_prob": conflict_score,
        "coverage_zipf": prob_to_zipf(coverage_score),
        "conflict_zipf": prob_to_zipf(conflict_score),
        "conflict_ratio": conflict_score / coverage_score if coverage_score > 0 else 0
    }

def print_detailed_matches(matches, pron_freqs):
    """Print matches with chord breakdown details including frequency"""
    for combo, match_list in sorted(matches.items()):
        # Format each unique match
        formatted_matches = []
        seen = set()
        for match in match_list:
            # Create a unique key to avoid duplicates
            key = (match['full_match'], tuple(match['left_chords']), tuple(match['right_chords']))
            if key not in seen:
                seen.add(key)
                
                # Get the frequency for this pronunciation
                pron = match['full_match']
                freq_info = "unknown"
                if pron in pron_freqs:
                    # pron_freqs[pron] is a dict like {'word': zipf_freq, ...}
                    # Show the words and their frequencies
                    words_with_freqs = [f"{w} ({freq})" for w, freq in pron_freqs[pron].items()]
                    freq_info = ", ".join(words_with_freqs)
                
                # Add frequency to the match
                match_with_freq = match.copy()
                match_with_freq['frequency'] = freq_info
                formatted_matches.append(match_with_freq)
        
        # Format the output
        match_strings = []
        for match in formatted_matches:
            left_str = str(match['left_chords']) if match['left_chords'] else '[]'
            right_str = str(match['right_chords']) if match['right_chords'] else '[]'
            formatted = (f"full match: '{match['full_match']}', "
                        f"frequency: {match['frequency']}, "
                        f"left chords: {left_str}, "
                        f"vowel: {match['vowel']}, "
                        f"right chords: {right_str}")
            match_strings.append(formatted)
        
        print(f"{combo}: [{'; '.join(match_strings)}]")


if __name__ == "__main__":
    with open(PRON_FREQ_FILE, "r", encoding="utf-8") as f:
        PRONUNCIATIONS = json.load(f)

    start_time = time.time()

    matches, ambiguous = find_vowel_split_matches(
        PRONUNCIATIONS,
        VOWELS,
        LEFT_BANK_MASKS,
        RIGHT_BANK_MASKS
    )

    print("\nAll valid mask combos with chord breakdown:")
    print_detailed_matches(matches, PRONUNCIATIONS)  # Pass PRONUNCIATIONS here

    # Compute coverage and conflict
    scores = score_layout(matches, ambiguous, PRONUNCIATIONS)

    alpha = 10.0
    beta = 1.0
    overall_fitness = math.log10(scores["coverage_prob"]**alpha * (1 - scores["conflict_ratio"])**beta)

    print("\n--- Layout Scoring ---")
    print(f"Coverage (prob): {scores['coverage_prob']:.2f}")
    print(f"Conflict ratio:  {scores['conflict_ratio']:.4%}")
    print(f"Overall fitness: {overall_fitness:,.4f}")

    elapsed = time.time() - start_time
    print(f"\nExecution time: {elapsed:.2f} seconds")
