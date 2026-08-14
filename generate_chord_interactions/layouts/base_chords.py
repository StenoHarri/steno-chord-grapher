
current_layout = "michela"
current_layout = "extended_stenotype"
current_layout = "evolved_stenotype"
current_layout = "stenotype"
current_layout = "controller_steno_run1"
current_layout = "controller_steno_27_07_2026_run_2"

import json

with open(f"generate_chord_interactions/layouts/{current_layout}.json") as f:
    layout = json.load(f)

LEFT_BANK_LEN = layout["left_bank_len"]
RIGHT_BANK_LEN = layout["right_bank_len"]
DISALLOWED_STARTINGS = layout["disallowed_startings"]
DISALLOWED_ENDINGS = layout["disallowed_endings"]
LEFT_CHORDS = layout["left_chords"]
RIGHT_CHORDS = layout["right_chords"]


# Helper function to strip numbers from chord names for pronunciation matching
def strip_chord_numbers(chord_str):
    """Remove trailing numbers from chord names for pronunciation matching"""
    import re
    # Split into words and strip numbers from each word
    words = chord_str.split()
    stripped_words = [re.sub(r'\d+$', '', word) for word in words]
    return ' '.join(stripped_words)
