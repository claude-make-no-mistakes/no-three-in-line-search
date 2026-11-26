"""Search for a one-point-short repair using exact two-vacancy cuts."""

import argparse
import json
from collections import Counter
from pathlib import Path

from pysat.solvers import Solver

from grid import blockers, coordinates, crops, point_id, triples
from pair_cuts import can_keep, direction
from repair import encode
from verify import is_valid


def vacancy_constraints(n, seed, conflicts, primary, radius):
    """Apply the one-deficient-line allowance separately on each axis.

    Conditional on adding a point, an initially deficient line cannot be
    full if too few other vacancies on that line can coexist with the point.
    Deleting a seed point only increases the number of required vacancies.
    """
    vacant = {coordinates(n, lit) for lit in primary} - set(seed)
    counts = [Counter(point[axis] for point in seed) for axis in (0, 1)]
    deficient = [(axis, index, 2-counts[axis][index]) for axis in (0, 1)
                 for index in range(n) if counts[axis][index] < 2]
    labels = {point: i for i, point in enumerate(sorted(seed))}
    blockers_by_point = {point: tuple((labels[a], labels[b]) for a, b in conflicts.get(point, ()))
                         for point in vacant}
    masks = {point: sum((1 << a) + (1 << b) for a, b in matching)
             for point, matching in blockers_by_point.items()}
    axes = [sorted(p for p in vacant if p[axis] == index) for axis, index, _ in deficient]
    rays = {}
    for candidate in {point for cells in axes for point in cells}:
        ray = Counter()
        for point, i in labels.items():
            ray[direction(candidate, point)] |= 1 << i
        rays[candidate] = ray
    incompatible = set()
    for point in sorted(vacant):
        flag_axes = set()
        reject = False
        negative = -point_id(n, point)
        for (axis, index, deficit), candidates in zip(deficient, axes):
            need = deficit - (point[axis] == index)
            if need <= 0:
                continue
            compatible = []
            for other in candidates:
                if other == point:
                    continue
                pair = tuple(sorted((negative, -point_id(n, other))))
                if pair in incompatible:
                    continue
                left, right = blockers_by_point[point], blockers_by_point[other]
                forced = rays[other][direction(other, point)]
                if not can_keep(left, right, masks[point], masks[other], forced, radius):
                    incompatible.add(pair)
                else:
                    compatible.append(point_id(n, other))
            if len(compatible) < need - 1 or (len(compatible) < need and axis in flag_axes):
                reject = True
                break
            if len(compatible) < need:
                flag_axes.add(axis)
            if need == 2:
                yield [negative, *compatible]
        if reject:
            yield [negative]
    yield from sorted(incompatible)


def search(n, seed, radius, budget, iterations, solver_name, add_cuts=True):
    conflicts = blockers(n, seed)
    cnf, primary, _ = encode(n, seed, radius, 2*n-1, conflicts)
    initial_clauses = len(cnf.clauses)
    if add_cuts:
        cnf.extend(vacancy_constraints(n, seed, conflicts, primary, radius))
    extra_clauses = len(cnf.clauses) - initial_clauses
    count = 0
    result = None
    with Solver(name=solver_name, bootstrap_with=cnf) as solver:
        for _ in range(iterations):
            remaining = budget - solver.accum_stats()["conflicts"]
            if remaining <= 0:
                break
            solver.conf_budget(remaining)
            result = solver.solve_limited()
            if result is not True:
                break
            selected = sorted(coordinates(n, lit) for lit in solver.get_model() if lit in primary)
            missing = list(triples(selected, skip_axes=True))
            if not missing:
                if len(selected) < 2*n-1 or len(set(seed)-set(selected)) > radius or not is_valid(selected):
                    raise RuntimeError("independent witness verification failed")
                return {"result": "sat", "witness": selected, "cuts": extra_clauses,
                        "added_triples": count, "stats": solver.accum_stats()}
            for row in missing:
                solver.add_clause([-point_id(n, point) for point in row])
            count += len(missing)
            result = None
        return {"result": "unsat" if result is False else "unresolved", "cuts": extra_clauses,
                "added_triples": count, "stats": solver.accum_stats()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order", type=int, required=True)
    parser.add_argument("--radius", type=int, required=True)
    parser.add_argument("--source-order", type=int)
    parser.add_argument("--budget", type=int, default=50000)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--solver", default="cd195")
    parser.add_argument("--no-cuts", action="store_true")
    args = parser.parse_args()
    if args.order < 2 or args.radius < 0 or args.budget < 1 or args.iterations < 1:
        parser.error("invalid order, radius, conflict budget or iteration count")
    codes = Path(__file__).with_name("catalogue-records.txt").read_text(encoding="ascii").splitlines()
    groups = crops(args.order, codes, include_embeddings=True)
    for seed, sources in sorted(groups.items(), key=lambda item: (-len(item[0]), item[0])):
        if args.source_order is not None and not any(source[1] == args.source_order for source in sources):
            continue
        result = search(args.order, seed, args.radius, args.budget, args.iterations,
                        args.solver, add_cuts=not args.no_cuts)
        print(json.dumps({"order": args.order, "seed_size": len(seed), "sources": sources,
                          "radius": args.radius, **result}), flush=True)
        if result["result"] == "sat":
            break


if __name__ == "__main__":
    main()
