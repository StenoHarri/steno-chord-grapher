import math
from base_chords import LEFT_CHORDS, RIGHT_CHORDS

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
                
                # Get individual masks for each chord, with bank specified
                left_chords_with_masks = [
                    {'chord': c, 'mask': get_chord_mask(c, 'left'), 'bank': 'left'} 
                    for c in match['left_chords']
                ]
                right_chords_with_masks = [
                    {'chord': c, 'mask': get_chord_mask(c, 'right'), 'bank': 'right'} 
                    for c in match['right_chords']
                ]
                
                formatted_match = {
                    'full_match': match['full_match'],
                    'frequency': freq_info,
                    'left_chords': left_chords_with_masks,
                    'vowel': match['vowel'],
                    'right_chords': right_chords_with_masks,
                    'left_mask': match['left_mask'],
                    'right_mask': match['right_mask']
                }
                formatted_matches.append(formatted_match)
        
        export[combo] = formatted_matches
    
    return export


def get_chord_mask(chord, bank=None):
    """Get the mask for a chord from a specific bank, or try both if bank not specified"""
    if bank == 'left':
        return LEFT_CHORDS.get(chord, "unknown")
    elif bank == 'right':
        return RIGHT_CHORDS.get(chord, "unknown")
    else:
        # Fallback: try both banks (but this is ambiguous)
        return LEFT_CHORDS.get(chord) or RIGHT_CHORDS.get(chord, "unknown")


def serialize_edge(edge, bank):
    """Serialize an edge tuple with masks, specifying which bank"""
    return {
        'from': edge[0],
        'from_mask': get_chord_mask(edge[0], bank),
        'from_bank': bank,
        'to': edge[1],
        'to_mask': get_chord_mask(edge[1], bank),
        'to_bank': bank
    }


def serialize_conflicts_for_export(conflicts, conflict_details):
    """Convert conflicts to a JSON-serializable format"""
    export = []
    for combo, details in sorted(conflict_details.items(), 
                                  key=lambda x: x[1]['losing_prob'], reverse=True):
        
        # Serialize colliding chords with masks (specify bank)
        colliding_left_chords = [
            {'chord': c, 'mask': get_chord_mask(c, 'left'), 'bank': 'left'} 
            for c in details['colliding_left_chords']
        ]
        colliding_right_chords = [
            {'chord': c, 'mask': get_chord_mask(c, 'right'), 'bank': 'right'} 
            for c in details['colliding_right_chords']
        ]
        
        # Serialize colliding edges with directional info, masks, and bank
        colliding_left_edges = [serialize_edge(e, 'left') for e in details['colliding_left_edges']]
        colliding_right_edges = [serialize_edge(e, 'right') for e in details['colliding_right_edges']]
        
        # Serialize word chord info with masks and bank
        word_to_chords_with_masks = {}
        for word, chords in details['word_to_chords'].items():
            word_to_chords_with_masks[word] = {
                'left': [
                    {'chord': c, 'mask': get_chord_mask(c, 'left'), 'bank': 'left'} 
                    for c in chords.get('left', [])
                ],
                'right': [
                    {'chord': c, 'mask': get_chord_mask(c, 'right'), 'bank': 'right'} 
                    for c in chords.get('right', [])
                ]
            }
        
        # Serialize winner chords with masks and bank
        winner_left = [
            {'chord': c, 'mask': get_chord_mask(c, 'left'), 'bank': 'left'} 
            for c in details['winner_left']
        ]
        winner_right = [
            {'chord': c, 'mask': get_chord_mask(c, 'right'), 'bank': 'right'} 
            for c in details['winner_right']
        ]
        
        export.append({
            'combo': combo,
            'winner_word': details['winner_word'],
            'winner_prob': details['winner_prob'],
            'winner_pron': details['winner_pron'],
            'winner_left_chords': winner_left,
            'winner_right_chords': winner_right,
            'losing_words': {w: round(p, 6) for w, p in details['losing_words'].items()},
            'losing_prob': round(details['losing_prob'], 6),
            'num_words': details['num_words'],
            'word_to_pron': details['word_to_pron'],
            'word_to_chords': word_to_chords_with_masks,
            'colliding_left_chords': colliding_left_chords,
            'colliding_right_chords': colliding_right_chords,
            'colliding_left_edges': colliding_left_edges,
            'colliding_right_edges': colliding_right_edges
        })
    return export


def serialize_frequencies_for_export(freq_dict, name):
    """Convert frequency dict to sorted list for export. 'name' is 'left' or 'right'"""
    result = []
    for k, v in sorted(freq_dict.items(), key=lambda x: x[1], reverse=True):
        if isinstance(k, tuple):
            # For edges, store as separate from/to fields with masks and bank
            item = {
                'from': k[0],
                'from_mask': get_chord_mask(k[0], name),
                'from_bank': name,
                'to': k[1],
                'to_mask': get_chord_mask(k[1], name),
                'to_bank': name
            }
        else:
            # For single chords, include the mask and bank
            item = {
                'chord': k,
                'mask': get_chord_mask(k, name),
                'bank': name
            }
        
        entry = {
            **item,
            'probability': round(v, 6),
            'zipf': round(6 + math.log10(v), 2) if v > 0 else 0
        }
        result.append(entry)
    return result


def serialize_frequencies_with_collisions_for_export(freq_dict, collisions_dict, name):
    """
    Convert frequency dict with collision details to sorted list for export.
    Includes ALL collisions (not just top 3) - the graph will decide how many to display.
    """
    result = []
    for k, v in sorted(freq_dict.items(), key=lambda x: x[1], reverse=True):
        if isinstance(k, tuple):
            # For edges
            item = {
                'from': k[0],
                'from_mask': get_chord_mask(k[0], name),
                'from_bank': name,
                'to': k[1],
                'to_mask': get_chord_mask(k[1], name),
                'to_bank': name
            }
        else:
            # For single chords
            item = {
                'chord': k,
                'mask': get_chord_mask(k, name),
                'bank': name
            }
        
        # Get ALL collisions for this chord/edge (not just top 3)
        collisions = collisions_dict.get(k, [])
        
        entry = {
            **item,
            'probability': round(v, 6),
            'zipf': round(6 + math.log10(v), 2) if v > 0 else 0,
            'total_collisions': len(collisions),  # Store the total count
            'top_collisions': collisions  # Store ALL collisions, graph will display first 3
        }
        result.append(entry)
    return result
