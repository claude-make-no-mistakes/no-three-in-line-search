"""Exact grid geometry and record decoding for the planar no-three-in-line problem."""

from collections import defaultdict
from itertools import combinations
from math import gcd

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,."


def point_id(n, point):
    x, y = point
    return x*n + y + 1


def coordinates(n, item):
    return divmod(item-1, n)


def decode(code):
    payload = code.strip()[1:]
    n, remainder = divmod(len(payload), 2)
    if remainder or not 2 <= n <= len(ALPHABET):
        raise ValueError("invalid record length")
    points = [(i//2, ALPHABET.index(c)) for i, c in enumerate(payload)]
    validate(n, points, full=True)
    return n, tuple(points)


def validate(n, points, full=False):
    if len(set(points)) != len(points) or any(not (0 <= x < n and 0 <= y < n) for x, y in points):
        raise ValueError("invalid point set")
    if next(triples(points), None) is not None:
        raise ValueError("collinear triple")
    if full and len(points) != 2*n:
        raise ValueError("record does not attain the row bound")


def triples(points, *, skip_axes=False):
    """Yield each collinear triple once, oriented from its first sorted point."""
    ordered = sorted(points)
    for i, (x, y) in enumerate(ordered):
        rays = defaultdict(list)
        for u, v in ordered[i+1:]:
            dx, dy = u-x, v-y
            if skip_axes and (dx == 0 or dy == 0):
                continue
            d = gcd(dx, dy)
            rays[dx//d, dy//d].append((u, v))
        for ray in rays.values():
            for b, c in combinations(ray, 2):
                yield (x, y), b, c


def blockers(n, seed):
    """Return every pair of seed points blocking each vacant grid cell."""
    occupied = set(seed)
    conflicts = defaultdict(list)
    for a, b in combinations(sorted(seed), 2):
        x, y = a
        dx, dy = b[0]-x, b[1]-y
        d = gcd(dx, dy)
        dx, dy = dx//d, dy//d
        while 0 <= x-dx < n and 0 <= y-dy < n:
            x, y = x-dx, y-dy
        while 0 <= x < n and 0 <= y < n:
            if (x, y) not in occupied:
                conflicts[x, y].append((a, b))
            x, y = x+dx, y+dy
    return conflicts


def dihedral(n, points):
    """Canonical tuple over the eight symmetries of the square."""
    return min(tuple(sorted((n-1-x if rx else x, n-1-y if ry else y)
                            for x, y in ([(b, a) for a, b in points] if swap else points)))
               for swap in (0, 1) for rx in (0, 1) for ry in (0, 1))


def crops(target, records, include_embeddings=False):
    groups = defaultdict(list)
    for index, code in enumerate(records, start=1):
        n, points = decode(code)
        if include_embeddings and n == target-1:
            offsets = range(-1, 1)
        else:
            offsets = range(n-target+1)
        for a in offsets:
            for b in offsets:
                cropped = [(x-a, y-b) for x, y in points if a <= x < a+target and b <= y < b+target]
                groups[dihedral(target, cropped)].append((index, n, a, b))
    return groups
