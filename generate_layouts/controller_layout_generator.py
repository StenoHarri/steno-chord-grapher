
import json

organism_file = "run1"


layout={
    "left_bank_len": (6+1)*2, # 3 bits for 8 segments, 1 bit for rotation, 2 bits to describe rotation, 1 bit to prevent overlap with same bank
    "right_bank_len": 6+1+6+1,
    "disallowed_startings": "^(nothing)",
    "disallowed_endings": "(nothing)$"
}


# Load the genes
with open(f"generate_layouts/evolved_runs/{organism_file}.json") as f:
    organism = json.load(f)

genes = organism['layout']

for bank in genes:
    print(genes[bank])


