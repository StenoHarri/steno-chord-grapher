"""
Common chords should be in easier locations to reach, however chords will evolve to share a location with other chords
Thus, it's not just the frequency of the chord, but the frequency of the evolved masks that determines placement

Remove and reorder chords according to their frequencies
Also need to undo the chord duplication as technically chord1 and chord2 of the same name will be in the same joystick rotation
"""
import json

# Input files
CHORD_FREQS_FILE = "analysis/chord_data/mask_frequencies.json"

# Load data
with open(CHORD_FREQS_FILE, "r", encoding="utf-8") as f:
    chord_freqs = json.load(f)

print(chord_freqs)

# remove chords that are rare

# remove chords that are only used 3 times

# remove chords that contribute to disproportionately more collisions

# shove 1st and 2nd occurences of a chord into the same

# make a note of which chords are solely word final (drop them and treat as suffixes? -Y, -MNT)

# take the most common occurence, delete the other

# order by mask frequency
