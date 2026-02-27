import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment
import random
import statistics as stats

def euclidean_distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))

def run_finite_energy_auction(n_nodes, n_robots, area_scale, E, bases):
    """
    Runs one trial of the finite-energy auction until the target is found.
    - n_nodes: total nodes
    - n_robots: number of robots
    - area_scale: coordinate scale for node/base placement
    - E: battery capacity (max round-trip distance)
    - bases: list of (x,y) home positions for each robot
    Returns: (total_dist, optimal_dist, iterations, comp_ratio)
    """
    # 1) Generate random nodes & probabilities
    node_positions = {
        i: (random.uniform(0, area_scale), random.uniform(0, area_scale))
        for i in range(n_nodes)
    }
    raw = np.random.uniform(0.1, 1.0, size=n_nodes)
    p = {i: raw[i] / raw.sum() for i in range(n_nodes)}
    
    # 2) Precompute distances from each base
    d = {
        r: {i: euclidean_distance(bases[r], node_positions[i]) for i in range(n_nodes)}
        for r in range(n_robots)
    }
    
    # 3) Choose target by probability
    target = random.choices(range(n_nodes), weights=list(p.values()), k=1)[0]
    
    # 4) Simulate rounds
    available = set(range(n_nodes))
    total_dist = 0.0
    iterations = 0
    
    while True:
        iterations += 1
        
        # a) Build bids per robot
        bids = {}
        for r in range(n_robots):
            bids[r] = sorted(
                [(i, p[i] / d[r][i]) for i in available if 2 * d[r][i] <= E],
                key=lambda x: x[1], reverse=True
            )
        
        # b) Auction: assign one node per robot
        assigned = {}
        idx = {r: 0 for r in range(n_robots)}
        free = set(range(n_robots))
        while free:
            proposals = {}
            for r in list(free):
                if idx[r] < len(bids[r]):
                    i, bv = bids[r][idx[r]]
                    proposals.setdefault(i, []).append((r, bv))
            if not proposals:
                break
            for i, offers in proposals.items():
                winner = max(offers, key=lambda x: x[1])[0]
                assigned[winner] = i
                free.remove(winner)
                for r, _ in offers:
                    if r != winner:
                        idx[r] += 1
        
        # c) All assigned robots travel
        #    If robot reaches target, it travels one-way and we stop
        for r, i in assigned.items():
            if i == target:
                # robot r finds the target
                total_dist += d[r][i]
                optimal = min(d[r][i] for r in range(n_robots))  # best-case direct
                return total_dist, optimal, iterations, total_dist / optimal
            else:
                total_dist += 2 * d[r][i]
                available.discard(i)

def simulate_trials(n_nodes, n_robots, area_scale, E, trials=100):
    # Generate fixed bases once
    bases = [
        (random.uniform(0, area_scale), random.uniform(0, area_scale)) 
        for _ in range(n_robots)
    ]
    
    dist_totals = []
    opt_dists = []
    ratios = []
    iters = []
    
    for _ in range(trials):
        td, od, it, cr = run_finite_energy_auction(n_nodes, n_robots, area_scale, E, bases)
        dist_totals.append(td)
        opt_dists.append(od)
        ratios.append(cr)
        iters.append(it)
    
    return dist_totals, opt_dists, ratios, iters

# === Parameters ===
n_nodes = 20
n_robots = 3
area_scale = 10
E = 30
trials = 200

# Run simulation
dist_totals, opt_dists, ratios, iters = simulate_trials(n_nodes, n_robots, area_scale, E, trials)

# === Summaries ===
print("After", trials, "trials:")
print("Avg total distance:", stats.mean(dist_totals))
print("Avg optimal direct:", stats.mean(opt_dists))
print("Avg iterations:", stats.mean(iters))
print("Avg competitive ratio:", stats.mean(ratios))

# === Plots ===
plt.figure(figsize=(7,4))
plt.hist(ratios, bins=20, edgecolor='black')
plt.xlabel('Competitive Ratio (Auction / Optimal)')
plt.ylabel('Frequency')
plt.title('Distribution of Competitive Ratios')
plt.grid(True)
plt.show()

plt.figure(figsize=(7,4))
plt.scatter(iters, ratios, alpha=0.6)
plt.xlabel('Iterations until Target Found')
plt.ylabel('Competitive Ratio')
plt.title('Ratio vs Iterations')
plt.grid(True)
plt.show()
