# UHP Honors Symposium — Speaker Script
**"On the Numerical Analysis of Multi-Robot Search & Rescue"**
Fozhan Babaeiyan Ghamsari · CSULB Honors Program · Spring 2026
**Target time: 10 minutes · 13 slides · ~45 seconds each**

> **How to use:** Read this out loud 2–3 times before the talk. Words in **[brackets]** are stage directions — don't say them. The goal is natural delivery, not memorization.

---

## Slide 1 — Title

**[Smile. Pause 2 seconds. Make eye contact before speaking.]**

Good afternoon. My name is Fozhan, and my honors thesis asks a question that sounds simple but turns out to be surprisingly deep:

*If you have a small team of battery-powered drones and a collapsed building — how do those drones coordinate to find a survivor as fast as possible?*

I'm going to show you what we found, why it matters, and a live simulator you can try right now on your phone.

---

## Slide 2 — Disasters are search problems

**[Let the image sit for a moment.]**

Think about Haiti. Turkey. The moment a building collapses, there's a window — measured in hours — where survivors can still be found.

Drones can cover that rubble far faster than human teams. But there's a catch: without coordination, multiple drones visit the same rooms over and over while the high-probability zones go unchecked.

Look at this slide. Same map. Same three robots. Same target. On the left — no coordination: the drones produce spaghetti tracks and a score of 53. On the right — our coordinated approach: clean ordered paths and a score of 3.

That eighteen-fold difference is what this research is about.

---

## Slide 3 — The question is not *whether*

The question is not *whether* we should use robots for search and rescue. That debate is over.

The question is *how* — specifically, how to coordinate a small fleet when each robot has a limited battery.

Here's the setup: R robots, each with energy budget E — think of it as meters of flight. n candidate sites scattered across an arena. Each site has a prior probability — maybe from a thermal sensor sweep. One site hides the target, drawn at random from those priors.

The robots don't know where the target is. We need to assign them so the robot that *finds* the target travels as little as possible.

---

## Slide 4 — Finder Competitive Ratio

To compare algorithms fairly, we need one number.

We use the **Finder Competitive Ratio** — FCR. It's simple: distance the finding robot actually flew, divided by the distance an all-knowing agent would have flown.

FCR of 1: the finder went straight there. Perfect.
FCR of 3: the finder traveled three times the minimum.
FCR of 53: basically wandering.

Everything above 1 is the cost of uncertainty. Our job is to drive that number down.

---

## Slide 5 — Four models, one ladder

We don't just propose one algorithm and claim it works. We build a hierarchy of four models, each adding one real-world capability.

**M1** — no communication, infinite battery. The baseline. Pure chaos.

**M2** — we add a coordination auction. Robots bid on sites and divide the work. Still infinite battery.

**M3** — we add the real constraint: finite energy. Each robot does one round trip per search iteration.

**M4-star** — our contribution. We add two things: robots chain multiple sites into a single sortie, and a new smarter bid formula.

Each step up the ladder is a clean experiment in what coordination is actually worth.

---

## Slide 6 — Two algorithms. One seed.

**[Pause. Let the numbers land.]**

Same map. Same seed. Same three robots. Same target.

M1 on the left: FCR 53.65. Spaghetti.
M4-star on the right: FCR 3.02. Tight, ordered tours.

An **18-fold reduction** in finder travel — with no new hardware, no bigger batteries, no extra robots.

Just smarter coordination.

---

## Slide 7 — Auction, then chain

So how does M4-star actually work? Three phases, every iteration.

**Phase 1 — the auction.** Every robot bids on every site it can reach. Highest bid wins that site. Remove that pair, repeat until every robot has an assignment.

**Phase 2 — chain extension.** From its assigned site, each robot asks: can I visit one more site and still make it home? If yes, go. Repeat until the energy budget runs out. One trip visits roughly five sites on average.

**Phase 3 — Bayesian update.** Robots return to base, share results, zero out sites they visited, renormalize the probabilities, and re-auction.

---

## Slide 8 — Why p/d²?

**[This is your key insight. Slow down.]**

The classical bid formula — established in 1975 — is *p over d*. Probability divided by distance.

Under finite energy, that rule breaks. Here's the intuition:

If your assigned site is far away, the *round trip* to that site burns most of your battery — leaving almost nothing for chaining additional sites. Distant anchors don't just cost more to reach — they *shut down* your whole sortie.

We call this **cost foreclosure**. The correct response is to penalize distance *twice as hard*. That gives us **p over d²**.

And the data prove it: p/d² beats p/d under every energy-constrained configuration we tested.

---

## Slide 9 — Headline results

**[Reference the table briefly, then the three big callout numbers.]**

Five thousand paired Monte Carlo trials. 30 sites, 3 robots, energy budget of 14.

Three numbers tell the whole story:

**6.6 times** — coordination gain. Same fleet, same hardware, just communication added. M1 random to M2 coordinated.

**90%** — energy penalty recovered. M3 with smart trip chaining closes 90% of the gap to the infinite-battery ideal. No hardware changes. Pure scheduling.

**3.11** — M4-star sits within 10% of the theoretical floor set by a robot with unlimited battery.

---

## Slide 10 — SearchFCR Web Simulator

**[This is the live demo moment. Pull up the site or show the QR code.]**

Everything I just showed you is interactive at **searchfcr.fozhan.dev**.

You can run all five models on the same seed, watch the auction assign robots in real time, and see FCR and belief entropy collapse round by round.

**Scan the QR code** — try it on your phone right now. Pick M1 and M4-star, run them side by side, and watch the 18-fold difference play out live.

This was built as part of the thesis so the results are fully reproducible — every figure in the paper can be generated with one command.

---

## Slide 11 — PyBullet 3D Demo

**[Let the visual speak first.]**

We also ship a full 3D physics demonstration built in PyBullet.

Left side: M1. Watch the robots wander. Paths overlap. The finder travels 18 times further than necessary.

Right side: M4-star. Clean assignments from the auction. Robots chain their sites. The finder reaches the target efficiently.

Same map, same three robots, same target — radically different paths. This is the difference coordination makes, visualized in physics.

---

## Slide 12 — A benchmark you can fork

The entire research is open-source as **SearchFCR**.

One command — `python reproduce_thesis.py` — regenerates every figure in the thesis. Seven models, five bid functions, four cost metrics, eight experiments, five thousand trials each, thirty-seven unit tests.

If you want to test a new bid formula or a new terrain model, the API is designed for exactly that.

**github.com/foojanbabaeeian/Multi-Robot-Algo**

---

## Slide 13 — Four takeaways

**[Read these slowly. One breath between each.]**

**One:** The dominant lever is communication, not fleet size. If your robots aren't coordinating, buying more robots barely helps.

**Two:** Multi-node trip planning recovers 90% of the energy penalty — in software, with no hardware changes.

**Three:** p over d² is the right bid under energy constraints. The advantage is largest exactly when you need it most: tight batteries, noisy maps.

**Four:** All of this is reproducible, open-source, and live at searchfcr.fozhan.dev.

**[Pause. Smile. Look up.]**

Thank you. I'm happy to take questions.

---

## Q&A Cheat Sheet

**"Why not just use AI / machine learning?"**
> ML approaches are hard to bound analytically. Our contribution is a closed-form framework with provable guarantees — something a practitioner can reason about on a whiteboard without a trained model.

**"Does this scale to more robots or larger areas?"**
> Yes. FCR improves as roughly 1/√R — adding robots always helps. The auction is O(R·n) per round so it scales well. We tested up to 6 robots and 80 sites.

**"What if the prior map is totally wrong?"**
> We tested this — corrupted priors with Gaussian noise. The p/d² advantage actually *grows* as priors get noisier. That's the operating condition of any real deployed system, so the result goes in the right direction.

**"Is p/d² globally optimal?"**
> We prove it's the correct functional form given cost foreclosure, and the experiments validate it across every configuration. Proving a tight lower bound on achievable FCR under finite energy is an open problem — good thesis extension.

**"How do I run it?"**
> `pip install searchfcr` then `python reproduce_thesis.py` — or just open searchfcr.fozhan.dev and run it in the browser.

---

*Good luck! You've got this.*
