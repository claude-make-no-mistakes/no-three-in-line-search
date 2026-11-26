# No-three-in-line repair exclusions at orders 75 and 77

Any 150-point configuration at order 75 must omit at least 11 points from either of the two distinct 148-point crops of the catalogued order-76 solutions and at least ten points from either embedded order-74 record. It must omit at least nine points from each of the four distinct 144-point crops of the order-78 solution. Any 154-point configuration at order 77 must omit at least 11 points from the 152-point crop of the order-78 solution. Each bound applies to all eight orientations of its source window. The unrestricted orders 75 and 77 remain open. [Original proof](PROOF.md) · [New two-point cuts and certificates](PAIR-CUTS.md) · [Catalogue](https://wwwhomes.uni-bielefeld.de/achim/no3in/table.html)

Thirteen DRAT certificates passed independent checking. A fresh referee reconstructed the first ten DIMACS instances line for line and checked the original pruning argument. The three additional instances use exact two-point deletion costs to shrink the candidate sets. The first positive-semidefinite Lovász–Schrijver lift also admits exact size-$2n$ witnesses at both open grid orders. [First ten certificate hashes](proof-checks.jsonl) · [Three additional hashes](pair-proof-checks.jsonl) · [Lift and verifier](PAIR-CUTS.md)

## Replay

Install the pinned dependency from `requirements.txt`.

```sh
python -B verify.py
python -B repair.py --order 75 --radius 8 --target 150 --budget 150000 --iterations 20 --proof-dir proofs/75-r8
python -B repair.py --order 75 --radius 10 --target 150 --budget 450000 --iterations 20 --max-seeds 2 --prune --proof-dir proofs/75-r10
python -B repair.py --order 77 --radius 8 --target 154 --budget 150000 --iterations 20 --proof-dir proofs/77-r8
python -B repair.py --order 77 --radius 9 --target 154 --budget 250000 --iterations 15 --prune --proof-dir proofs/77-r9
python -B check_proofs.py /path/to/drat-trim proofs/75-r10/n75-s1-r10-t150.cnf
python -B verify_pairs.py
python -B moment_witness.py 13 49 75 77
python -B pair_cuts.py --order 75 --seed-index 1 --include-embeddings --radius 9 --pair-clauses --budget 160000 --proof no3-pair-75-embed1-r9
python -B pair_cuts.py --order 75 --seed-index 4 --include-embeddings --radius 9 --pair-clauses --budget 160000 --proof no3-pair-75-embed4-r9
python -B pair_cuts.py --order 77 --seed-index 1 --include-embeddings --radius 10 --pair-clauses --budget 180000 --proof no3-pair-77-crop-r10
python -B check_proofs.py /path/to/drat-trim no3-pair-75-embed1-r9.cnf no3-pair-75-embed4-r9.cnf no3-pair-77-crop-r10.cnf
```

The hashes identify the files as emitted on Windows, including line endings. The geometric tests independently certify five catalogue records and the blocker data for 11 crop or embedding types. The small-grid check covers 78 repair cases, including six exclusions. [Verification output](verification.json) · [DRAT-trim](https://github.com/marijnheule/drat-trim)

## Search seeds for wider repairs

The C++ search tried 48 seeded runs across the 11 crop and embedding types. The best valid configurations still have 148 points at order 75 and 152 at order 77. The archived full-size configurations contain verified collinear triples. They provide starting points for exact searches deliberately centered outside the certified deletion radii. The separate `partial_repair.py` driver searches for $2n-1$ points and allows one deficient line on each axis. [Near configurations](near-targets.jsonl) · [Configurations farther from their seed](deep-targets.jsonl)
