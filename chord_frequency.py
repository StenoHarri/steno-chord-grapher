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


def get_chord_edges(chords):
    """Get edges between consecutive chords on the same bank."""
    edges = []
    for i in range(len(chords) - 1):
        edges.append((chords[i], chords[i+1]))
    return edges


def find_colliding_elements(winner_left, winner_right, loser_left, loser_right, left_mask, right_mask):
    """
    Determine what's actually colliding: individual chords or edges.
    A collision happens when different chord structures produce the same mask.
    """
    colliding_chords = []
    colliding_edges = []
    
    # Check left side collisions
    if left_mask != "0" * len(left_mask):  # Skip blank masks
        # If one side has 1 chord and other has 2+ chords
        if len(winner_left) == 1 and len(loser_left) >= 2:
            # Loser's edges are colliding with winner's chord
            colliding_chords.append(winner_left[0])
            colliding_edges.extend(get_chord_edges(loser_left))
        elif len(loser_left) == 1 and len(winner_left) >= 2:
            # Winner's edges are fine, loser's chord is colliding
            colliding_chords.append(loser_left[0])
        elif len(winner_left) >= 2 and len(loser_left) >= 2:
            # Both are edges - find which specific edges collide
            winner_edges = get_chord_edges(winner_left)
            loser_edges = get_chord_edges(loser_left)
            # Only mark loser's edges as colliding (winner stays)
            colliding_edges.extend(loser_edges)
        elif len(winner_left) == 1 and len(loser_left) == 1:
            # Both are single chords colliding
            colliding_chords.append(loser_left[0])
    
    # Check right side collisions
    if right_mask != "0" * len(right_mask):  # Skip blank masks
        if len(winner_right) == 1 and len(loser_right) >= 2:
            colliding_chords.append(winner_right[0])
            colliding_edges.extend(get_chord_edges(loser_right))
        elif len(loser_right) == 1 and len(winner_right) >= 2:
            colliding_chords.append(loser_right[0])
        elif len(winner_right) >= 2 and len(loser_right) >= 2:
            loser_edges = get_chord_edges(loser_right)
            colliding_edges.extend(loser_edges)
        elif len(winner_right) == 1 and len(loser_right) == 1:
            colliding_chords.append(loser_right[0])
    
    return colliding_chords, colliding_edges


def calculate_conflicts(matches, conflicts, pron_freqs):
    """
    Calculate conflict scores where the same mask combo maps to multiple words.
    Attributes conflict to the specific chords or edges that collide.
    """
    total_conflict_score = 0.0
    conflict_details = {}
    chord_conflict_scores = defaultdict(float)  # chord -> accumulated conflict probability
    edge_conflict_scores = defaultdict(float)   # edge -> accumulated conflict probability
    
    for combo, prons in conflicts.items():
        # Get all words that map to this combo with their probabilities and chord info
        word_info = {}  # word -> {prob, left_chords, right_chords, pron}
        for pron in prons:
            if pron in pron_freqs:
                # Get the chord breakdown for this pronunciation
                for match in matches[combo]:
                    if match['full_match'] == pron:
                        left_chords = match['left_chords']
                        right_chords = match['right_chords']
                        left_mask = match['left_mask']
                        right_mask = match['right_mask']
                        break
                else:
                    left_chords = []
                    right_chords = []
                    left_mask = "0" * len(combo.split('-')[0])
                    right_mask = "0" * len(combo.split('-')[2])
                
                for word, zipf in pron_freqs[pron].items():
                    word_prob = zipf_to_prob(zipf)
                    if word not in word_info:
                        word_info[word] = {
                            'prob': 0, 
                            'left_chords': left_chords, 
                            'right_chords': right_chords,
                            'left_mask': left_mask,
                            'right_mask': right_mask,
                            'pron': pron
                        }
                    word_info[word]['prob'] += word_prob
        
        if len(word_info) <= 1:
            continue  # No actual conflict if only one word
        
        # Find the winning word (most frequent)
        winner_name = max(word_info.items(), key=lambda x: x[1]['prob'])[0]
        winner_info = word_info[winner_name]
        winner_prob = winner_info['prob']
        
        # Calculate losing probability and find what collides
        losing_words = {}
        losing_prob = 0.0
        all_colliding_chords = set()
        all_colliding_edges = set()
        
        for word, info in word_info.items():
            if word != winner_name:
                losing_words[word] = info['prob']
                losing_prob += info['prob']
                
                # Find what specifically collides between winner and this loser
                colliding_chords, colliding_edges = find_colliding_elements(
                    winner_info['left_chords'], winner_info['right_chords'],
                    info['left_chords'], info['right_chords'],
                    info['left_mask'], info['right_mask']
                )
                
                # Attribute conflict to colliding elements
                for chord in colliding_chords:
                    chord_conflict_scores[chord] += info['prob']
                for edge in colliding_edges:
                    edge_conflict_scores[edge] += info['prob']
                
                all_colliding_chords.update(colliding_chords)
                all_colliding_edges.update(colliding_edges)
        
        total_conflict_score += losing_prob
        
        # Get chord breakdown for display
        example_match = matches[combo][0] if combo in matches else None
        chord_breakdown = get_chord_representation(example_match) if example_match else combo
        
        conflict_details[combo] = {
            'chord_breakdown': chord_breakdown,
            'winner_word': winner_name,
            'winner_prob': winner_prob,
            'winner_pron': winner_info['pron'],
            'winner_left': winner_info['left_chords'],
            'winner_right': winner_info['right_chords'],
            'losing_words': losing_words,
            'losing_prob': losing_prob,
            'num_words': len(word_info),
            'word_to_pron': {w: info['pron'] for w, info in word_info.items()},
            'word_to_chords': {w: {'left': info['left_chords'], 'right': info['right_chords']} 
                              for w, info in word_info.items()},
            'colliding_chords': list(all_colliding_chords),
            'colliding_edges': list(all_colliding_edges)
        }
    
    return total_conflict_score, conflict_details, dict(chord_conflict_scores), dict(edge_conflict_scores)


def print_conflict_detail(combo, details):
    """Print detailed breakdown of a single conflict"""
    print(f"\n{'='*80}")
    print(f"CONFLICT DETAIL: {combo}")
    print(f"{'='*80}")
    print(f"\nThis mask combo maps to {details['num_words']} different words:")
    
    print(f"\n  WINNER: {details['winner_word']}")
    print(f"    Frequency: {details['winner_prob']:.6f}")
    print(f"    Pronunciation: {details['winner_pron']}")
    print(f"    Left chords: {details['winner_left']}")
    print(f"    Right chords: {details['winner_right']}")
    
    print(f"\n  LOSERS ({len(details['losing_words'])} words):")
    for word, prob in sorted(details['losing_words'].items(), key=lambda x: x[1], reverse=True):
        pron = details['word_to_pron'].get(word, 'unknown')
        chords = details['word_to_chords'].get(word, {})
        print(f"    {word:<25} freq: {prob:.6f}")
        print(f"      Pronunciation: {pron}")
        print(f"      Left chords: {chords.get('left', [])}")
        print(f"      Right chords: {chords.get('right', [])}")
        print()
    
    if details['colliding_chords']:
        print(f"  Colliding chords (loser's chords that conflict): {details['colliding_chords']}")
    if details['colliding_edges']:
        edge_strs = [f"{e[0]}→{e[1]}" for e in details['colliding_edges']]
        print(f"  Colliding edges (loser's edges that conflict): {edge_strs}")
    
    print(f"\n  Total losing probability: {details['losing_prob']:.6f}")
    print(f"  This amount is attributed to the colliding chords/edges above")


def get_chord_representation(match):
    """Convert a match to its chord representation string (e.g., 'P R CH' or 'IH K S')"""
    parts = []
    
    # Add left chords if any
    if match['left_chords']:
        parts.append(' '.join(match['left_chords']))
    
    # Add vowel
    parts.extend(match['vowel'])
    
    # Add right chords if any
    if match['right_chords']:
        parts.append(' '.join(match['right_chords']))
    
    return ' '.join(parts)