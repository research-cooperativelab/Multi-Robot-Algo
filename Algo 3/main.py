import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment
import random
import statistics as stats

def euclidean_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def run_finite_energy_auction(n_nodes, n_robots, area_scale, E, verbose=False):
    # Base/home at the origin
    home = (0.0, 0.0)

    # Generate node positions and probabilities
    node_positions = {i: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
                      for i in range(n_nodes)}
    node_values = {i: np.random.uniform(0.1, 1.0) for i in range(n_nodes)}
    total_value = sum(node_values.values())
    node_probabilities = {i: node_values[i] / total_value for i in range(n_nodes)}

    available_nodes = set(range(n_nodes))
    robot_paths = {r: [] for r in range(n_robots)}
    auction_totals = []
    # optimal_totals = []

    # optimal assignment (for comparison)
    target = random.choices(list(node_values.keys()), weights=node_values.values(), k=1)[0]
    optimal_distance = euclidean_distance(home, node_positions[target])

    # Create the complete instance 
    iteration = 0
    while available_nodes and len(available_nodes) >= n_robots:
        if verbose:
            print(f"\n--- Iteration {iteration} ---")

        # 1) Recharge at base
        remaining_energy = {r: E for r in range(n_robots)}

        # 2) Build candidate lists with energy-return filter
        candidates = {}
        for r in range(n_robots):
            C = []
            for n in available_nodes:
                d = euclidean_distance(home, node_positions[n])
                # Only allow nodes robot can visit and return
                if 2 * d <= remaining_energy[r]:
                    bid = node_probabilities[n] / d
                    C.append((n, d, bid))
            # Sort by descending bid
            C.sort(key=lambda x: x[2], reverse=True)
            candidates[r] = C
            if verbose:
                print(f"Robot {r} candidates:", C)

        # 3) Optimal assignment (minimize round-trip cost)
        # avail_list = list(available_nodes)
        # cost_opt = np.zeros((n_robots, len(avail_list)))
        # for r in range(n_robots):
        #     for j, n in enumerate(avail_list):
        #         d = euclidean_distance(home, node_positions[n])
        #         cost_opt[r, j] = 2 * d
        # row_ind, col_ind = linear_sum_assignment(cost_opt)
        # optimal_assignments = {r: (avail_list[col_ind[k]], cost_opt[r, col_ind[k]])
        #                         for k, r in enumerate(row_ind)}
        # opt_total = sum(dist for _, dist in optimal_assignments.values())

        # 4) Auction assignment
        assigned = {}
        idx = {r: 0 for r in range(n_robots)}
        unresolved = set(range(n_robots))
        while unresolved:
            proposals = {}
            for r in list(unresolved):
                if idx[r] < len(candidates[r]):
                    n, d, bid = candidates[r][idx[r]]
                    proposals.setdefault(n, []).append((r, bid, d))
            if not proposals:
                break
            for n, runners in proposals.items():
                # Highest bid wins
                r_best, _, d_best = max(runners, key=lambda x: x[1])
                assigned[r_best] = (n, d_best)
                unresolved.remove(r_best)
                # Others move to next candidate
                for r, _, _ in runners:
                    if r != r_best:
                        idx[r] += 1

        auc_total = sum(d for _, d in assigned.values()) * 2  # out-and-back
        auction_totals.append(auc_total)
    
        # optimal_totals.append(opt_total)

        # 5) Update paths and available nodes
        for r, (n, _) in assigned.items():
            robot_paths[r].append(n)
            available_nodes.remove(n)
            if n == target:
                distance_total = sum(euclidean_distance(home, node_positions[i]) for i in robot_paths[r])*2 - euclidean_distance(home, node_positions[n])  
                print(iteration)

                competative_ratio = distance_total / optimal_distance
                # Display per-iteration results
                # for i, (a, o) in enumerate(zip(auction_dists, competative_ratio)):

                print(f"Iteration {iteration}: Auction total distance = {distance_total:.2f}, Optimal total distance = {optimal_distance:.2f}, Ratio = {competative_ratio:.2f}")

                return node_positions, robot_paths, auction_totals , distance_total, optimal_distance , iteration
            

        iteration += 1
        print(f"{target} is this, Error: Target node not found.")


# Parameters
n_nodes = 12
n_robots = 2
area_scale = 10
E = 30  # battery capacity (distance units)
list_distance_total = []
list_optimal_distance = []
list_compaptive_ratio = []
list_number_iterations = []
number_iterations = 5
for i in range(number_iterations):
    # Run the finite-energy auction simulation
    node_positions, robot_paths, auction_dists, distance_total, optimal_distance , iteration = run_finite_energy_auction(
        n_nodes, n_robots, area_scale, E, verbose=False 
    )
    # competative_ratio = distance_total / optimal_distance
    competative_ratio = distance_total / optimal_distance

    # Store results
    list_distance_total.append(distance_total)
    list_optimal_distance.append(optimal_distance)
    list_compaptive_ratio.append(competative_ratio)
    list_number_iterations.append(iteration)



    # Display per-iteration results

print(f"Average Iterations: {sum(list_number_iterations)/len(list_number_iterations):.2f} , Iteration: Auction total distance = {sum(list_distance_total)/len(list_distance_total):.2f}, Optimal total distance = {sum(list_optimal_distance)/len(list_optimal_distance):.2f}, Ratio = {sum(list_compaptive_ratio)/len(list_compaptive_ratio):.2f}")

print(f"Max Iterations: {max(list_number_iterations):.2f} , Auction Max total distance = {max(list_distance_total):.2f}, Max Optimal total distance = {max(list_optimal_distance):.2f}, Max Ratio = {max(list_compaptive_ratio):.2f}")

# Plot the distances per iteration
plt.figure()
plt.plot(auction_dists, marker='o', label='Auction')
plt.plot(competative_ratio, marker='o', label='Optimal')
plt.xlabel('Iteration')
plt.ylabel('Total Distance')
plt.title('Finite‐Energy Auction vs. Optimal (per iteration)')
plt.legend()
plt.grid(True)
plt.show()
