# No-three-in-line repair exclusions at orders 75 and 77

Any 150-point configuration at order 75 must omit at least 11 points from either of the two distinct 148-point crops of the catalogued order-76 solutions. It must omit at least nine points from each of the four distinct 144-point crops of the order-78 solution. Any 154-point configuration at order 77 must omit at least ten points from the 152-point crop of the order-78 solution. Each bound applies to all eight orientations of its crop. The unrestricted orders 75 and 77 remain open. [Proof](PROOF.md) · [Catalogue](https://wwwhomes.uni-bielefeld.de/achim/no3in/table.html)

The ten DRAT certificates passed independent checking. The UNSAT instances used the radius bound, row and column counts, and constraints from lines through two seed points. A fresh referee reconstructed all ten DIMACS instances line for line and checked the pruning argument. [Certificate hashes](proof-checks.jsonl)

## Replay

Install the pinned dependency from `requirements.txt`.

```sh
python -B verify.py
python -B repair.py --order 75 --radius 8 --target 150 --budget 150000 --iterations 20 --proof-dir proofs/75-r8
python -B repair.py --order 75 --radius 10 --target 150 --budget 450000 --iterations 20 --max-seeds 2 --prune --proof-dir proofs/75-r10
python -B repair.py --order 77 --radius 8 --target 154 --budget 150000 --iterations 20 --proof-dir proofs/77-r8
python -B repair.py --order 77 --radius 9 --target 154 --budget 250000 --iterations 15 --prune --proof-dir proofs/77-r9
python -B check_proofs.py /path/to/drat-trim proofs/75-r10/n75-s1-r10-t150.cnf
```

The hashes identify the files as emitted on Windows, including line endings. The geometric tests independently certify five catalogue records and the blocker data for 11 crop or embedding types. The small-grid check covers 78 repair cases, including six exclusions. [Verification output](verification.json) · [DRAT-trim](https://github.com/marijnheule/drat-trim)
