"""
most implied chords are not found in any English words
"""
import json

PRON_FREQ_FILE = "pronunciation_frequency.json"
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY",
          "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}


before_vowel = set()
after_vowel = set()


with open(PRON_FREQ_FILE, "r") as f:
    data = json.load(f)

for key in data.keys():
    pronunciation = key.split()

    # Find indices of vowels in this sequence
    vowel_indices = [i for i, phoneme in enumerate(pronunciation) if phoneme in VOWELS]


    for idx in vowel_indices:
        # Before vowel: everything up to but not including that vowel
        if idx > 0:
            before_vowel.add(" ".join(pronunciation[:idx]))
        
        # After vowel: everything from that vowel onward
        after_vowel.add(" ".join(pronunciation[idx:]))

