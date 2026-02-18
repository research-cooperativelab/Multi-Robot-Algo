import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from scipy.optimize import linear_sum_assignment

# No communication 
# The probabilities 
# robots with different perspectives
# Robot i has a different probabilities for each node 

# Euclidean distance
def euclidean_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
#create a function that returns a radnom position of m targets
def random_positions(m, area_scale):
    return {i: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
                       for i in range(m)}

# Dynamic auction simulation with optimal comparison at each iteration.
def run_dynamic_auction_with_optimal(n_nodes, n_robots, area_scale, verbose=False):
    # Generate positions for nodes and assign random values to compute probabilities.
    node_positions = {i: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
                      for i in range(n_nodes)}
    node_values = {i: np.random.uniform(0.1, 1.0) for i in range(n_nodes)}
    total_value = sum(node_values.values())
    node_probabilities = {i: node_values[i] / total_value for i in range(n_nodes)}
    
    # Generate starting positions for robots.
    robot_positions = {r: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
                       for r in range(n_robots)}
    
    available_nodes = set(range(n_nodes))
    robot_paths = {r: [] for r in range(n_robots)}
    # Current positions (will be updated as robots move).
    robot_current_positions = robot_positions.copy()
    
    # To record details per iteration.
    comparison_tables = []      # One table per iteration comparing Auction vs Optimal.
    auction_total_per_iter = [] # Sum of auction distances per iteration.
    optimal_total_per_iter = [] # Sum of optimal (best-case) distances per iteration.
    iteration = 0
    
    # Continue until there are no more available nodes
    # (or if there aren’t enough nodes for all robots, we break).
    while available_nodes and len(available_nodes) >= n_robots:
        if verbose:
            print(f"\n--- Iteration {iteration} ---")
        
        # === Compute the Optimal (Best-Case) Assignment for This Iteration ===
        #  The optimal could be determitistic (e.g., Hungarian algorithm) or probabilistic.
        available_nodes_list = list(available_nodes)
        cost_matrix_opt = np.zeros((n_robots, len(available_nodes_list)))
        for r in range(n_robots):
            for j, node in enumerate(available_nodes_list):
                cost_matrix_opt[r, j] = euclidean_distance(robot_current_positions[r], node_positions[node])
        # Using the Hungarian algorithm for the optimal assignment:
        row_ind, col_ind = linear_sum_assignment(cost_matrix_opt)
        optimal_assignments = {}
        for idx, r in enumerate(row_ind):
            node_opt = available_nodes_list[col_ind[idx]]
            distance_opt = cost_matrix_opt[r, col_ind[idx]]
            optimal_assignments[r] = (node_opt, distance_opt)
            if verbose:
                print(f"Optimal for Robot {r}: Node {node_opt} at distance {distance_opt:.2f}")
        
        # === Dynamic Auction Assignment for This Iteration ===
        # Each robot builds its candidate list (node, distance, probability, bid).
        # different optimals. 
        # Here they have communication
        # Full knowledge with probabilities, full knowsledge without probabilities, partial knowledge. 
        # Tk (FK) <= Tk (FP) <= Pk (FP) <= Pk (FK)
        #  FP: Full Probabilities, FK: Full Knowledge, Pk: Partial Knowledge
        # Travek salesman poblem with n nodes and m robots. -> NP hard problem.
        # Travel salesman can be a lower bound 
            # What if the robot doesn't know the location of the other robots?
            # We do not want it to increase indifinitely.
        # The sandwich theorem:
        # Is it true that the optimal is
        # The optimal is just straight to the target 
        # I have the robot that is the closest to the node. min{d_1, d_2, d_3, d_4}
        # The probability of the node over distance + 1 - probability of the node over the new distance + ... 
        robot_candidates = {}
        for r in range(n_robots):
            pos = robot_current_positions[r]
            candidates = []
            for n in available_nodes:
                d = euclidean_distance(pos, node_positions[n])
                # Bid is defined as probability/distance (avoid division by zero)
                bid = node_probabilities[n] / d if d > 0 else float('inf')
                candidates.append((n, d, node_probabilities[n], bid))
            # Sort candidates by descending bid (best bid first).
            candidates.sort(key=lambda x: x[3], reverse=True)
            robot_candidates[r] = candidates
            if verbose:
                df_candidates = pd.DataFrame(candidates, columns=["Node", "Distance", "Probability", "Bid"])
                print(f"\nRobot {r} at {pos}:")
                print(df_candidates)
        
        # Resolve conflicts: each robot should be assigned a unique node.
        assigned = {}
        candidate_index = {r: 0 for r in range(n_robots)}
        unresolved = set(range(n_robots))
        while unresolved:
            proposals = {}
            for r in list(unresolved):
                candidates = robot_candidates[r]
                idx = candidate_index[r]
                if idx < len(candidates):
                    candidate = candidates[idx]  # (node, distance, probability, bid)
                    proposals.setdefault(candidate[0], []).append((r, candidate))
                else:
                    unresolved.remove(r)
            for node, props in proposals.items():
                if len(props) == 1:
                    r, candidate = props[0]
                    assigned[r] = candidate
                    unresolved.remove(r)
                else:
                    # If more than one robot wants the same node, choose the one with highest bid.
                    best_r, best_candidate = max(props, key=lambda x: x[1][3])
                    assigned[best_r] = best_candidate
                    unresolved.remove(best_r)
                    # For the others, move to their next candidate.
                    for r, candidate in props:
                        if r != best_r:
                            candidate_index[r] += 1
            if not proposals:
                break
        
        # Build the comparison table for this iteration.
        iter_table = []
        auction_total = 0
        optimal_total = 0
        for r in range(n_robots):
            if r in assigned:
                node_auction, distance_auction, prob, bid = assigned[r]
                node_opt, distance_opt = optimal_assignments[r]
                iter_table.append({
                    "Robot": r,
                    "Auction Node": node_auction,
                    "Auction Distance": distance_auction,
                    "Optimal Node": node_opt,
                    "Optimal Distance": distance_opt,
                    "Difference": distance_auction - distance_opt
                })
                auction_total += distance_auction
                optimal_total += distance_opt
                # Update the robot's current position and record its path.
                robot_current_positions[r] = node_positions[node_auction]
                robot_paths[r].append(node_auction)
        comparison_tables.append(iter_table)
        auction_total_per_iter.append(auction_total)
        optimal_total_per_iter.append(optimal_total)
        
        # Remove assigned nodes from available_nodes.
        for record in iter_table:
            available_nodes.discard(record["Auction Node"])
        iteration += 1

    return (node_positions, robot_positions, robot_paths, 
            comparison_tables, auction_total_per_iter, optimal_total_per_iter)

# Run the Simulation with Comparison
n_nodes = 12     # Total number of nodes (should be >= n_robots per iteration)
n_robots = 2
area_scale = 10  # Area size (best-case: nodes are close)

# Run our dynamic auction with optimal comparison (verbose=True to see printed details).
(node_positions, robot_positions, robot_paths, 
 comparison_tables, auction_total, optimal_total) = run_dynamic_auction_with_optimal(n_nodes, n_robots, area_scale, verbose=True)

# Print Comparison Tables for Each Iteration
for i, table in enumerate(comparison_tables):
    df = pd.DataFrame(table)
    print(f"\n=== Iteration {i} Comparison Table ===")
    print(df)

# Compute Overall Totals and Ratios
overall_auction = sum(auction_total)
overall_optimal = sum(optimal_total)
print("\n=== Overall Comparison ===")
print(f"Total Auction Distance: {overall_auction:.2f}")
print(f"Total Optimal Distance: {overall_optimal:.2f}")
print(f"Ratio (Auction/Optimal): {overall_auction/overall_optimal:.2f}")

# Plot the Per-Iteration Total Distances
plt.figure(figsize=(10,6))
plt.plot(range(len(auction_total)), auction_total, marker='o', label="Auction Total Distance")
plt.plot(range(len(optimal_total)), optimal_total, marker='o', label="Optimal (Best-Case) Total Distance")
plt.xlabel("Iteration")
plt.ylabel("Total Distance (sum for all robots)")
plt.title("Per-Iteration Total Travel Distance: Auction vs. Optimal")
plt.legend()
plt.grid(True)
plt.show()

# Plot the Difference (Auction - Optimal) per Iteration
diffs = [a - o for a, o in zip(auction_total, optimal_total)]
plt.figure(figsize=(10,6))
plt.bar(range(len(diffs)), diffs)
plt.xlabel("Iteration")
plt.ylabel("Difference in Total Distance")
plt.title("Difference in Total Distance (Auction - Optimal) per Iteration")
plt.grid(True)
plt.show()

print("Dynamic auction vs. optimal comparison simulation executed successfully.")
