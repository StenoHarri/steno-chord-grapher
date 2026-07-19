import json
import pronouncing
import math
import re
from wordfreq import zipf_frequency
from tqdm import tqdm
from collections import Counter

# input
WORD_LIST_FILE = "generate_pronunciations/words.txt"

# output
PRON_FREQ_FILE = "generate_chord_interactions/pronunciation_data/pronunciation_frequency.json"
PRON_FREQ_SPECIFIC_FILE = "generate_chord_interactions/pronunciation_data/pronunciation_frequency_specific.json"
INITIAL_CLUSTERS_FILE = "generate_chord_interactions/pronunciation_data/initial_clusters.json"
FINAL_CLUSTERS_FILE = "generate_chord_interactions/pronunciation_data/final_clusters.json"

# Load or generate word list
def load_word_list():
    pattern = re.compile(r'^[A-Za-z]+$')  # only letters and optional hyphens
    with open(WORD_LIST_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
        # Filter out words with punctuation or numbers
        words = [w for w in words if pattern.match(w)]
        print(f"Loaded {len(words)} words from {WORD_LIST_FILE} (punctuation removed)")
        return words


PRIMARY_WEIGHT = 0.999  # adjustable primary pronunciation weighting
# words like "content" could have a schwa as the first vowel or not
#currently set to 1 because words like "fifth" that can be pronounced "fifth" or alternatively "fith", but I wish to ignore that


VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY",
          "EH", "ER", "EY", "IH", "IY",
          "OW", "OY", "UH", "UW"}


def is_vowel(phone):
    return any(phone.startswith(v) for v in VOWELS)


def define_pronunciation_frequencies(word, keep_specific_vowels=False):
    """
    Fetch the how common the pronunciation of a given word is.
    If keep_specific_vowels is True, stressed vowels keep their specific identity.
    """
    prons = pronouncing.phones_for_word(word)
    if not prons:
        return {}
    

    # words like "laughed" end in a -ed, but actually end in a T sound
    # I'm pretending as if they end in a D sound as that helps with conflict resolution
    if word.lower().endswith("ed"):
        new_prons = []
        for p in prons:
            phones = p.split()
            # If it ends in a single T, change it to D
            if len(phones) > 0 and phones[-1] == "T":
                phones[-1] = "D"
            new_prons.append(" ".join(phones))
        prons = new_prons


    # plurals create a lot of conflicts, like sax/sacks, claps/collapse
    # So I'm pretending all plurals have the Z sound
    elif word.lower().endswith("s"): #as opposed to se or ce
        new_prons = []
        for p in prons:
            phones = p.split()
            # If it ends in a single S, give it its own phoneme (later I will merge with Z but with smart arpeggiation logic)
            if len(phones) > 0 and phones[-1] in ["S","Z"]: #cyclops, eskimos
                phones[-1] = "SS"
            new_prons.append(" ".join(phones))
        prons = new_prons

    freq_zipf = zipf_frequency(word.lower(), "en")
    if freq_zipf <= 0.0:
        return {}

    # Convert Zipf (log10) → linear space for additive combination
    freq_linear = 10 ** (freq_zipf - 6)

    # Sort pronunciations by length (descending: longest first)
    prons = sorted(prons, key=lambda p: len(p.split()), reverse=True)

    # Weight pronunciations
    n = len(prons)
    if n == 1:
        weights = [1.0]
    else:
        secondary_weight = (1.0 - PRIMARY_WEIGHT) / (n - 1)
        weights = [PRIMARY_WEIGHT] + [secondary_weight] * (n - 1)

    # Remove superfluous vowels
    normalised_prons = {}
    for p, w in zip(prons, weights):
        pron = remove_vowels_but_keep_main(p, keep_specific_vowels=keep_specific_vowels)
        if pron:
            normalised_prons[pron] = normalised_prons.get(pron, 0) + w

    # Filter out pronunciations that have an issue, but keep the valid ones
    valid_prons = {pron: freq_linear * w for pron, w in normalised_prons.items()}

    # If there's at least one valid pronunciation, return the frequencies
    return valid_prons if valid_prons else {}


def remove_vowels_but_keep_main(pron, keep_specific_vowels=False):
    """
    Remove vowels unless they are initial, final, or stressed.
    Also, replace first vowel in any vowel–vowel sequence with Y/W
    (before vowel removal), transferring primary stress if needed.
    
    If keep_specific_vowels is True, stressed vowels keep their specific
    identity (AA1, AE1, etc.) instead of being reduced to 'vowel'.
    """
    #Treat secondary stress as simply unstressed
    pron = pron.replace("2", "0").replace("3", "0")

    #Merge NG G into just NG
    pron = pron.replace("NG G", "NG")

    #Merge th and th, this is usually reflected in spelling too
    pron = pron.replace("DH", "TH")

    # R coloured vowels into vowel+R
    pron = pron.replace("ER0", "AH0 R").replace("ER1", "AH1 R").replace("ER2", "AH2 R")

    # Normalise some glide-vowel combinations
    pron = pron.replace("Y UW", "UW").replace("Y UH", "UH")

    # Unstressed long E into Y
    pron = pron.replace("IY0", "Y").replace("IY2", "Y")

    ## In my accent, unstressed IH is merged with EH
    #pron = pron.replace("IH0", "EH0").replace("IH2", "EH2")

    phones = pron.split()

    def replace_first_vowel_with_glide(phones, i):
        """
        When two vowels are adjacent, replace the first with a Y or W glide,
        and if the first vowel had primary stress, transfer that stress to the
        second vowel.
        Example:
          R IY1 AE0 -> R Y AE1
        """
        if not (0 < i < len(phones)):
            return False

        first = phones[i - 1]
        second = phones[i]

        if not (is_vowel(first) and is_vowel(second)):
            return False

        # Determine glide replacement and target stress transfer
        first_base = first[:2]
        first_stress = first[2:] if len(first) > 2 else ""
        second_base = second[:2]
        second_stress = second[2:] if len(second) > 2 else ""

        if first_base in {"IY", "EY", "AE"}:
            glide = "Y"
        elif first_base in {"AA", "AO", "OW", "UW", "AH", "UH"}:
            glide = "W"
        else:
            return False  # No suitable glide

        # Replace first vowel with glide
        phones[i - 1] = glide

        # If first vowel had primary stress, transfer it
        if "1" in first_stress and "1" not in second_stress:
            phones[i] = second_base + "1"

        return True

    ## Replace IH with EH if it's at the start or end (pin/pen merger)
    #if phones:
    #    if phones[0].startswith("IH"):
    #        phones[0] = phones[0].replace("IH", "EH", 1)
    #    if phones[-1].startswith("IH"):
    #        phones[-1] = phones[-1].replace("IH", "EH", 1)

    #  replace 2 vowels with glide+vowel
    i = 1
    while i < len(phones):
        if is_vowel(phones[i - 1]) and is_vowel(phones[i]):
            replace_first_vowel_with_glide(phones, i)
        i += 1

    # Some words like "fourteen" have multiple main stresses? Only keep the first
    found_primary = False
    for i, ph in enumerate(phones):
        if "1" in ph:
            if not found_primary:
                found_primary = True
            else:
                phones[i] = ph.replace("1", "0")

    # I'm wanting to only keep vowels that are 1: stressed 2: the first sound or 3: the final sound

    # Build final reduced pronunciation
    reduced = []
    last_index = len(phones) - 1
    if phones[-1] == "SS":
        last_index-=1

    for i, ph in enumerate(phones):

        if not is_vowel(ph):
            reduced.append(ph)
            continue

        # Rule 1: primary stress
        if "1" in ph:
            if keep_specific_vowels:
                reduced.append(ph[:2])  # Keep the full vowel with stress (e.g., "IY1")
            else:
                reduced.append("vowel")
            continue

        # Rule 2: first sound
        if i == 0:
            reduced.append(ph[:2])
            continue

        # Rule 3: last sound
        if i == last_index:
            reduced.append(ph[:2])
            continue

        # Rule 4: remove all other vowels
        #
 
    return " ".join(reduced)


# I'm doing this so when a mutation grabs a new cluster it's a cluster that will actually contribute to the fitness
def extract_clusters(pron):
    """Extract initial (left of vowel) and final (right of vowel) clusters"""
    phones = pron.split()

    initials = []
    finals = []

    # Find vowel positions - works for both "vowel" and specific vowels like "IY1"
    vowel_indices = [i for i, p in enumerate(phones) if p == "vowel" or p[:2] in VOWELS]
    
    if not vowel_indices:
        return [], []

    for vi in vowel_indices:
        # Everything before the vowel (exclude the vowel itself)
        if vi > 0:
            left_cluster = " ".join(phones[:vi])
            if left_cluster:
                initials.append(left_cluster)

        # Everything after the vowel (exclude the vowel itself)
        if vi < len(phones) - 1:
            right_cluster = " ".join(phones[vi + 1:])
            if right_cluster:
                finals.append(right_cluster)

    return initials, finals



def build_pronunciation_frequency(words):
    # Merged vowel dataset
    merged_pron_map = {}
    
    # Specific vowel dataset
    specific_pron_map = {}
    
    # Clusters are identical for both, so we only need one set
    initial_counter = Counter()
    final_counter = Counter()
    
    skipped = 0

    for word in tqdm(words, desc="Processing words", unit="word"):
        # Generate merged version
        merged_freqs = define_pronunciation_frequencies(word, keep_specific_vowels=False)
        # Generate specific version
        specific_freqs = define_pronunciation_frequencies(word, keep_specific_vowels=True)
        
        if not merged_freqs and not specific_freqs:
            skipped += 1
            continue

        # Process merged version
        for pron, freq_linear in merged_freqs.items():
            freq_zipf = round(6 + math.log10(freq_linear), 3)
            if freq_zipf < 1:
                continue
            merged_pron_map.setdefault(pron, {})[word] = freq_zipf
            # Extract clusters (only need to do this once since they're identical)
            initials, finals = extract_clusters(pron)
            for ic in initials:
                initial_counter[ic] += freq_linear
            for fc in finals:
                final_counter[fc] += freq_linear

        # Process specific version
        for pron, freq_linear in specific_freqs.items():
            freq_zipf = round(6 + math.log10(freq_linear), 3)
            if freq_zipf < 1:
                continue
            specific_pron_map.setdefault(pron, {})[word] = freq_zipf

    print(f"Skipped {skipped} words that did not have frequency data, writing to JSON")

    # Sort clusters most to least common
    sorted_initials = dict(sorted(initial_counter.items(), key=lambda x: x[1], reverse=True))
    sorted_finals = dict(sorted(final_counter.items(), key=lambda x: x[1], reverse=True))

    return merged_pron_map, specific_pron_map, sorted_initials, sorted_finals


def merge_and_cap_frequencies(pron_map):
    """Apply frequency capping and merge words for a pronunciation map"""
    merged_pron_freq_map = {}

    for pron, words_dict in pron_map.items():
        # Words can only contribute so much, I don't want a common word to dominate, "th" is a rare sound despite "the"
        capped_words = {
            w: min(freq, 3.5)
            for w, freq in words_dict.items()
        }

        total_linear = sum(
            min(10 ** (zipf - 6), 10 ** (3.5 - 6))
            for zipf in words_dict.values()
        )
        total_freq = 6 + math.log10(total_linear)

        sorted_words = sorted(capped_words.items(), key=lambda x: x[1], reverse=True)
        word_label = "/".join(w for w, _ in sorted_words)

        merged_pron_freq_map[pron] = {
            word_label: round(total_freq, 3)
        }

    return merged_pron_freq_map


if __name__ == "__main__":
    words = load_word_list()

    # No longer necessary as I'm capping frequencies at 3.5
    # removing the top 250 words
    # = [(w, zipf_frequency(w.lower(), "en")) for w in words]
    #words_with_freq.sort(key=lambda x: x[1], reverse=True)
    #cutoff = 250
    # excluded_words = [w for w, f in words_with_freq[:cutoff]]
    #words = [w for w, f in words_with_freq[cutoff:]]
    #print(f"Excluded common words (top {cutoff})")

    merged_pron_map, specific_pron_map, initial_clusters, final_clusters = build_pronunciation_frequency(words)
    
    # Apply frequency capping and merging to both datasets
    merged_pron_map = merge_and_cap_frequencies(merged_pron_map)
    specific_pron_map = merge_and_cap_frequencies(specific_pron_map)

    # Write cluster files (shared between both datasets)
    with open(INITIAL_CLUSTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(initial_clusters.keys()), f, indent=2)
    print(f"Written to {INITIAL_CLUSTERS_FILE}")

    with open(FINAL_CLUSTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(final_clusters.keys()), f, indent=2)
    print(f"Written to {FINAL_CLUSTERS_FILE}")

    # Write merged vowel dataset
    with open(PRON_FREQ_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_pron_map, f, indent=2)
    print(f"Written to {PRON_FREQ_FILE}")

    # Write specific vowel dataset
    with open(PRON_FREQ_SPECIFIC_FILE, "w", encoding="utf-8") as f:
        json.dump(specific_pron_map, f, indent=2)
    print(f"Written to {PRON_FREQ_SPECIFIC_FILE}")
