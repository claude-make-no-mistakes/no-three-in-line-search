"""Verify pair deletion costs and pruning by exhaustive small-grid checks."""

from itertools import combinations, product

from grid import blockers
from pair_cuts import direction, pair_cost, pair_filter


def feasible(points):
    return all((b[0] - a[0]) * (c[1] - a[1]) != (c[0] - a[0]) * (b[1] - a[1])
               for a, b, c in combinations(points, 3))


def check_costs(points, seeds):
    count = 0
    for seed in seeds:
        conflicts = blockers(3, seed)
        index = {p: i for i, p in enumerate(seed)}
        for p, q in combinations(sorted(points - set(seed)), 2):
            rows = [tuple((index[a], index[b]) for a, b in conflicts.get(v, ())) for v in (p, q)]
            forced = sum(1 << index[s] for s in seed if direction(p, s) == direction(p, q))
            best_kept = next(k for k in range(len(seed), -1, -1)
                             if any(feasible((*part, p, q)) for part in combinations(seed, k)))
            if pair_cost(*rows, forced) != len(seed) - best_kept:
                raise RuntimeError(f"pair cost disagrees with enumeration for {seed}, {p}, {q}")
            count += 1
    return count


def check_pruning(points, seeds):
    solutions = {size: [set(part) for part in combinations(sorted(points), size) if feasible(part)]
                 for size in (5, 6)}
    count = 0
    for seed in seeds:
        occupied = set(seed)
        conflicts = blockers(3, seed)
        for radius, target in product(range(len(seed) + 1), solutions):
            allowed, pairs, _, _ = pair_filter(3, seed, radius, target, conflicts)
            for solution in solutions[target]:
                if len(occupied - solution) > radius:
                    continue
                if not solution <= allowed or any(a in solution and b in solution for a, b in pairs):
                    raise RuntimeError(f"pruning lost a repair for {seed}, radius {radius}, target {target}")
                count += 1
    return count


if __name__ == "__main__":
    grid = set(product(range(3), repeat=2))
    valid_seeds = [seed for size in range(1, 7) for seed in combinations(sorted(grid), size) if feasible(seed)]
    print(f"Checked {check_costs(grid, valid_seeds)} pair minima and {check_pruning(grid, valid_seeds)} feasible repairs.")
