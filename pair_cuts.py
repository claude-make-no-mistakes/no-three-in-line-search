"""Search seed repairs using exact two-insertion deletion costs."""

from argparse import ArgumentParser
from collections import Counter
import json
from math import gcd
from pathlib import Path

from pysat.solvers import Solver

from deficits import prune as previous_prune
from grid import blockers, coordinates, crops, point_id, triples, validate
from repair import encode


def direction(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    scale = gcd(dx, dy)
    if dx < 0 or (dx == 0 and dy < 0):
        scale = -scale
    return dx // scale, dy // scale


def cover_size(first, second):
    """Size of a minimum vertex cover of the union of two matchings."""
    adjacency = {}
    for a, b in (*first, *second):
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    needed = 0
    while adjacency:
        vertex = next(iter(adjacency))
        stack = [vertex]
        size = 0
        while stack:
            v = stack.pop()
            row = adjacency.pop(v, None)
            if row is not None:
                size += 1
                stack.extend(row)
        needed += size // 2
    return needed


def pair_cost(first, second, forced):
    first = tuple((a, b) for a, b in first if not (forced & ((1 << a) | (1 << b))))
    second = tuple((a, b) for a, b in second if not (forced & ((1 << a) | (1 << b))))
    return forced.bit_count() + cover_size(first, second)


def can_keep(first, second, mask_a, mask_b, forced, radius):
    if not forced:
        # Cheap endpoints of the interval containing the exact cost.
        upper = len(first) + len(second)
        if upper <= radius:
            return True
        if upper - (mask_a & mask_b).bit_count() > radius:
            return False
    return pair_cost(first, second, forced) <= radius


def pair_filter(n, seed, radius, target, conflicts):
    occupied = set(seed)
    allowed = occupied | {(x, y) for x in range(n) for y in range(n)
                          if len(conflicts.get((x, y), ())) <= radius}
    previous_rounds = []
    if target == 2 * n:
        allowed, previous_rounds = previous_prune(n, seed, radius, conflicts, allowed)
    seeds = sorted(seed)
    labels = {p: i for i, p in enumerate(seeds)}
    points = sorted(allowed - occupied)
    indices = range(len(points))
    pairs = [tuple((labels[a], labels[b]) for a, b in conflicts.get(q, ())) for q in points]
    covers = [sum((1 << a) + (1 << b) for a, b in row) for row in pairs]
    counts = [Counter(p[axis] for p in seed) for axis in (0, 1)]
    minimum = 2 if target == 2 * n else 1
    deficits = [
        (minimum - counts[axis][line], sum(1 << i for i, p in enumerate(points) if p[axis] == line))
        for axis in (0, 1) for line in range(n) if counts[axis][line] < minimum
    ]

    def positions(mask):
        while mask:
            bit = mask & -mask
            yield bit.bit_length() - 1
            mask ^= bit

    pivots = sorted({i for _, mask in deficits for i in positions(mask)})
    # Rows at mandatory additions also capture triples with two new points.
    incompat = [0] * len(points)
    pivot_set = set(pivots)
    for i in pivots:
        p = points[i]
        rays = {}
        for a, seed_point in enumerate(seeds):
            d = direction(p, seed_point)
            rays[d] = rays.get(d, 0) | (1 << a)
        for j, q in enumerate(points):
            if j == i or (j < i and j in pivot_set):
                continue
            forced = rays.get(direction(p, q), 0)
            if not can_keep(pairs[i], pairs[j], covers[i], covers[j], forced, radius):
                incompat[i] |= 1 << j
                incompat[j] |= 1 << i

    alive = (1 << len(points)) - 1
    rounds = []
    while alive:
        keep = 0
        axes = [(d, mask & alive) for d, mask in deficits]
        for i in positions(alive):
            if all((mask & ~incompat[i]).bit_count() >= d for d, mask in axes):
                keep |= 1 << i
        if keep == alive:
            break
        rounds.append((alive ^ keep).bit_count())
        alive = keep
    edges = [(points[i], points[j]) for i in positions(alive)
             for j in positions(incompat[i] & alive & ~((1 << (i + 1)) - 1))]
    return occupied | {points[i] for i in positions(alive)}, edges, previous_rounds, rounds


def build(n, seed, radius, target, pair_clauses=False):
    conflicts = blockers(n, seed)
    allowed, incompatible, legacy, rounds = pair_filter(n, seed, radius, target, conflicts)
    cnf, primary, _ = encode(n, seed, radius, target, conflicts, allowed_cells=allowed)
    if pair_clauses:
        cnf.extend([-point_id(n, a), -point_id(n, b)] for a, b in incompatible)
    return cnf, primary, {"allowed": len(allowed), "legacy_prunes": legacy,
                          "exact_pair_prunes": rounds, "incompatible_pairs": len(incompatible),
                          "pair_clauses": pair_clauses}


def search(n, seed, radius, target, budget, iterations, pair_clauses, proof_stem=None):
    cnf, primary, details = build(n, seed, radius, target, pair_clauses)
    initial = len(cnf.clauses)
    cuts = set()
    selected = None
    with Solver(name="cadical195", bootstrap_with=cnf.clauses,
                with_proof=proof_stem is not None) as solver:
        for _ in range(iterations):
            remaining = budget - solver.accum_stats()["conflicts"]
            if remaining <= 0:
                answer = None
                break
            solver.conf_budget(remaining)
            answer = solver.solve_limited()
            if answer is not True:
                break
            model = sorted(coordinates(n, i) for i in solver.get_model() if i in primary)
            violations = list(triples(model, skip_axes=True))
            if not violations:
                validate(n, model)
                if len(model) < target or len(set(seed) - set(model)) > radius:
                    raise RuntimeError("SAT model failed target or radius validation")
                selected = model
                break
            for violation in violations:
                clause = tuple(-point_id(n, p) for p in violation)
                if clause in cuts:
                    raise RuntimeError("a cut is violated after insertion")
                cuts.add(clause)
                solver.add_clause(clause)
                cnf.append(clause)
            answer = None
        proof = solver.get_proof() if answer is False and proof_stem is not None and not cuts else None
        stats = solver.accum_stats()
    if answer is False and proof_stem is not None:
        if cuts:
            # Replay against the final formula from a fresh solver so the
            # exported trace never relies on incremental input-clause order.
            with Solver(name="cadical195", bootstrap_with=cnf.clauses, with_proof=True) as replay:
                if replay.solve() is not False:
                    raise RuntimeError("the final formula did not replay as UNSAT")
                proof = replay.get_proof()
        if not proof:
            raise RuntimeError("solver did not return an UNSAT proof")
        cnf.to_file(str(proof_stem) + ".cnf")
        with Path(str(proof_stem) + ".drat").open("w", encoding="ascii", newline="\n") as handle:
            for line in proof:
                handle.write(line + "\n")
    status = "sat" if selected is not None else "unsat" if answer is False else "unresolved"
    result = {**details, "initial_clauses": initial, "added_triples": len(cuts),
              "result": status, "solver_stats": stats}
    if selected is not None:
        result["witness"] = selected
    if answer is False and proof is not None:
        result["proof_lines"] = len(proof)
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--order", type=int, required=True)
    parser.add_argument("--radius", type=int, required=True)
    parser.add_argument("--target", type=int)
    parser.add_argument("--seed-index", type=int, required=True)
    parser.add_argument("--include-embeddings", action="store_true")
    parser.add_argument("--pair-clauses", action="store_true")
    parser.add_argument("--budget", type=int, default=250_000)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    target = args.target if args.target is not None else 2 * args.order
    if target not in (2 * args.order - 1, 2 * args.order):
        parser.error("pair cuts support targets 2n or 2n−1")
    records = Path(__file__).with_name("catalogue-records.txt").read_text(encoding="ascii").splitlines()
    seeds = crops(args.order, records, include_embeddings=args.include_embeddings)
    sorted_seeds = sorted(seeds, key=lambda p: (-len(p), p))
    if not 1 <= args.seed_index <= len(sorted_seeds):
        parser.error(f"seed index must be in 1..{len(sorted_seeds)}")
    seed = sorted_seeds[args.seed_index - 1]
    if not 0 <= args.radius <= len(seed) or args.budget < 1 or args.iterations < 1:
        parser.error("invalid radius, conflict budget or iteration count")
    outcome = search(args.order, seed, args.radius, target, args.budget, args.iterations,
                     args.pair_clauses, args.proof)
    print(json.dumps({"order": args.order, "radius": args.radius, "target": target,
                      "seed": args.seed_index, "seed_size": len(seed), "crops": seeds[seed],
                      "conflict_budget": args.budget, **outcome}), flush=True)


if __name__ == "__main__":
    main()
