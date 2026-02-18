import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from scipy.optimize import linear_sum_assignment

# unit test library 



#create a function that returns a radnom position of m targets
def random_positions(m, area_scale):
    return {i: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
                       for i in range(m)}



# Helper function: Euclidean distance.
def euclidean_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# def resolve_conflict(n_robots, robot_candidates):
#      # Resolve conflicts: assign each robot a unique node.
#         assigned = {}
#         candidate_index = {r: 0 for r in range(n_robots)}
#         unresolved = set(range(n_robots))
#         while unresolved:
#             proposals = {}
#             for r in list(unresolved):
#                 candidates = robot_candidates[r]
#                 idx = candidate_index[r]
#                 if idx < len(candidates):
#                     candidate = candidates[idx]
#                     proposals.setdefault(candidate[0], []).append((r, candidate))
#                 else:
#                     unresolved.remove(r)
#             for node, props in proposals.items():
#                 if len(props) == 1:
#                     r, candidate = props[0]
#                     assigned[r] = candidate
#                     unresolved.remove(r)
#                 else:
#                     best_r, best_candidate = max(props, key=lambda x: x[1][3])
#                     assigned[best_r] = best_candidate
#                     unresolved.remove(best_r)
#                     for r, candidate in props:
#                         if r != best_r:
#                             candidate_index[r] += 1
#             if not proposals:
#                 break


def test_sample_graph():
    # Fixed node positions.
    node_positions = {
        0: (5, 0),
        1: (5, 5),
        2: (10, 10),
        3: (0, 10)
    }
    # Fixed node values.
    node_values = {
        0: 0.95,
        1: 0.5,
        2: 0.5,
        3: 0.95
    }
    total_value = sum(node_values.values())
    # Normalized probabilities.
    node_probabilities = {i: node_values[i] / total_value for i in node_values}  # 0: ~0.33, 1: ~0.167, 2: ~0.167, 3: ~0.33
    
    # Fixed robot starting positions.
    robot_positions = {
        0: (0, 0),   
        1: (10, 0)    
    }
    n_robots = 2
    available_nodes = set(node_positions.keys())  # {0, 1, 2, 3}
    robot_paths = {r: [] for r in range(n_robots)}
    # Current positions will be updated as robots "move".
    robot_current_positions = robot_positions.copy()
    
    # To record comparisons per iteration.
    comparison_tables = []
    auction_total_per_iter = []
    optimal_total_per_iter = []
    iteration = 0
    
    # We will perform assignments until there are fewer than n_robots remaining.
    while available_nodes and len(available_nodes) >= n_robots:
        print(f"\n--- Iteration {iteration} ---")
        # === Optimal Assignment (Best-Case) ===
        available_nodes_list = list(available_nodes)
        cost_matrix_opt = np.zeros((n_robots, len(available_nodes_list)))
        for r in range(n_robots):
            for j, node in enumerate(available_nodes_list):
                cost_matrix_opt[r, j] = euclidean_distance(robot_current_positions[r], node_positions[node])
        row_ind, col_ind = linear_sum_assignment(cost_matrix_opt)
        optimal_assignments = {}
        for idx, r in enumerate(row_ind):
            node_opt = available_nodes_list[col_ind[idx]]
            distance_opt = cost_matrix_opt[r, col_ind[idx]]
            optimal_assignments[r] = (node_opt, distance_opt)
            print(f"Optimal for Robot {r}: Node {node_opt} at distance {distance_opt:.2f}")
        
        # === Dynamic Auction Assignment ===
        # Each robot computes bids = probability/distance for each available node.
        robot_candidates = {}
        for r in range(n_robots):
            pos = robot_current_positions[r]
            candidates = []
            for n in available_nodes:
                d = euclidean_distance(pos, node_positions[n])
                bid = node_probabilities[n] / d if d > 0 else float('inf')
                candidates.append((n, d, node_probabilities[n], bid))
            # Sort by descending bid.
            candidates.sort(key=lambda x: x[3], reverse=True)
            robot_candidates[r] = candidates
            print(f"\nRobot {r} candidates from position {pos}:")
            df_candidates = pd.DataFrame(candidates, columns=["Node", "Distance", "Probability", "Bid"])
            print(df_candidates)
        
        # assigned = resolve_conflict()
        # Resolve conflicts: assign each robot a unique node.
        assigned = {}
        candidate_index = {r: 0 for r in range(n_robots)}
        unresolved = set(range(n_robots))
        while unresolved:
            proposals = {}
            for r in list(unresolved):
                candidates = robot_candidates[r]
                idx = candidate_index[r]
                if idx < len(candidates):
                    candidate = candidates[idx]
                    proposals.setdefault(candidate[0], []).append((r, candidate))
                else:
                    unresolved.remove(r)
            for node, props in proposals.items():
                if len(props) == 1:
                    r, candidate = props[0]
                    assigned[r] = candidate
                    unresolved.remove(r)
                else:
                    best_r, best_candidate = max(props, key=lambda x: x[1][3])
                    assigned[best_r] = best_candidate
                    unresolved.remove(best_r)
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
                # Update robot position.
                robot_current_positions[r] = node_positions[node_auction]
                robot_paths[r].append(node_auction)
        comparison_tables.append(iter_table)
        auction_total_per_iter.append(auction_total)
        optimal_total_per_iter.append(optimal_total)
        
        # Remove the assigned nodes from available_nodes.
        for record in iter_table:
            available_nodes.discard(record["Auction Node"])
        iteration += 1
    
    # Print comparison tables.
    print("\nComparison Tables:")
    for i, table in enumerate(comparison_tables):
        print(f"\nIteration {i}:")
        print(pd.DataFrame(table))
    
    print("\nFinal Robot Paths:")
    for r in range(n_robots):
        print(f"Robot {r}: {robot_paths[r]}")
    
    print("\nOverall Totals:")
    overall_auction = sum(auction_total_per_iter)
    overall_optimal = sum(optimal_total_per_iter)
    print(f"Total Auction Distance: {overall_auction:.2f}")
    print(f"Total Optimal Distance: {overall_optimal:.2f}")
    print(f"Ratio (Auction/Optimal): {overall_auction/overall_optimal:.2f}")
    
    # --- Plot the Sample Scenario ---
    plt.figure(figsize=(8,8))
    G = nx.Graph()
    for i, pos in node_positions.items():
        G.add_node(f"Node {i}", pos=pos)
    for r, pos in robot_positions.items():
        G.add_node(f"Robot {r}", pos=pos)
    pos_all = nx.get_node_attributes(G, 'pos')
    nx.draw(G, pos_all, with_labels=True, node_size=800, node_color='lightblue')
    colors = ['red', 'blue']
    for r, path in robot_paths.items():
        start = robot_positions[r]
        coords = [start] + [node_positions[n] for n in path]
        plt.plot([p[0] for p in coords], [p[1] for p in coords],
                 color=colors[r], marker='o', label=f"Robot {r} Path")
    plt.title("Sample Graph Test: Dynamic Auction vs. Optimal")
    plt.legend()
    plt.show()

# Run the test sample.
test_sample_graph()
