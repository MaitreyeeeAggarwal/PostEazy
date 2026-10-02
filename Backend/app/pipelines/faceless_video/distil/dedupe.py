from app.core.ir import Claim


def jaccard_similarity(text1: str, text2: str) -> float:
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    return len(words1.intersection(words2)) / float(len(words1.union(words2)))


def deduplicate_claims(claims: list[Claim], similarity_threshold: float = 0.86) -> list[Claim]:
    """Clusters claims by textual similarity and retains the highest salience claim per cluster."""
    if not claims:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        texts = [c.text for c in claims]
        vectorizer = TfidfVectorizer().fit_transform(texts)
        sim_matrix = cosine_similarity(vectorizer)
        has_sklearn = True
    except ImportError:
        has_sklearn = False

    # Sort claims by salience descending
    indexed_claims = sorted(enumerate(claims), key=lambda x: x[1].salience, reverse=True)

    retained_claims: list[Claim] = []
    used_indices = set()

    for idx, claim in indexed_claims:
        if idx in used_indices:
            continue

        retained_claims.append(claim)
        used_indices.add(idx)

        # Suppress duplicates
        for other_idx in range(len(claims)):
            if other_idx not in used_indices:
                if has_sklearn:
                    sim = sim_matrix[idx][other_idx]
                else:
                    sim = jaccard_similarity(claims[idx].text, claims[other_idx].text)

                if sim >= similarity_threshold:
                    used_indices.add(other_idx)

    # Re-assign sequential IDs
    for new_id, claim in enumerate(retained_claims, start=1):
        claim.id = new_id

    return retained_claims
