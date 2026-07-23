"""
Common chords should be in easier locations to reach, however chords will evolve to share a location with other chords
Thus, it's not just the frequency of the chord, but the frequency of the evolved masks that determines placement

Remove and reorder chords according to their frequencies
Also need to undo the chord duplication as technically chord1 and chord2 of the same name will be in the same joystick rotation
"""
import json
import math

def probability_to_zipf(probability_percent):
    """Convert a percentage probability to a Zipf score."""
    if probability_percent <= 0:
        return 0
    return round(math.log10(probability_percent / 100) + 9, 2)

# Input file
CHORD_FREQS_FILE = "analysis/chord_data/mask_frequencies.json"

# Output file
REORDERED_CHORD_FREQS_FILE = "analysis/chord_data/reordered_mask_frequencies.json"

# Load data
with open(CHORD_FREQS_FILE, "r", encoding="utf-8") as f:
    chord_freqs = json.load(f)

print(chord_freqs)

# remove chords that are rare
RARE_CUTOFF = 3.5  # zipf, equivalent to a probability of 0.003162

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    filtered_masks = []

    for mask in chord_freqs[bank]:
        kept_chords = []

        for chord in mask["chords"]:
            # remove chords with this zipf
            if chord["zipf"] < RARE_CUTOFF:
                continue

            kept_chords.append(chord)

        if kept_chords:
            mask["chords"] = kept_chords
            filtered_masks.append(mask)

    chord_freqs[bank] = filtered_masks

# remove chords that are only used 1-9 times

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    filtered_masks = []

    for mask in chord_freqs[bank]:
        kept_chords = []

        for chord in mask["chords"]:
            if chord["count"] < 10:
                continue

            kept_chords.append(chord)

        if kept_chords:
            mask["chords"] = kept_chords
            filtered_masks.append(mask)

    chord_freqs[bank] = filtered_masks

# remove chords that contribute to disproportionately more collisions
COLLISION_RATIO = 1.5 # remove if its contribution to collisions is closer to double its contribution to the mask

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    filtered_masks = []

    for mask in chord_freqs[bank]:
        kept_chords = []

        for chord in mask["chords"]:
            mask_share = chord["percent_of_mask"]
            collision_share = chord["percent_of_mask_collisions"]

            if (
                mask_share > 0
                and collision_share > COLLISION_RATIO * mask_share
            ):
                continue

            kept_chords.append(chord)

        if kept_chords:
            mask["chords"] = kept_chords
            filtered_masks.append(mask)

    chord_freqs[bank] = filtered_masks

# shove 1st and 2nd occurences of a chord into the same mask

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    merged_masks = {}

    for mask in chord_freqs[bank]:
        bits = mask["mask"]

        # One half is empty, the other contains the real location.
        left_half = bits[:6]
        right_half = bits[7:13]

        canonical_mask = left_half if left_half != "000000" else right_half

        if canonical_mask not in merged_masks:
            merged_masks[canonical_mask] = {
                "bank": mask["bank"],
                "mask": canonical_mask,
                "probability": 0.0,
                "zipf": 0.0,
                "collision_probability": 0.0,
                "collision_zipf": 0.0,
                "chords": [],
            }

        merged = merged_masks[canonical_mask]

        merged["probability"] += mask["probability"]
        merged["collision_probability"] += mask["collision_probability"]
        merged["chords"].extend(mask["chords"])

    # recompute derived values
    for merged in merged_masks.values():
        if merged["probability"] > 0:
            merged["zipf"] = round(
                max(ch["zipf"] for ch in merged["chords"]),
                2,
            )

        if merged["collision_probability"] > 0:
            merged["collision_zipf"] = round(
                max(ch.get("collision_zipf", 0) for ch in merged["chords"]),
                2,
            )

    chord_freqs[bank] = list(merged_masks.values())

# make a note of which chords are mostly initial or successive
# If one's mostly successive, drop them and treat as suffixes? -Y, -MNT

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    occurrences = {}

    for mask in chord_freqs[bank]:
        for chord in mask["chords"]:
            name = chord["chord"]

            if not name.endswith(("1", "2")):
                continue

            base = name[:-1]
            variant = name[-1]

            if base not in occurrences:
                occurrences[base] = {
                    "1": 0,
                    "2": 0,
                }

            occurrences[base][variant] += chord["count"]

    imbalance = []

    for base, counts in occurrences.items():
        initial = counts["1"]
        successive = counts["2"]
        total = initial + successive

        if total == 0:
            continue

        dominant = max(initial, successive)
        imbalance.append({
            "chord": base,
            "initial": initial,
            "successive": successive,
            "total": total,
            "dominance": dominant / total,
        })

    imbalance.sort(
        key=lambda x: (x["dominance"], x["total"]),
        reverse=True,
    )

    print(f"\n{bank} most unbalanced chords:")

    for item in imbalance[:30]:
        print(
            f"{item['chord']:12} "
            f"1:{item['initial']:6} "
            f"2:{item['successive']:6} "
            f"{item['dominance']*100:5.1f}%"
        )

# take the most common occurence of a duplicate chord on the same mask("R Y1" vs "R Y2"), delete the other

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    for mask in chord_freqs[bank]:
        best_versions = {}

        for chord in mask["chords"]:
            # Strip trailing 1/2 to get the logical chord name.
            base_name = chord["chord"]
            if base_name.endswith(("1", "2")):
                base_name = base_name[:-1]

            if (
                base_name not in best_versions
                or chord["count"] > best_versions[base_name]["count"]
            ):
                best_versions[base_name] = chord

        mask["chords"] = list(best_versions.values())

# recalculate mask statistics

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    for mask in chord_freqs[bank]:

        # recompute totals from the remaining chords
        mask["probability"] = sum(
            chord["probability"]
            for chord in mask["chords"]
        )

        mask["collision_probability"] = sum(
            chord["collision_probability"]
            for chord in mask["chords"]
        )

        # recompute Zipf values from the probabilities
        mask["zipf"] = probability_to_zipf(mask["probability"])
        mask["collision_zipf"] = probability_to_zipf(
            mask["collision_probability"]
        )

        # recompute each chord's contribution to the mask
        for chord in mask["chords"]:

            if mask["probability"] > 0:
                chord["percent_of_mask"] = round(
                    100 * chord["probability"] / mask["probability"],
                    1,
                )
            else:
                chord["percent_of_mask"] = 0

            if mask["collision_probability"] > 0:
                chord["percent_of_mask_collisions"] = round(
                    100
                    * chord["collision_probability"]
                    / mask["collision_probability"],
                    1,
                )
            else:
                chord["percent_of_mask_collisions"] = 0

# order by mask frequency

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    chord_freqs[bank].sort(
        key=lambda mask: mask["probability"],
        reverse=True,
    )

    for mask in chord_freqs[bank]:
        mask["chords"].sort(
            key=lambda chord: chord["probability"],
            reverse=True,
        )

# print simple summary of masks in frequency order

for bank in ("left_masks", "right_masks"):
    if bank not in chord_freqs:
        continue

    print(f"\n{bank}")

    for i, mask in enumerate(chord_freqs[bank], start=1):
        chords = ", ".join(
            f"{chord['chord']} ({chord['count']})"
            for chord in mask["chords"]
        )

        print(
            f"mask {i}: {mask['mask']} "
            f"[{mask['probability']:.3f}%] -> {chords}"
        )

with open(REORDERED_CHORD_FREQS_FILE, "w", encoding="utf-8") as f:
    json.dump(chord_freqs, f, indent=2)
print(f"Exported layout scores to {REORDERED_CHORD_FREQS_FILE}")
