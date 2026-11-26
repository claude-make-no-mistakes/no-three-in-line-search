"""Try to repair a full-size grid set that contains collinear triples."""

from argparse import ArgumentParser
from collections import defaultdict
from itertools import combinations, product
import json
from pathlib import Path

from pysat.solvers import Solver

from grid import coordinates, point_id, triples, validate
from pair_cuts import direction
from repair import encode


def build(n, seed, radius):
    occupied = set(seed)
    extras = {}
    for point in product(range(n), repeat=2):
        if point in occupied:
            continue
        groups = defaultdict(list)
        for old in seed:
            groups[direction(point, old)].append(old)
        conflicts = [members for members in groups.values() if len(members) >= 2]
        if sum(len(group) - 1 for group in conflicts) <= radius:
            extras[point] = conflicts
    allowed = occupied | extras.keys()
    cnf, primary, _ = encode(n, seed, radius, 2 * n, {}, allowed_cells=allowed)
    for bad in triples(sorted(seed), skip_axes=True):
        cnf.append([-point_id(n, vertex) for vertex in bad])
    for new, groups in sorted(extras.items()):
        for members in groups:
            if members[0][0] == members[1][0] or members[0][1] == members[1][1]:
                continue
            for a, b in combinations(members, 2):
                cnf.append([-point_id(n, vertex) for vertex in (new, a, b)])
    return cnf, primary


def run(n, seed, radius, budget, proof_stem=None):
    cnf, primary = build(n, seed, radius)
    info = {"allowed": len(primary), "clauses": len(cnf.clauses), "lazy_triples": 0}
    with Solver(name="cadical195", bootstrap_with=cnf.clauses, with_proof=proof_stem is not None) as sat:
        while (remaining := budget - sat.accum_stats()["conflicts"]) > 0:
            sat.conf_budget(remaining)
            answer = sat.solve_limited()
            if answer is not True:
                if answer is False and proof_stem is not None and info["lazy_triples"] == 0:
                    proof = sat.get_proof()
                    cnf.to_file(str(proof_stem) + ".cnf")
                    with Path(str(proof_stem) + ".drat").open("w", encoding="ascii", newline="\n") as f:
                        f.writelines(line + "\n" for line in proof)
                    info["proof_lines"] = len(proof)
                return {**info, "status": "unsat" if answer is False else "unresolved", **sat.accum_stats()}
            picked = sorted(coordinates(n, lit) for lit in sat.get_model() if lit in primary)
            violations = list(triples(picked, skip_axes=True))
            if not violations:
                validate(n, picked)
                if len(picked) != 2*n or len(set(seed) - set(picked)) > radius:
                    raise RuntimeError("checked solution missed the target or radius")
                return {**info, "status": "solution", "points": picked, **sat.accum_stats()}
            for bad in violations:
                sat.add_clause([-point_id(n, vertex) for vertex in bad])
            info["lazy_triples"] += len(violations)
        return {**info, "status": "unresolved", **sat.accum_stats()}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("identifier", type=int)
    parser.add_argument("radius", type=int)
    parser.add_argument("--budget", type=int, default=100_000)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    rows = args.log.read_text(encoding="utf-8-sig").splitlines()
    if not 1 <= args.identifier <= len(rows) or args.radius < 0 or args.budget < 1:
        parser.error("invalid row index, repair radius, or conflict budget")
    row = json.loads(rows[args.identifier - 1])
    n = row["order"]
    record = row.get("best_deep_target_configuration") or row.get("best_target_configuration")
    if not record:
        parser.error("the selected row has no target configuration")
    seed = [tuple(p) for p in record["points"]]
    if len(seed) != 2*n or len(set(seed)) != len(seed) or args.radius > len(seed):
        parser.error("provide a distinct full-size seed and a radius no larger than the seed")
    if any(not (0 <= x < n and 0 <= y < n) for x, y in seed):
        parser.error("a seed point lies outside the grid")
    print(json.dumps({"order": n, "seed_id": args.identifier, "radius": args.radius,
                      "budget": args.budget, **run(n, seed, args.radius, args.budget, args.proof)}), flush=True)
