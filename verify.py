"""Check record geometry and brute-force small repair cases independently."""

import json
from collections import Counter, defaultdict
from itertools import combinations, product
from math import gcd
from pathlib import Path

from deficits import prune
from grid import blockers, crops, decode
from repair import decide


def collinear(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) == (b[1]-a[1])*(c[0]-a[0])


def is_valid(points):
    return not any(collinear(*t) for t in combinations(points, 3))


def by_directions(point, seed):
    grouped = defaultdict(list)
    for x, y in seed:
        dx, dy = x-point[0], y-point[1]
        d = gcd(dx, dy)
        if dx < 0 or (dx == 0 and dy < 0):
            d = -d
        grouped[dx//d, dy//d].append((x, y))
    return {tuple(sorted(pair)) for pair in grouped.values() if len(pair) == 2}


def checked_blockers(n, seed):
    direct = blockers(n, seed)
    occupied = set(seed)
    for q in product(range(n), repeat=2):
        if q not in occupied:
            actual = direct.get(q, ())
            assert len({p for pair in actual for p in pair}) == 2*len(actual)
            assert set(actual) == by_directions(q, seed)
    return direct


def check_small():
    cases = solutions = excluded = 0
    for n in (3, 4):
        board = tuple(product(range(n), repeat=2))
        for gap in (0, 1):
            target = 2*n-gap
            valid = [set(p) for p in combinations(board, target) if is_valid(p)]
            solutions += len(valid)
            seeds = [sorted(base)[deletion:] for base in valid[:3] for deletion in (1, 2)]
            for candidate in combinations(board, target-1):
                if is_valid(candidate) and all(not set(candidate) <= p for p in valid):
                    seeds.append(candidate)
                    break
            for seed in seeds:
                conflict = checked_blockers(n, seed)
                for radius in (0, 1, 2):
                    feasible = [p for p in valid if len(set(seed)-p) <= radius]
                    if gap == 0:
                        allowed = {p for p in board if len(conflict.get(p, ())) <= radius}
                        reduced, _ = prune(n, seed, radius, conflict, allowed)
                        assert all(p <= reduced for p in feasible)
                    outcome = decide(n, seed, radius, target, 10000, 20, conflicts=conflict,
                                     use_pruning=(gap == 0))
                    assert outcome["result"] == ("sat" if feasible else "unsat")
                    excluded += not feasible
                    cases += 1
    assert excluded
    return cases, solutions, excluded


if __name__ == "__main__":
    records = Path(__file__).with_name("catalogue-records.txt").read_text(encoding="ascii").splitlines()
    for code in records:
        n, points = decode(code)
        assert is_valid(points)
        for axis in (0, 1):
            assert Counter(p[axis] for p in points) == {v: 2 for v in range(n)}
    crop_cases = 0
    for n in (75, 77):
        for seed in crops(n, records, include_embeddings=True):
            assert is_valid(seed)
            checked_blockers(n, seed)
            crop_cases += 1
    cases, solutions, excluded = check_small()
    print(json.dumps({"verified_catalogue_records": len(records), "verified_crop_and_embedding_types": crop_cases,
                      "direct_small_target_sets": solutions, "small_repair_comparisons": cases,
                      "small_unsat_comparisons": excluded}))
