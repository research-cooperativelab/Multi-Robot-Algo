# Speaker Script — SearchFCR Conference Talk
**"On the Numerical Analysis of Multi-Robot Search and Rescue Algorithms in Unknown Environments"**
Fozhan Babaeiyan Ghamsari · Advisor: Prof. Oscar Morales-Ponce · CSULB · Spring 2026

---
> **How to use this script:**
> Print this out. Each section starts with what's on screen, then your words in plain text.
> Aim for ~2 minutes per slide → ~40 minutes total for 20 slides. Adjust to your time limit.
> Words in **[brackets]** are stage directions, not spoken.

---

## Slide 01 — Cover

**[Wait for audience to settle. Breathe. Smile. Start strong.]**

Good afternoon. The work I'm presenting today is titled *On the Numerical Analysis of Multi-Robot Search and Rescue Algorithms in Unknown Environments.* It's my Honors Thesis from Cal State Long Beach, done with Professor Oscar Morales-Ponce.

The short version: we asked a simple question — if you have a small fleet of battery-powered drones and a collapsed building, how should those drones coordinate to find a survivor as fast as possible?

The answer turns out to be interesting. Let me show you.

---

## Slide 02 — Disasters are search problems

**[Let the image land for a second before speaking.]**

Think about what happens after a building collapses. You have rubble, you have potential survivors, and you have a window of time. Drones can clear that space much faster than human search teams — but only if they coordinate.

Without coordination, what you get is this: multiple robots revisiting the same rooms while the rooms that actually matter — the high-probability zones — go unchecked.

This slide shows the same scenario, the same three robots, the same map. Uncoordinated: a Finder Competitive Ratio of 53. Coordinated: 3. That difference is the entire research question.

---

## Slide 03 — The question is not *whether*

The question is not whether we should use autonomous robots for search and rescue. That debate is over. The question is *how* to coordinate them when you have real constraints.

Here's the formal setup. You have R robots — in our experiments, three. Each robot has a finite energy budget E — think of it as battery life measured in meters of flight. There are n candidate sites spread across an arena — we use 30. Each site carries a prior probability, maybe from a sensor sweep or domain knowledge. Somewhere among those 30 sites is a single target, hidden, drawn at random according to those priors.

The robots don't know where the target is. Our job is to find an assignment and an order of visits that minimizes how far the robot that actually finds the target has to fly.

---

## Slide 04 — Finder Competitive Ratio

To compare algorithms fairly across problem instances of different sizes and difficulties, we need a normalized metric. We use the **Finder Competitive Ratio**.

FCR equals the distance the finding robot actually traveled — call it D-f — divided by D-opt, which is the distance an omniscient agent with perfect knowledge would have flown from the nearest base.

FCR of one means the finder went straight there. No wasted motion.
FCR of three means the finder traveled three times further than necessary.
FCR of eighteen means the robots were basically wandering.

Everything above one is overhead from uncertainty and coordination constraints. Our goal is to drive that number down.

---

## Slide 05 — Four models, one ladder

We don't propose a single algorithm and claim it's optimal. Instead, we define a hierarchy of four models, each adding exactly one operational capability.

**M1** — no communication, infinite battery. Pure random walk. This is the baseline.

**M2** — we add a sequential single-item auction. Robots bid on sites, coordinate assignments. Still infinite battery.

**M3** — we keep the auction and add the realistic constraint: finite energy. Each robot does one round trip per iteration.

**M4-star** — our contribution. We add two things: a greedy chain that strings multiple sites into one sortie, and a new bid function: p over d-squared.

The ladder is deliberate. It lets us isolate the value of communication, the cost of finite battery, and the recovery from smarter scheduling — each as a clean numerical experiment.

---

## Slide 06 — Two algorithms. One seed.

**[Pause here. Let the numbers speak.]**

Same map. Same seed. Same three robots. Same target.

M1 on the left: spaghetti tracks, FCR of 53.65.
M4-star on the right: tight, ordered tours, FCR of 3.02.

An eighteen-fold reduction in finder travel from coordination alone — no new hardware, no bigger batteries, no extra robots. Just smarter scheduling.

---

## Slide 07 — Auction, then chain

So how does M4-star actually run? Three phases.

**Phase one — the SSI auction.** Every robot computes a bid for every energy-feasible site. The bid is p over d-squared: probability of finding the target at that site, divided by distance squared. Highest bid wins. That robot-site pair is removed from the pool, and the process repeats until every robot has an anchor site assigned.

**Phase two — greedy chain extension.** From its anchor, each robot asks: can I visit one more site and still make it back to base? If yes, append it. Repeat until the budget runs out. A single sortie visits roughly five sites on average.

**Phase three — Bayesian update.** Robots return to base, broadcast their results, zero out the priors for visited sites, renormalize, and re-auction. Start over.

---

## Slide 08 — Why p/d²?

**[This is your key theoretical contribution. Slow down here.]**

The classical bid function — established by Stone in 1975 — is p over d. That's the single-searcher optimum: probability divided by distance.

Under finite energy, that rule breaks. Here's why.

Anchoring at distance d burns 2d of your energy budget just on the base legs — out and back. That leaves only E minus 2d for chain extensions. The number of additional sites you can visit decreases linearly with how far your anchor is. Distant anchors aren't just expensive to reach — they *foreclose* on everything that comes after.

We call this cost foreclosure. The effective marginal cost of distance is superlinear in d. The correct response is to penalize distance quadratically. That gives us p over d-squared.

And the data confirm it: p/d-squared beats p/d under every energy-constrained configuration we tested.

---

## Slide 09 — Headline results

**[Reference the table on the left, then the three big numbers on the right.]**

Five thousand paired Monte Carlo trials. Default configuration: 30 sites, 3 robots, energy budget 14.

M1 random: 18.74.
The Hungarian baselines: 6.88 to 7.38.
M3 single-sortie auction: 6.32.
M4 chain with classical bid: 3.16.
**M4-star, our contribution: 3.11.**
The unconstrained ceiling — infinite battery, M2: 2.83.

Three headline numbers from this table:

**6.6 times** — that's the coordination gain. Identical fleet. Switching only the communication regime.

**90%** — that's how much of the energy penalty M4 recovers through smart trip planning, with no hardware changes.

**3.11** — that's M4-star, sitting within 10% of the theoretical floor set by infinite-battery M2.

---

## Slide 10 — Coordination dominates fleet size

**[Let the numbers animate in. Then speak.]**

From 18.74 to 2.83. A factor of 6.6. Same fleet size, same arena, same energy budget.

The practical implication: if you're trying to improve your search system, the first question to ask is not "how many robots do I have?" It's "are my robots talking to each other?"

A well-coordinated team of three substantially outperforms a larger uncoordinated fleet.

---

## Slide 11 — SSI beats Hungarian

This result surprised us.

Distributed sequential auctions outperform centralized Hungarian assignment — even when Hungarian gets the same prior probability information.

In fact, giving Hungarian probability weights makes it *worse*. FCR goes from 6.88 to 7.38. The reason: Hungarian solves the full assignment problem in one shot, which tends to cluster robots in the same high-probability region. Sequential auctions avoid this because each successful bid removes its winner from competition. The remaining robots re-bid on a smaller, cleaner problem.

The lever isn't the bid function. It's the iterative re-weighting baked into SSI.

---

## Slide 12 — Smart trips beat bigger batteries

**[Point to the four columns, left to right.]**

M3, single sortie: 6.32. One site per round trip.
M4, greedy chain with classical bid: 3.16. Roughly 5.3 sites per sortie.
M4-star, greedy chain with p/d-squared: 3.11.
M2, infinite battery: 2.83. That's the floor.

M4 closes **90%** of the gap to the battery-free ideal. No larger batteries. No additional robots. No new hardware. Just a different scheduling rule.

The lever to pull is software, not procurement.

---

## Slide 13 — The lead grows when budgets tighten

The energy sweep tells us *when* p/d-squared matters most.

At E equals 8 — a tight budget — the gap between M4-star and M4 reaches 12%. Cost foreclosure pressure is highest here.

At E equals 20 and above, the curves converge. When energy is plentiful, foreclosure stops biting, and the two bid functions become equivalent.

Real search-and-rescue drones operate at the left edge of this chart — small batteries, long flights. That is exactly where our contribution provides the largest benefit.

---

## Slide 14 — Robust to bad priors

A natural objection: what if the prior probability map is wrong? In real SAR, your sensor data is always noisy.

We perturbed the priors with Gaussian noise at three levels and re-ran.

At sigma zero — perfect priors — M4-star's margin over M4 is 0.13.
At sigma 0.5 — moderately corrupted — the margin grows to 0.49.

The quadratic distance penalty matters *more*, not less, when the map is unreliable. That's the operating condition of any deployed search system. This is a robustness result in the right direction.

---

## Slide 15 — Counterintuitive: 2-opt hurts

Here's the most surprising result in the thesis.

We applied 2-opt tour polishing to M4-star outputs. 2-opt shortens the geometric tour — it is doing its job. But it worsened the Finder Competitive Ratio by 6.58%.

Why? Geometric optimization reorders sites by travel efficiency. It has no concept of probability-weighted reward. It trades high-probability sites late in the tour for shorter total distance. The target gets visited later. FCR goes up.

The lesson: the standard *build tour, then polish* pipeline is actively harmful for finder-centric metrics under Bayesian priors. This is a result practitioners need to know.

---

## Slide 16 — Wins under every cost model

One might ask: does this only work in flat Euclidean space?

We swapped the distance metric — Euclidean, Manhattan, heterogeneous robot speeds, and an obstacle-penalty shortest-path metric — and re-ran.

M4-star achieves the lower mean FCR in all four cases. The cost-foreclosure argument depends only on the existence of a finite energy budget and a well-defined round-trip metric. It doesn't require Euclidean geometry.

---

## Slide 17 — Every bound holds

We also derived closed-form upper bounds on the expected FCR for each model.

**[Point to each row.]**

M1: empirical 18.74, bound 34.09. Holds. ✓
M2: empirical 2.83, bound 3.05. Holds — and it's tight at 93%. ✓
M3: empirical 6.32, bound 17.34. Holds. ✓
M4: empirical 3.16, bound 4.78. Holds — and we tightened this bound by a factor of 2.9 over a prior derivation. ✓

Every single empirical result lies strictly below its closed-form upper bound. Theory and experiment agree.

---

## Slide 18 — Runs on real drones, in sim

**[Let the GIF run for a few seconds before speaking.]**

We ship a full PyBullet 3D physics demonstration with the repository. Same algorithms, same parameters, visualized in real-time.

Left: M1. Watch the robots wander. Paths overlap. The finder travels 18× further than necessary.

Right: M4-star. The auction resolves clean assignments. Robots chain their sites. The finder reaches the target efficiently.

Same map, same robots, same target. Radically different paths.

---

## Slide 19 — A benchmark you can fork

Everything is released as the **SearchFCR** open-source benchmark.

One command — `python reproduce_thesis.py` — regenerates every figure in the thesis in about three minutes.

Seven models, five bid functions, four cost metrics, eight reproducible experiment scripts, five thousand paired trials per configuration, thirty-seven unit tests.

If you want to test a new bid function or a new cost model, the API is designed for exactly that.

---

## Slide 20 — Four takeaways

**[Read these slowly. Pause between each one.]**

**One:** The dominant determinant of search efficiency is the communication regime, not the fleet size. If your robots aren't talking, more robots won't help much.

**Two:** Sequential single-item auctions outperform centralized Hungarian assignment — even information-augmented Hungarian. The mechanism matters.

**Three:** Multi-node sortie planning recovers 90% of the energy penalty without any hardware changes. The lever is scheduling.

**Four:** p over d-squared is the right bid function under energy constraints. The advantage is largest exactly when you need it most — tight budgets, noisy priors.

**[Pause. Look up. Smile.]**

Thank you. The repository is at github.com/research-cooperativelab/Multi-Robot-Algo. I'm happy to take questions.

---

## Q&A Cheat Sheet

**Q: Why not use reinforcement learning?**
> RL approaches are promising but require extensive training and are hard to bound analytically. Our contribution is a closed-form analysis with provable bounds that practitioners can reason about without a trained model.

**Q: Does this scale to larger fleets or more sites?**
> Yes. We show FCR scales as 1/√R — adding robots always helps. The SSI auction is O(R·n) per round, so it scales well. We tested up to R=10 and n=100 in the sweep experiments.

**Q: How sensitive is the result to the energy parameter E?**
> The energy sweep on slide 13 answers this directly. The p/d² advantage is largest at tight budgets (E≈8) and disappears at E≈20+. For real SAR drones with typical 10–15 minute flight times, you're firmly in the regime where our bid function helps.

**Q: What about communication failures or partial observability?**
> Great open question. The current model assumes perfect communication at base. Robustness to communication dropout is a natural extension. The Bayesian update structure means that even with delayed information, robots can still re-auction with stale beliefs — it degrades gracefully.

**Q: Is the p/d² function optimal?**
> We don't claim global optimality — we claim it's the right functional form given the cost-foreclosure argument, and the experiments validate it. Proving a tight lower bound on achievable FCR under finite energy is an interesting open problem.

**Q: How does this compare to prior work?**
> The FCR framework is new. Prior work on multi-robot search (Stone 1975, Bourgault 2003, Hollinger 2009) optimizes total tour length or detection probability, not the finder-specific metric. Our analysis is the first to integrate energy constraints, auction mechanisms, and prior-weighted search under a unified competitive-ratio framework.

---

*End of script. Good luck!*
