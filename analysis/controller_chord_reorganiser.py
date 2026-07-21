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
