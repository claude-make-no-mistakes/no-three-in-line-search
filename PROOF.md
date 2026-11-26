# Excluding repairs near catalogued grid configurations

Let $S$ be a set with no three collinear points in the $n\times n$ grid. A repair of deletion radius $r$ is a new set $T$ with no collinear triple and $|S\setminus T|\le r$. The target here is $|T|=2n$. Every row and column of a target then contains exactly two selected points.

## Blocking pairs

For a vacant cell $q$, let $B(q)$ be the two-element subsets of $S$ collinear with $q$. Each pair lies on a distinct line through $q$ and the pairs are disjoint. If two pairs shared a point, the common line would contain three points of $S$. Every target containing $q$ must delete at least one seed point from every pair in $B(q)$. Thus $|B(q)|\le r$ is necessary.

For simultaneous additions $p,q$, set $V(p)=\bigcup B(p)$ and $V(q)=\bigcup B(q)$. The sum of the two pair counts is the number of required hits, counting a shared pair once for each addition. Each removed vertex can supply at most one hit for each addition. Therefore at least

$$|B(p)|+|B(q)|-|V(p)\cap V(q)|$$

removals are needed. Any new point must have enough compatible peers on every deficient axis line. A row or column with $s<2$ seed points must contain at least $2-s$ new points, even if a repair also removes some of its seed points. Counting the new point itself when it lies on that line gives a necessary local count. Repeating the removal of additions that fail the count preserves every feasible repair by induction.

## SAT instances and what they certify

Give each allowed grid point a Boolean selection variable. Use sequential counters for two selected points per row and column and for at most $r$ false seed variables. For each allowed $q$ and each blocking pair $\{a,b\}\in B(q)$, forbid selecting $q,a,b$ together. Axis-aligned blocking pairs are already handled by the row and column constraints.

This initial instance only imposes necessary conditions, so an UNSAT certificate already excludes every repair of the specified radius. The solver can also add any missing collinear triples found in a satisfying model, preserving every actual repair. The recorded UNSAT cases in this repository closed using the initial instance. They do not depend on handling a model with multiple new collinear points.

The optional target of at least $2n-1$ points uses at most two in each row and column, at least one in each, and at most one deficiency flag on each axis. An unflagged line must have at least two. This is equivalent to the cardinality requirement because the selected point count is the sum over either axis. The alternative global cardinality branch handles smaller targets.

## Seed provenance and scope

The five records are the two order-74, two order-76, and single order-78 lines from Flammenkamp's `all_known_solutions` snapshot with SHA-256 `2aa1d0565e6792177c4dbb7a145257739d2008f7b9c126be7ea6be076f16eed5`. The decoder uses the catalogue's documented rowwise alphabet. The verifier checks each record with integer determinants and checks every blocking-pair list against an independent direction-grouping implementation. [Catalogue](https://wwwhomes.uni-bielefeld.de/achim/no3in/download/) · [Encoding specification](https://wwwhomes.uni-bielefeld.de/achim/no3in/readme.html#config)

The default search crops each larger source window, and identifies equivalent crops under the eight symmetries of the target square. For order 75 this gives two crops with 148 points and four with 144. For order 77 it gives one with 152 points. A certified radius exclusion is a lower bound on the number of seed points any full solution must omit. It leaves other configurations on the same board possible.
