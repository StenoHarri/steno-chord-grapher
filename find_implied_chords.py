"""
Given a base layout, construct all the implied chords, such as 1000: s + 0100: t = 1100: st
"""
from allowed_chords import before_vowel, after_vowel


def mask_is_subset(possible_subset, full_mask):
    """If a key is present in the subset that isn't in the full mask, return false"""
    return all(possible_subset_key == '0' or full_mask_key == '1' 
               for possible_subset_key, full_mask_key in zip(possible_subset, full_mask))


def subtract_mask(full, sub):
    return ''.join('0' if s == '1' else f for s, f in zip(sub, full))


def is_intersecting(accumulated_mask, mask):
    """if the mask to add starts before the accumulated mask ends, then fail
    This prevents overlapping chords like SH+TK -> STKH"""
    return accumulated_mask.rfind('1') > mask.find('1')


def find_combinations(target_mask, base_items, start_index=0, accumulated_mask=None):
    """
    Find all combinations of base chords that form the target mask.
    Returns list of chord combinations, where each combination preserves
    the individual chords that make it up.
    """
    if accumulated_mask is None:
        accumulated_mask = '0' * len(target_mask)

    results = []
    for i in range(start_index, len(base_items)):
        mask, name = base_items[i]

        # If the chord to add isn't even a part of the target combination, give up early
        if not mask_is_subset(mask, target_mask):
            continue
        # If the chord to add nestles between the already added chord(s), don't allow that
        if is_intersecting(accumulated_mask, mask):
            continue

        # Show what keys are already being pressed for that target combination
        new_accum = ''.join(str(int(a) | int(m)) for a, m in zip(accumulated_mask, mask))
        remainder = subtract_mask(target_mask, mask)

        if remainder == '0' * len(target_mask):
            # This single chord completes the mask
            results.append([name])
        else:
            # Look for additional chords to complete the mask
            for combo in find_combinations(remainder, base_items, i, new_accum):
                combined = [name] + combo
                
                # Filter to make sure only combos that are actually in the training data come up
                if ' '.join(combined) in before_vowel or ' '.join(combined) in after_vowel:
                    results.append(combined)

    return results


def order_base_items(order_len, base_chords):
    """Starting from the left, smaller chords get added, so this should be size biggest to smallest, 100000 to 000001"""
    ordered_base_items = []
    for i in range(order_len):
        for mask_key, names in base_chords.items():
            if mask_key[i] == '1':
                for name in names:
                    if (mask_key, name) not in ordered_base_items:
                        ordered_base_items.append((mask_key, name))
    return ordered_base_items


def mask_to_chords(mask, order_len, base_chords):
    """
    Convert a mask into all possible chord combinations.
    Returns a dict mapping pronunciation strings to their constituent chord lists.
    Example: {'Z': [['Z']], 'S D': [['S', 'D']]}
    """
    combos = find_combinations(mask, order_base_items(order_len, base_chords))
    
    # Convert to dict: pronunciation -> list of constituent chords
    results = {}
    for combo in combos:
        pron_string = ' '.join(combo)
        if pron_string not in results:
            results[pron_string] = []
        results[pron_string].append(combo)
    
    return results


# Generate all possible binary masks for the left bank
def generate_masks(length):
    """Generate all binary masks of a given length as strings."""
    return [format(i, f"0{length}b") for i in range(2 ** length)]


from collections import defaultdict
def generate_bank(chord_map):
    bank = defaultdict(list)
    for chord, mask in chord_map.items():
        bank[mask].append(chord)
    return dict(bank)
