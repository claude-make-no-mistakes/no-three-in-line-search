"""Replay DRAT proofs with an independent checker and print file hashes."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checker", type=Path)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for cnf in args.files:
        proof = cnf.with_suffix(".drat")
        if not proof.is_file():
            raise ValueError(f"missing proof for {cnf}")
        result = subprocess.run([str(args.checker.resolve()), str(cnf), str(proof)],
                                capture_output=True, text=True)
        if result.returncode or "s VERIFIED" not in result.stdout:
            raise RuntimeError(f"certificate failed: {cnf}\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
        print(json.dumps({"case": cnf.stem, "checked": True, "cnf_sha256": sha256(cnf),
                          "drat_sha256": sha256(proof)}), flush=True)


if __name__ == "__main__":
    main()
