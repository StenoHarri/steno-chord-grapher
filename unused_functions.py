
class FitnessCache:
    def __init__(self, shared_dict=None):
        # If shared_dict is provided, use it; otherwise, fallback to normal dict
        self.cache = shared_dict if shared_dict is not None else {}

    def key(self, individual):
        left, right = individual

        def freeze(part):
            return tuple(sorted(
                (cluster, mask)
                for gene in part
                for cluster, mask in gene.items()
            ))

        return (freeze(left), freeze(right))

    def get(self, individual):
        return self.cache.get(self.key(individual))

    def set(self, individual, value):
        self.cache[self.key(individual)] = value


def bank_genes_into_bank_chords(chord_list):
    chords = {}
    for d in chord_list:
        for cluster, mask in d.items():
            chords.setdefault(mask, []).append(cluster)
    return chords


def score_individual(individual, cache):
    # If this individual's already been scored, it should be in the cache
    if cache is None:
        from evolve_population import worker_cache
        cache = worker_cache

    cached_value = cache.get(individual)
    if cached_value is not None:
        return cached_value

    try:
        left_bank_genes, right_bank_genes = individual

        left_bank = bank_genes_into_bank_chords(left_bank_genes)
        right_bank = bank_genes_into_bank_chords(right_bank_genes)

        # Build masks with chord composition preserved
        left_masks = {}
        for mask in generate_masks(LEFT_BANK_LEN):
            chord_compositions = mask_to_chords(mask, LEFT_BANK_LEN, left_bank)
            if chord_compositions:
                left_masks[mask] = chord_compositions

        right_masks = {}
        for mask in generate_masks(RIGHT_BANK_LEN):
            if re.search(DISALLOWED_ENDINGS, mask) is not None:
                continue
            chord_compositions = mask_to_chords(mask, RIGHT_BANK_LEN, right_bank)
            if chord_compositions:
                right_masks[mask] = chord_compositions

        matches, ambiguous = find_vowel_split_matches(
            PRONUNCIATIONS,
            VOWELS,
            left_masks,
            right_masks
        )

        scores = score_layout(matches, ambiguous, PRONUNCIATIONS)

        coverage = scores["coverage_prob"]
        conflict = scores["conflict_ratio"]

        # initial target, not penalising conflicts too much
        alpha = 10.0
        beta = 1.0

        # target, once it gets to here, conflicts will be at 0.0015
        coverage_threshold = 522  # WSI is at 522.67
        target_conflict = 0.0012  # WSI is at 001237

        if coverage > (coverage_threshold + 5) and conflict < target_conflict:
            overall_fitness = math.log10(coverage**alpha * (1 - conflict)**beta)
            cache.set(individual, overall_fitness)
            return overall_fitness

        # Sigmoid function for gradual penalty
        a = 0.15
        midpoint = 486
        activation = 1 / (1 + math.exp(-a * (coverage - midpoint)))

        excess_conflict = max(0.0, conflict - target_conflict)

        # penalty strength
        s = 50
        penalty = 1 + s * activation * excess_conflict

        overall_fitness = math.log10(coverage**alpha * (1 - conflict)**beta / penalty)
        
        cache.set(individual, overall_fitness)
        return overall_fitness

    except Exception as e:
        print("Error scoring individual:", e)
        return 1


def score_individual_detailed(individual):
    left_bank_genes, right_bank_genes = individual

    left_bank = bank_genes_into_bank_chords(left_bank_genes)
    right_bank = bank_genes_into_bank_chords(right_bank_genes)

    left_masks = {}
    for mask in generate_masks(LEFT_BANK_LEN):
        chord_compositions = mask_to_chords(mask, LEFT_BANK_LEN, left_bank)
        if chord_compositions:
            left_masks[mask] = chord_compositions

    right_masks = {}
    for mask in generate_masks(RIGHT_BANK_LEN):
        if re.search(DISALLOWED_ENDINGS, mask) is not None:
            continue
        chord_compositions = mask_to_chords(mask, RIGHT_BANK_LEN, right_bank)
        if chord_compositions:
            right_masks[mask] = chord_compositions

    matches, ambiguous = find_vowel_split_matches(
        PRONUNCIATIONS,
        VOWELS,
        left_masks,
        right_masks
    )

    scores = score_layout(matches, ambiguous, PRONUNCIATIONS)

    alpha = 10.0
    beta = 1.0
    overall_fitness = math.log10(scores["coverage_prob"]**alpha * (1 - scores["conflict_ratio"])**beta)

    print("\n--- Layout Scoring ---")
    print(f"Coverage (prob): {scores['coverage_prob']:.2f}")
    print(f"Conflict ratio:  {scores['conflict_ratio']:.4%}")
    print(f"Overall fitness: {overall_fitness:,.4f}")

    return overall_fitness