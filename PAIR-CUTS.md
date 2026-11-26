# Two-point repair exclusions and a semidefinite feasibility witness

## Certified repair exclusions

Fix a valid seed $S$, two proposed additions $p,q\notin S$, and a deletion budget $r$. Let $F\subseteq S$ consist of the seed points on the line $pq$. Every repair containing $p,q$ deletes $F$. For each of $p,q$ the pairs of seed points on lines through that point form a matching, since no line contains three seed points. After removing edges incident to $F$, the union of the two matchings is a simple graph whose nontrivial components are paths or even cycles. A repeated edge counts once. For a component with $k$ vertices the minimum size of a vertex cover is $\lfloor k/2\rfloor$. The minimum number of deletions to keep both proposed additions and avoid all collinear triples among those two points and the surviving seed is therefore

$$|F|+\sum_C\lfloor |V(C)|/2\rfloor.$$

A pair with cost greater than $r$ cannot lie in a repair. An axis line with $s<2$ seed points requires at least $2-s$ additions for a full configuration. Thus every surviving addition must be compatible with at least that many surviving candidates on the line, counting itself if it belongs to the line. Applying this test repeatedly keeps every possible full repair, by induction on the pruning rounds. The three instances also forbid retaining both endpoints of every recorded incompatible pair. The remaining SAT encoding is given in the [original repair proof](PROOF.md).

Three additional instances have independently checked DRAT certificates. They use the pruned point sets and require no lazy triple clauses. The seed numbers in the table use `--include-embeddings`.

| Order | Source and seed index | Excluded radius | Minimum seed points omitted |
| --- | --- | --- | --- |
| 75 | Order-74 embedding, seed 1 | 9 | 10 |
| 75 | Order-74 embedding, seed 4 | 9 | 10 |
| 77 | Order-78 crop, seed 1 | 10 | 11 |

The lower bounds apply to every placement equivalent under the eight square symmetries. The exclusions leave configurations outside those radii possible. [Instance data](pair-runs.jsonl) · [Checked hashes](pair-proof-checks.jsonl)

## The first positive-semidefinite lift reaches $2n$

Let $P$ be the point relaxation with variables $0\le x_u\le1$ for the $n^2$ grid points. Put a cap of two on every Euclidean grid line and require exactly two on each row and column. Write $p=2/n$. The Lovász–Schrijver $N_+(P)$ conditions at $x=p\mathbf 1$ ask for a positive semidefinite matrix with first row $(1,x^T)$, diagonal $(1,x^T)$, and point block $Q$ such that both $Q_{u,*}/p$ and $(p\mathbf1^T-Q_{u,*})/(1-p)$ lie in $P$ for every $u$. We give such a matrix at $n=75$, and at every $n\ge13$ coprime to $30$, including $77$. A lifted relaxation at the same hierarchy level has previously been shown to reach $2n$ at prime orders $n\ge13$. [Lovász–Schrijver lift](https://doi.org/10.1137/0801013) · [Earlier prime-order construction](https://rstation.ai/problems/no_three_in_line/papers/8)

On $(\mathbb Z/n\mathbb Z)^2$ use the directions

$$D=\{(1,0),(0,1),(1,1),(1,-1),(1,2),(1,-2),(2,1),(2,-1)\}.$$

Let $K$ be the orthogonal projector onto the orthogonal complement of the span of all toroidal line indicators in these directions. The projector is translation invariant. For $n$ coprime to $30$ put $B=K$. At $n=75$ put $B=(50I+\sum_{s\in\{25,50\}^2}T_s)K$, where $T_s$ is translation by $s$. The shifts occur in opposite pairs and their sum has operator norm at most four. Thus its translate by $50I$ is positive definite, commutes with $K$, and makes $B$ positive semidefinite. In both cases $B$ annihilates every selected toroidal line indicator. Its diagonal is constant, denoted $b_0>0$.

Set $Q=p^2 J+(p-p^2)B/b_0$. The Schur complement of the leading entry of the augmented matrix is $(p-p^2)B/b_0$, hence it is positive semidefinite, and the diagonal of $Q$ is $p$. Each conditional vector sums to two on the selected toroidal lines because these lines contain $n$ points. Therefore the actual rows and columns sum to two, and nonnegative conditional entries give a cap of two on any Euclidean line with primitive direction of maximum coordinate magnitude at most two.

For the remaining lines, their length is at most $L=1+\lfloor(n-1)/3\rfloor$. Denote the smallest and largest off-diagonal entries of $Q$ by $q_{\min},q_{\max}$. Given $0\le q_{\min}\le q_{\max}\le p$, the conditioned inclusion sum on any such line is at most $1+(L-1)q_{\max}/p$ and the conditioned exclusion sum is at most $Lp/(1-p)$. Individual exclusion entries are at most $p/(1-p)$.

To bound the entries, the frequency subgroup of a direction $(a,b)$ is $\{(-bi,ai):i\in\mathbb Z/n\mathbb Z\}$. On its characters the projection $K$ vanishes. The inverse character sum of any intersection of these subgroups is its size on its annihilator and zero elsewhere. Inclusion–exclusion gives the exact values of $n^2 K(w)$ for each displacement $w$. When $n$ is coprime to $30$, the pairwise direction determinants are units. Hence distinct subgroups intersect only at zero and the scaled kernel is $n^2[\,w=0\,]-n m(w)+7$, where $m(w)$ counts the directions containing $w$ and $m(w)\le1$ for $w\ne0$. The scaled diagonal is $(n-1)(n-7)$, and off-diagonal values are between $7-n$ and $7$. In particular $q_{\min}>0$, and

$$\frac{q_{\max}}p\le \frac2n+\left(1-\frac2n\right)\frac7{(n-1)(n-7)}\le\frac3{n-1}$$

for $n\ge13$. This gives the inclusion cap, and $Lp/(1-p)\le2$ follows from $L\le(n+2)/3$. For $n=75$, the shifted kernel has scaled diagonal $251568$ and off-diagonal range $[-6582,948]$. Including the $50I$ term and all four shifts, the exact verifier obtains $1+(L-1)q_{\max}/p=45283/26205$ and $Lp/(1-p)=50/73$. Both are less than two, with $0<q_{\min}\le q_{\max}<p$. [Integer kernel verification](moment_witness.py) · [Exact values](moment-witness.jsonl)

The witness concerns feasibility of the continuous lift. The underlying integer configuration problem at 75 and 77 remains open.

## Integer configurations must overload toroidal lines

Any full Euclidean configuration at order 75 has at least four toroidal lines in the six nonaxial directions of $D$ with more than two points. At least two of these lines lie in the two slope-$\pm1$ families. At order 77 there are at least two overloaded toroidal lines in the six nonaxial directions of $D$. Lines in different directions are counted separately. The continuous witnesses above keep every one of these toroidal line sums at two in both conditionings.

Reduce the coordinates modulo $\ell=3$ at order 75 and modulo $\ell=7$ at order 77. Let $c_z$ count points at a residue cell $z\in\mathbb F_\ell^2$ and put $A=2n/\ell$. For each coarse affine line let its deviation be its number of points minus $A$. Write $\Delta_d(z)$ for the deviation of the line of direction $d$ through $z$. Each axial line has deviation zero because each grid row and column contains two points. The affine lines through $z$ contain every other residue cell once and count $z$ a total of $\ell+1$ times. Hence

$$\sum_{d\text{ nonaxial}}\Delta_d(z)=\ell c_z-A.$$

For a fine toroidal line of direction $(a,b)$, the integer value of $ay-bx$ ranges over an interval of length $(|a|+|b|)(n-1)$. Thus a fine line in the two diagonal families splits into at most two Euclidean lines and its excess over two is at most two. In the four other nonaxial families it splits into at most three and its excess is at most four. The average count per fine line is two. Each coarse line is a union of $n/\ell$ fine lines in any direction in $D$ that reduces to the given coarse direction.

At order 75 there are two nonaxial coarse directions. In each, one diagonal and two other nonaxial directions of $D$ coincide after reduction. The two coarse line indices can vary independently. The identity implies that the three entries in each deviation vector are congruent modulo three, and that the two residues sum to $-50\equiv1$. If both residues are two, each coarse family has a positive deviation since its entries sum to zero and none vanish. Each of its three fine directions has an overloaded line in a positive bin, giving six overall and one in each diagonal direction. Otherwise one residue is one. If its vector has at least two positive entries, each of its fine directions must have at least two overloaded lines in distinct bins. If it has a unique positive entry, both negative entries are at most $-2$. The positive entry is at least four, which requires at least two fine diagonal overloads plus at least one overload in each of the other two fine directions.

At order 77 the eight directions give all eight distinct coarse directions. A fine family with no overload has all its counts equal to two and contributes only zero coarse deviations. If there were at most one overload in total, at most one nonaxial coarse family could have nonzero deviations. The identity implies that a family must have nonzero deviations, since $A=22$ is not divisible by seven. Every one of its deviations would then be congruent to $-22\equiv6$ modulo seven. A positive deviation exists because the family sums to zero, and is at least six. One fine overload gives at most four, a contradiction.
