"""Exact rational first-lift witnesses for the full line-capacity relaxation."""

from argparse import ArgumentParser
from collections import Counter
from fractions import Fraction
from itertools import combinations, product
import json
from math import gcd


DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1), (1, 2), (1, -2), (2, 1), (2, -1))
SHIFTS_75 = ((25, 25), (25, 50), (50, 25), (50, 50))


def projector_kernel(n):
    """Return n² times the orthogonal projector kernel via subgroup sums."""
    direction_groups = [frozenset(((-b * i) % n, (a * i) % n) for i in range(n))
                        for a, b in DIRECTIONS]
    weights = Counter()
    for size in range(1, len(direction_groups) + 1):
        for subgroups in combinations(direction_groups, size):
            intersection = frozenset.intersection(*subgroups)
            weights[intersection] += (-1) ** (size + 1)
    terms = [(subgroup, sign * len(subgroup)) for subgroup, sign in weights.items() if sign]
    return {
        (x, y): n * n * (x == y == 0) - sum(
            weight for subgroup, weight in terms
            if all((a * x + b * y) % n == 0 for a, b in subgroup)
        )
        for x, y in product(range(n), repeat=2)
    }


def check(n):
    if n != 75 and (n < 13 or gcd(n, 30) != 1):
        raise ValueError("the witness supports order 75 and orders at least 13 coprime to 30")
    kernel = projector_kernel(n)
    if n == 75:
        # The nontrivial translation operator is bounded in norm by 4, so
        # adding 50 times the identity preserves positive semidefiniteness.
        moment_kernel = {
            (x, y): 50 * value + sum(kernel[(x + a) % n, (y + b) % n] for a, b in SHIFTS_75)
            for (x, y), value in kernel.items()
        }
    else:
        moment_kernel = kernel
    if any(moment_kernel[x, y] != moment_kernel[-x % n, -y % n] for x, y in moment_kernel):
        raise RuntimeError("the moment kernel is not symmetric")
    for a, b in DIRECTIONS:
        lines = [0] * n
        for (x, y), value in moment_kernel.items():
            lines[(a * y - b * x) % n] += value
        if any(lines):
            raise RuntimeError(f"the projector does not annihilate direction {(a, b)}")

    p = Fraction(2, n)
    diagonal = moment_kernel[0, 0]
    if diagonal <= 0:
        raise RuntimeError("the diagonal must be positive")
    off_diagonal = [value for point, value in moment_kernel.items() if point != (0, 0)]
    lower, upper = min(off_diagonal), max(off_diagonal)
    scale = (p - p * p) / diagonal
    qmin, qmax = p * p + scale * lower, p * p + scale * upper
    short = 1 + (n - 1) // 3
    if not (0 <= qmin <= qmax <= p and 1 + (short - 1) * qmax / p <= 2
            and short * p / (1 - p) <= 2 and p / (1 - p) <= 1):
        raise RuntimeError("a conditioned LP bound failed")
    return {"order": n, "kernel_diagonal": diagonal, "kernel_offdiag_min": lower,
            "kernel_offdiag_max": upper, "minimum_pair_moment": str(qmin),
            "maximum_pair_moment": str(qmax),
            "short_line_maximum_length": short,
            "short_line_conditioned_inclusion_bound": str(1 + (short - 1) * qmax / p),
            "short_line_conditioned_exclusion_bound": str(short * p / (1 - p))}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("n", nargs="*", type=int, default=(75, 77))
    args = parser.parse_args()
    for order in args.n:
        print(json.dumps(check(order)))
