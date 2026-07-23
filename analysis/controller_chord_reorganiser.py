"""
Common chords should be in easier locations to reach, however chords will evolve to share a location with other chords
Thus, it's not just the frequency of the chord, but the frequency of the evolved masks that determines placement

Remove and reorder chords according to their frequencies
Also need to undo the chord duplication as technically chord1 and chord2 of the same name will be in the same joystick rotation
"""
import json

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

# make a note of which chords are solely word final (drop them and treat as suffixes? -Y, -MNT)

# take the most common occurence, delete the other

# order by mask frequency

print(json.dumps(chord_freqs, indent=2))


with open(REORDERED_CHORD_FREQS_FILE, "w", encoding="utf-8") as f:
    json.dump(chord_freqs, f, indent=2)
print(f"Exported layout scores to {REORDERED_CHORD_FREQS_FILE}")