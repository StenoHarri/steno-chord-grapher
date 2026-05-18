from collections import defaultdict
from layout_fitness_measurer import zipf_to_prob
import math
 

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


def calculate_chord_frequencies(matches, pron_freqs):
    """
    Calculate the frequency contribution for each chord.
    Returns two defaultdicts: left_chord_freqs and right_chord_freqs
    """
    left_chord_freqs = defaultdict(float)
    right_chord_freqs = defaultdict(float)
    
    for combo, match_list in matches.items():
        for match in match_list:
            pron = match['full_match']
            if pron not in pron_freqs:
                continue
            
            # Calculate total frequency for this pronunciation
            word_freqs = pron_freqs[pron]
            total_freq = sum(zipf_to_prob(z) for z in word_freqs.values())
            
            # Add frequency to each left chord
            for chord in match['left_chords']:
                left_chord_freqs[chord] += total_freq
            
            # Add frequency to each right chord
            for chord in match['right_chords']:
                right_chord_freqs[chord] += total_freq
    
    return dict(left_chord_freqs), dict(right_chord_freqs)


def print_chord_frequencies(left_freqs, right_freqs, min_freq=0.01):
    """Print chord frequencies sorted by frequency."""
    print("\n--- Left Hand Chord Frequencies ---")
    print(f"{'Chord':<8} {'Probability':<12} {'Zipf':<8}")
    print("-" * 30)
    for chord, prob in sorted(left_freqs.items(), key=lambda x: x[1], reverse=True):
        if prob >= min_freq:
            zipf = 6 + math.log10(prob) if prob > 0 else 0
            print(f"{chord:<8} {prob:<12.6f} {zipf:<8.2f}")
    
    print(f"\n--- Right Hand Chord Frequencies ---")
    print(f"{'Chord':<8} {'Probability':<12} {'Zipf':<8}")
    print("-" * 30)
    for chord, prob in sorted(right_freqs.items(), key=lambda x: x[1], reverse=True):
        if prob >= min_freq:
            zipf = 6 + math.log10(prob) if prob > 0 else 0
            print(f"{chord:<8} {prob:<12.6f} {zipf:<8.2f}")

def print_edge_frequencies(matches, pron_freqs):
    """
    Analyze edge frequencies between chords on the SAME bank only.
    This tracks transitions like S→L (both left chords) or K→SH (both right chords).
    """
    # Track transitions: (prev_chord, next_chord) -> frequency
    left_transitions = defaultdict(float)
    right_transitions = defaultdict(float)
    
    for combo, match_list in matches.items():
        for match in match_list:
            pron = match['full_match']
            if pron not in pron_freqs:
                continue
            
            # Calculate total frequency for this pronunciation
            word_freqs = pron_freqs[pron]
            total_freq = sum(zipf_to_prob(z) for z in word_freqs.values())
            
            left_chords = match['left_chords']
            right_chords = match['right_chords']
            
            # Within left-hand transitions
            for i in range(len(left_chords) - 1):
                left_transitions[(left_chords[i], left_chords[i+1])] += total_freq
            
            # Within right-hand transitions
            for i in range(len(right_chords) - 1):
                right_transitions[(right_chords[i], right_chords[i+1])] += total_freq
    
    print("\n--- Left-Hand Chord Transitions (Edges) ---")
    print(f"{'From':<8} {'To':<8} {'Probability':<12} {'Zipf':<8}")
    print("-" * 40)
    for (from_chord, to_chord), prob in sorted(left_transitions.items(), 
                                                key=lambda x: x[1], reverse=True):
        zipf = 6 + math.log10(prob) if prob > 0 else 0
        print(f"{from_chord:<8} {to_chord:<8} {prob:<12.6f} {zipf:<8.2f}")
    
    print(f"\n--- Right-Hand Chord Transitions (Edges) ---")
    print(f"{'From':<8} {'To':<8} {'Probability':<12} {'Zipf':<8}")
    print("-" * 40)
    for (from_chord, to_chord), prob in sorted(right_transitions.items(), 
                                                key=lambda x: x[1], reverse=True):
        zipf = 6 + math.log10(prob) if prob > 0 else 0
        print(f"{from_chord:<8} {to_chord:<8} {prob:<12.6f} {zipf:<8.2f}")
    
    # Combine both for analysis
    all_transitions = {}
    all_transitions.update(left_transitions)
    all_transitions.update(right_transitions)
    
    return {
        'left_transitions': dict(left_transitions),
        'right_transitions': dict(right_transitions),
        'all_transitions': all_transitions
    }
