"""Necessary compatibility of additions near an axis-deficient crop."""

from collections import Counter


def prune(n, seed, radius, conflicts, allowed):
    """Remove additions lacking enough compatible cells on a deficient axis."""
    counts = [Counter(p[axis] for p in seed) for axis in (0, 1)]
    deficits = [(axis, index, 2-counts[axis][index]) for axis in (0, 1) for index in range(n)
                if counts[axis][index] < 2]
    eligible = allowed - set(seed)
    point_bit = {p: 1 << i for i, p in enumerate(sorted(seed))}
    covers = {q: sum(point_bit[p] for pair in conflicts.get(q, ()) for p in pair) for q in eligible}
    pair_counts = {q: len(conflicts.get(q, ())) for q in eligible}
    rounds = []
    while eligible:
        axes = [(axis, index, deficit, [p for p in eligible if p[axis] == index])
                for axis, index, deficit in deficits]
        keep = set()
        for q in eligible:
            for axis, index, deficit, cells in axes:
                need = deficit - (q[axis] == index)
                for p in cells:
                    if need <= 0:
                        break
                    if p == q:
                        continue
                    required = pair_counts[q] + pair_counts[p] - (covers[q] & covers[p]).bit_count()
                    if required <= radius:
                        need -= 1
                if need > 0:
                    break
            else:
                keep.add(q)
        if len(keep) == len(eligible):
            break
        rounds.append(len(eligible)-len(keep))
        eligible = keep
    return eligible | set(seed), rounds
