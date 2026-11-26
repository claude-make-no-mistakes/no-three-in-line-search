"""Exact deletion-radius search around a verified no-three-in-line set."""

import argparse
import json
from pathlib import Path

from pysat.card import CardEnc, EncType
from pysat.formula import CNF, IDPool
from pysat.solvers import Solver

from deficits import prune
from grid import blockers, coordinates, crops, point_id, triples, validate


def encode(n, seed, radius, target, conflicts, use_pruning=False):
    occupied = set(seed)
    allowed = occupied | {(x, y) for x in range(n) for y in range(n)
                          if len(conflicts.get((x, y), ())) <= radius}
    rounds = []
    if use_pruning:
        if target != 2*n:
            raise ValueError("deficit pruning requires a full target")
        allowed, rounds = prune(n, seed, radius, conflicts, allowed)
    primary = sorted(point_id(n, p) for p in allowed)
    pool = IDPool(start_from=n*n+1)
    cnf = CNF()
    rows, columns = [[] for _ in range(n)], [[] for _ in range(n)]
    for lit in primary:
        x, y = coordinates(n, lit)
        rows[x].append(lit)
        columns[y].append(lit)
    if target == 2*n:
        for line in rows + columns:
            if len(line) < 2:
                cnf.append([])
            else:
                cnf.extend(CardEnc.equals(lits=line, bound=2, vpool=pool, encoding=EncType.seqcounter).clauses)
    elif target == 2*n-1:
        for lines in (rows, columns):
            deficits = []
            for line in lines:
                flag = pool.id()
                deficits.append(flag)
                cnf.append(line)
                if len(line) < 2:
                    cnf.append([flag])
                    continue
                cnf.extend(clause + [flag] for clause in CardEnc.atleast(
                    lits=line, bound=2, vpool=pool, encoding=EncType.seqcounter).clauses)
                cnf.extend(CardEnc.atmost(lits=line, bound=2, vpool=pool,
                                           encoding=EncType.seqcounter).clauses)
            cnf.extend(CardEnc.atmost(lits=deficits, bound=1, vpool=pool,
                                       encoding=EncType.seqcounter).clauses)
    else:
        for line in rows + columns:
            if len(line) > 2:
                cnf.extend(CardEnc.atmost(lits=line, bound=2, vpool=pool, encoding=EncType.seqcounter).clauses)
        if len(primary) < target:
            cnf.append([])
        else:
            cnf.extend(CardEnc.atleast(lits=primary, bound=target, vpool=pool,
                                       encoding=EncType.seqcounter).clauses)
    cnf.extend(CardEnc.atmost(lits=[-point_id(n, p) for p in sorted(seed)], bound=radius,
                              vpool=pool, encoding=EncType.seqcounter).clauses)
    for point in sorted(allowed - occupied):
        q = point_id(n, point)
        for a, b in conflicts.get(point, ()):
            if a[0] != b[0] and a[1] != b[1]:
                cnf.append([-q, -point_id(n, a), -point_id(n, b)])
    return cnf, set(primary), rounds


def decide(n, seed, radius, target, budget, iterations, proof_stem=None, conflicts=None, use_pruning=False):
    if conflicts is None:
        conflicts = blockers(n, seed)
    cnf, primary, rounds = encode(n, seed, radius, target, conflicts, use_pruning)
    initial = len(cnf.clauses)
    current_count = None
    banned = set()
    proof = None
    with Solver(name="g4", bootstrap_with=cnf, with_proof=proof_stem is not None) as solver:
        result = None
        for _ in range(iterations):
            solver.conf_budget(budget)
            result = solver.solve_limited()
            if result is not True:
                break
            selected = sorted(coordinates(n, lit) for lit in solver.get_model() if lit in primary)
            remaining = list(triples(selected, skip_axes=True))
            current_count = len(remaining)
            if not remaining:
                validate(n, selected)
                if len(selected) < target or len(set(seed)-set(selected)) > radius:
                    raise RuntimeError("returned model does not meet the target or radius")
                break
            for entry in remaining:
                clause = tuple(-point_id(n, p) for p in entry)
                if clause in banned:
                    raise RuntimeError("a previous exclusion appeared in the model")
                banned.add(clause)
                cnf.append(clause)
                solver.add_clause(clause)
            result = None
        if result is False and proof_stem is not None:
            proof = solver.get_proof() or []
            cnf.to_file(str(proof_stem) + ".cnf")
            Path(str(proof_stem) + ".drat").write_text("\n".join(proof) + "\n", encoding="ascii")
        stats = solver.accum_stats()
    record = {"radius": radius, "target": target, "allowed": len(primary), "initial_clauses": initial,
              "added_triples": len(banned), "remaining_violations_in_last_model": current_count,
              "result": "sat" if result is True else "unsat" if result is False else "unresolved",
              "proof_lines": len(proof) if proof is not None else None, "solver_stats": stats}
    if use_pruning:
        record["pruned_by_deficient_axes"] = rounds
    if result is True:
        record["witness"] = selected
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order", type=int, default=75)
    parser.add_argument("--radius", type=int, required=True)
    parser.add_argument("--target", type=int)
    parser.add_argument("--max-seeds", type=int)
    parser.add_argument("--seed-index", type=int)
    parser.add_argument("--budget", type=int, default=100000)
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--proof-dir", type=Path)
    parser.add_argument("--prune", action="store_true")
    parser.add_argument("--include-embeddings", action="store_true")
    args = parser.parse_args()
    records = Path(__file__).with_name("catalogue-records.txt").read_text(encoding="ascii").splitlines()
    seeds = crops(args.order, records, include_embeddings=args.include_embeddings)
    target = args.target if args.target is not None else 2*args.order
    if not 0 <= args.radius < target <= 2*args.order or args.budget <= 0 or args.iterations <= 0:
        parser.error("invalid radius, target, or solver budget")
    if args.proof_dir is not None:
        args.proof_dir.mkdir(parents=True, exist_ok=True)
    ranked = sorted(seeds, key=lambda p: (-len(p), p))
    for index, seed in enumerate(ranked[:args.max_seeds], start=1):
        if args.seed_index is not None and index != args.seed_index:
            continue
        if len(seed) >= target:
            raise ValueError("seed already meets the target")
        proof = None if args.proof_dir is None else args.proof_dir / f"n{args.order}-s{index}-r{args.radius}-t{target}"
        result = decide(args.order, seed, args.radius, target, args.budget, args.iterations, proof,
                        use_pruning=args.prune)
        print(json.dumps({"order": args.order, "seed": index, "seed_size": len(seed),
                          "crops": seeds[seed], **result}), flush=True)
        if "witness" in result:
            return


if __name__ == "__main__":
    main()
