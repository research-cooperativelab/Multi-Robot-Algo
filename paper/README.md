# Conference paper (IEEE format)

This directory contains the IEEE conference-format version of the paper.

- `paper.tex` — main source
- `ref.bib`   — bibliography
- figures are read from `../figures/`

## Changes relative to the original draft

1. **M2 reframed as a "strong baseline" rather than "ideal".** The original
   abstract and intro described M2 as "the best achievable performance,"
   but in the energy sweep M4* overtakes M2 — a contradiction with
   that framing. M2 is a greedy node-to-node auction, which is not an
   algorithmic lower bound. The language now calls it an
   "unconstrained-energy auction baseline" and explicitly notes the
   crossover in Section V.
2. **Hungarian ablation (H<sub>p/d</sub>).** The original Finding 2
   compared M3 (p/d bids, distributed) to Hungarian (distance-only,
   centralized) and concluded "probability-aware distributed auctions
   outperform centralized distance-optimal assignment." That sentence
   conflates two effects. Added a Hungarian variant with p/d-weighted
   costs to isolate the bid-function effect from the mechanism effect.
3. **Lemma 1 proof fixed.** The original proof said the bound holds with
   equality for uniform priors and called it "conservative for non-uniform
   priors", but did not justify why. Rewritten in terms of the auction's
   probability-ordered rank distribution, with a clean argument that
   uniform priors are the worst case.
4. **Theorem 4 off-by-one in S.** The original definition
   `S = max(1, floor((E - 2 d_avg)/d_hop))` counts only chain-extension
   hops, not the anchor site itself. Corrected to
   `S = max(1, 1 + floor((E - 2 d_avg)/d_hop))` with the corresponding
   change to the K_4 formula and the bounds table.
5. **Finding 4 numerical consistency note.** Added a sentence pointing
   out that the `1/d` bid (FCR ≈ 6.79) and H<sub>d</sub> (FCR ≈ 6.80)
   agree as a cross-check between the two implementations.
6. **Cost-foreclosure justification** for the p/d² bid expanded from
   the original hand-wave to an explicit argument about how far-anchor
   sites shrink the remaining chain reach.
