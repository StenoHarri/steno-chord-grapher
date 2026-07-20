
import json

organism_file = "run1"

layout={
    "left_bank_len": (6+1)*2, # 3 bits for 8 segments, 1 bit for rotation, 2 bits to describe rotation, 1 bit to prevent overlap with same bank
    "right_bank_len": 6+1+6+1,
    "disallowed_startings": "^(nothing)",
    "disallowed_endings": "(nothing)$"
}

with open(f"generate_layouts/evolved_runs/{organism_file}.json") as f:
    organism = json.load(f)

genes = organism['layout']

direction_to_three_digit_binary={
    '1': '001',
    '2': '010',
    '3': '011',
    '4': '100',
    '5': '101',
    '6': '110',
    '7': '111',
    '8': '000',
}

def location_to_binary_location(location):
    """
    First 3 bits to describe direction
    
    4th bit if rotation is involved
    5th bit 0 = l, 1=r
    6th bit if rotation is large
    """

    binary_location = direction_to_three_digit_binary[location[0]]

    if not len(location) > 1:
        binary_location += '000'
        return binary_location

    binary_location += '1'

    if location[1] == 'R':
        binary_location += '1'
    else:
        binary_location += '0'

    if len(location) > 2:
        binary_location += '1'
    else:
        binary_location += '0'

    return binary_location

left_chords={}
for left_chord_gene in genes['left_chord_genes']:
    if not left_chord_gene[0]: #If there's no sound
        continue

    binary_location = location_to_binary_location(left_chord_gene[1])
    left_chords[left_chord_gene[0]+'1']  = binary_location+'1'+'000000'+'0'
    left_chords[left_chord_gene[0]+'2']  = '000000'+'0'+binary_location+'1'


right_chords ={}
for right_chord_gene in genes['right_chord_genes']:
    if not right_chord_gene[0]:
        continue

    binary_location = location_to_binary_location(right_chord_gene[1])
    right_chords[right_chord_gene[0]+'1']  = binary_location+'1'+'000000'+'0'
    right_chords[right_chord_gene[0]+'2']  = '000000'+'0'+binary_location+'1'

layout['left_chords'] = left_chords
layout['right_chords'] = right_chords

with open(f"generate_chord_interactions/layouts/controller_steno_{organism_file}.json", "w") as f:
    json.dump(layout, f, indent=4)
