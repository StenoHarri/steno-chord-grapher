import math

def serialize_matches_for_export(matches, pron_freqs):
    """Convert matches to a JSON-serializable format with frequency info"""
    export = {}
    for combo, match_list in matches.items():
        formatted_matches = []
        seen = set()
        for match in match_list:
            key = (match['full_match'], tuple(match['left_chords']), tuple(match['right_chords']))
            if key not in seen:
                seen.add(key)
                
                pron = match['full_match']
                freq_info = {}
                if pron in pron_freqs:
                    freq_info = pron_freqs[pron]
                
                formatted_match = {
                    'full_match': match['full_match'],
                    'frequency': freq_info,
                    'left_chords': match['left_chords'],
                    'vowel': match['vowel'],
                    'right_chords': match['right_chords'],
                    'left_mask': match['left_mask'],
                    'right_mask': match['right_mask']
                }
                formatted_matches.append(formatted_match)
        
        export[combo] = formatted_matches
    
    return export


def serialize_conflicts_for_export(conflicts, conflict_details):
    """Convert conflicts to a JSON-serializable format"""
    export = []
    for combo, details in sorted(conflict_details.items(), 
                                  key=lambda x: x[1]['losing_prob'], reverse=True):
        export.append({
            'combo': combo,
            'winner_word': details['winner_word'],
            'winner_prob': details['winner_prob'],
            'winner_pron': details['winner_pron'],
            'winner_left_chords': details['winner_left'],
            'winner_right_chords': details['winner_right'],
            'losing_words': {w: round(p, 6) for w, p in details['losing_words'].items()},
            'losing_prob': round(details['losing_prob'], 6),
            'num_words': details['num_words'],
            'word_to_pron': details['word_to_pron'],
            'word_to_chords': details['word_to_chords'],
            'colliding_left_chords': details['colliding_left_chords'],
            'colliding_right_chords': details['colliding_right_chords'],
            'colliding_left_edges': [list(e) for e in details['colliding_left_edges']],
            'colliding_right_edges': [list(e) for e in details['colliding_right_edges']]
        })
    return export


def serialize_frequencies_for_export(freq_dict, name):
    """Convert frequency dict to sorted list for export"""
    result = []
    for k, v in sorted(freq_dict.items(), key=lambda x: x[1], reverse=True):
        if isinstance(k, tuple):
            # For edges, store as separate from/to fields
            item = {'from': k[0], 'to': k[1]}
        else:
            item = {'chord': k}
        
        entry = {
            **item,
            'probability': round(v, 6),
            'zipf': round(6 + math.log10(v), 2) if v > 0 else 0
        }
        result.append(entry)
    return result
