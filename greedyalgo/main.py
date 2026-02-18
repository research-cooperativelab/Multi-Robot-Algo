# Visiting all the nodes in a graph using greedy algorithm with multiple robots
# Class Robot -> they only know their position. and the euclidean distance to the other nodes on graph 
# They are scattered around the graph and they need to visit all the nodes in the graph
# They know the probability of each node and the distance to each node so they would like to choose the best node to visit next which would be calculated by probability / distance

# min_weight_matching *  - 1 (we need to maximaize the minimum) 
# The ony thing that we kept 
# 
#  we have two robots and 4 nodes 
# 1. Create a graph with 4 nodes and 2 robots - put the target at any of the nodes randomly
# 2. Create a probability for each node
# 3. Create a distance for each node
# 4. Create a function to calculate the probability / distance for each node
# 5. Create a function to calculate the minimum weight matching for each robot
# 6. If any of the robots is not at the target repeat the process
# 6. STOP when any robot is at target 
# 7. Compute the compatative ratio which is going to be the sum of the previous distances of the winner robot divided by the shortest distance of any of the robots to the target 
# 8. Compute the ratio of the winner robot to the other robots and return the result


# What if it is not a complete graph 
# What if we have obstacles. We need a more general approach to the problem

# 

import networkx as nx
import random, math
import matplotlib.pyplot as plt
import numpy as np 

def count_outliers(data):
    Q1 = np.percentile(data, 25)
    Q3 = np.percentile(data, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = [x for x in data if x < lower_bound or x > upper_bound]
    return len(outliers), outliers



def create_complete_graph(num_nodes):
    """
    Create a complete undirected graph with the given number of nodes.
    Each node is assigned random (x, y) coordinates for distance calculation.
    The graph edges are weighted by the Euclidean distance between node coordinates.
    """
    G = nx.Graph()
    positions = {}
    # Assign random coordinates to each node
    for i in range(num_nodes):
        x = random.random() * 100
        y = random.random() * 100
        positions[i] = (x, y)
        G.add_node(i, pos=(x, y))
        
    # Add edges between every pair of nodes with weight equal to Euclidean distance
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            (x1, y1) = positions[i]
            (x2, y2) = positions[j]
            distance = math.hypot(x1 - x2, y1 - y2)
            G.add_edge(i, j, weight=distance)
    
    return G, positions

def assign_probabilities(num_nodes):
    """
    Assign a random probability value to each node.
    Probabilities are drawn uniformly at random in [0, 1). These values represent
    the belief that the target might be at each node.
    """
    probabilities = {}
    for i in range(num_nodes):
        probabilities[i] = random.random()
    return probabilities

def greedy_choice_for_robot(robot_node, probabilities, positions):
    """
    Determine the best next node for a robot (at robot_node) using a greedy strategy.
    The greedy choice is the node that maximizes probability/distance for this robot.
    """
    best_node = None
    best_ratio = -float('inf')
    for node, prob in probabilities.items():
        if node == robot_node or prob == 0:
            continue  # Skip the current node or any node with zero probability
        (x1, y1) = positions[robot_node]
        (x2, y2) = positions[node]
        dist = math.hypot(x1 - x2, y1 - y2)
        if dist == 0:
            continue
        ratio = prob / dist
        if ratio > best_ratio:
            best_ratio = ratio
            best_node = node
    return best_node, best_ratio

def greedy_assignments(robot_positions, probabilities, positions):
    """
    Get each robot's chosen node if each acts greedily (independently) based on probability/distance.
    """
    choices = {}
    ratios = {}
    for r_idx, robot_node in enumerate(robot_positions):
        next_node, value = greedy_choice_for_robot(robot_node, probabilities, positions)
        choices[r_idx] = next_node
        ratios[r_idx] = value
    return choices, ratios

def match_robots_to_nodes(robot_positions, probabilities, positions):
    """
    Compute an optimal assignment of robots to nodes using min_weight_matching.
    Edge weights are defined as the inverse of the probability/distance ratio (distance/probability),
    so that minimizing the weight maximizes the original probability/distance objective.
    """
    mg = nx.Graph()
    # Add nodes for each robot and each potential target node
    for r_idx in range(len(robot_positions)):
        mg.add_node(("R", r_idx))
    for node in probabilities:
        mg.add_node(("N", node))
    # Add edges from each robot to each node with weight = distance / probability
    for r_idx, robot_node in enumerate(robot_positions):
        (x1, y1) = positions[robot_node]
        for node, prob in probabilities.items():
            if node == robot_node or prob == 0:
                continue
            (x2, y2) = positions[node]
            dist = math.hypot(x1 - x2, y1 - y2)
            if dist == 0:
                continue
            weight = dist / prob  # Inverse of probability/distance as weight
            mg.add_edge(("R", r_idx), ("N", node), weight=weight)
    matching = nx.algorithms.matching.min_weight_matching(mg)
    assignment = {}
    for u, v in matching:
        if u[0] == "R":
            robot_idx = u[1]
            node_idx = v[1]
        else:
            robot_idx = v[1]
            node_idx = u[1]
        assignment[robot_idx] = node_idx
    return assignment

def simulate_search(graph, positions, probabilities, robot_starts, target, verbose=False):
    """
    Simulate the multi-robot traversal until one robot finds the target.
    Robots move greedily (with matching-based coordination) and update beliefs after visiting nodes.
    Returns:
      - distances_traveled: list of total distances traveled by each robot
      - winner: index of the winning robot (that reached the target)
      - comp_ratio: (winner distance traveled) / (shortest direct distance from a start to the target)
      - perf_ratio: ratio of the winning robot's distance to the other robot's distance (for 2 robots)
      - final_positions: list containing the final positions of each robot
      - paths: a dictionary mapping each robot to the list of nodes it visited (its path) each round
    """
    num_robots = len(robot_starts)
    robot_positions = robot_starts[:]  # current positions of each robot
    distances_traveled = [0.0] * num_robots
    paths = {i: [robot_starts[i]] for i in range(num_robots)}
    round_num = 0

    # Compute the shortest distance from any start position to the target (for competitive ratio)
    shortest_start_to_target = min(
        math.hypot(positions[r][0] - positions[target][0], positions[r][1] - positions[target][1])
        for r in robot_starts
    )

    while True:
        if verbose:
            print(f"Round {round_num}: Robot positions: {robot_positions}")
        round_num += 1
        
        # Check if any robot has reached the target
        for r_idx, node in enumerate(robot_positions):
            if node == target:
                winner = r_idx
                comp_ratio = float('inf') if shortest_start_to_target == 0 else (distances_traveled[r_idx] / shortest_start_to_target)
                perf_ratio = None
                if num_robots == 2:
                    other_idx = 1 - r_idx
                    perf_ratio = (distances_traveled[r_idx] / distances_traveled[other_idx]) if distances_traveled[other_idx] > 0 else float('inf')
                if verbose:
                    print(f"Robot {r_idx} reached the target at node {target}!")
                return distances_traveled, winner, comp_ratio, perf_ratio, robot_positions, paths

        # Determine move assignments via matching
        assignment = match_robots_to_nodes(robot_positions, probabilities, positions)
        if verbose:
            print(f"  Assignment: {assignment}")

        # Each robot moves to its assigned node; update distances, positions, and record the path
        for r_idx, next_node in assignment.items():
            current_node = robot_positions[r_idx]
            dist = math.hypot(positions[current_node][0] - positions[next_node][0],
                              positions[current_node][1] - positions[next_node][1])
            distances_traveled[r_idx] += dist
            robot_positions[r_idx] = next_node
            paths[r_idx].append(next_node)
        if verbose:
            print(f"  New positions: {robot_positions}")
            print(f"  Distances traveled: {distances_traveled}\n")

        # Mark visited nodes (if not the target) as having zero probability
        for r_idx, node in enumerate(robot_positions):
            if node != target:
                probabilities[node] = 0.0

def save_graph_as_gml(G, filepath):
    """
    Save the given NetworkX graph to a GML file for external inspection.
    """
    nx.write_gml(G, filepath)
    print(f"Graph saved to GML file at: {filepath}")

def visualize_graph(G, positions, robot_positions=None, target=None):
    """
    Visualize the graph using Matplotlib.
    Robots are shown in red with labels, the target in green, and other nodes in light blue.
    """
    plt.figure(figsize=(8, 8))
    node_colors = []
    for node in G.nodes:
        if target is not None and node == target:
            node_colors.append('green')
        elif robot_positions is not None and node in robot_positions:
            node_colors.append('red')
        else:
            node_colors.append('lightblue')
    nx.draw_networkx(G, pos=positions, node_color=node_colors, with_labels=True, node_size=600)
    
    if robot_positions is not None:
        for idx, node in enumerate(robot_positions):
            x, y = positions[node]
            plt.text(x, y + 3, f"Robot {idx}", color='white', fontweight='bold',
                     fontsize=12, bbox=dict(facecolor="red", alpha=0.6, edgecolor="none"))
    if target is not None:
        x, y = positions[target]
        plt.text(x, y + 3, "Target", color='white', fontweight='bold', fontsize=12,
                 bbox=dict(facecolor="green", alpha=0.6, edgecolor="none"))
    
    plt.title("Graph Visualization: Robots (Red) and Target (Green)")
    plt.axis("equal")
    plt.show()

def visualize_paths(G, positions, paths, target=None):
    """
    Plot the full paths taken by each robot during the simulation.
    Each robot's path is drawn as a line connecting the node positions in the order visited.
    The graph is drawn in the background.
    """
    plt.figure(figsize=(8, 8))
    
    # Draw the underlying graph in light gray for context.
    nx.draw_networkx(G, pos=positions, node_color='lightblue', with_labels=True, node_size=500, edge_color='gray')
    
    colors = ['red', 'blue', 'orange', 'purple']  # Colors for different robots (expand as needed)
    
    for r_idx, path in paths.items():
        path_coords = [positions[node] for node in path]
        xs, ys = zip(*path_coords)
        plt.plot(xs, ys, marker='o', color=colors[r_idx % len(colors)], label=f"Robot {r_idx} Path")
        # Annotate rounds (optional)
        for round_num, node in enumerate(path):
            x, y = positions[node]
            plt.text(x, y, f"{round_num}", fontsize=10, color=colors[r_idx % len(colors)])
    
    # Mark the target clearly, if provided.
    if target is not None:
        x, y = positions[target]
        plt.scatter([x], [y], color='green', s=200, label='Target')
        plt.text(x, y + 3, "Target", color='white', fontweight='bold', 
                 fontsize=12, bbox=dict(facecolor="green", alpha=0.6, edgecolor="none"))
    
    plt.title("Robot Paths During Simulation")
    plt.legend()
    plt.axis("equal")
    plt.show()

# Main simulation: run 100 times to compute average ratios using a larger graph (e.g., 10 nodes)
# run it for different amounts of robots and see how it chnages 
# The CR should be independent of the num_robots 

# distribution of the simulations 
if __name__ == "__main__":
    stored_comp_ratio = []
    
    for i in range(2, 21):
        # I can run different 
        num_simulations =50
        num_nodes = 50  # Increase number of nodes for more complex simulation
        number_robots = i #Number of robots 
        
        comp_ratios = []
        perf_ratios = []

        for i in range(num_simulations):
            # Create new graph and assign probabilities for each simulation run
            G, positions = create_complete_graph(num_nodes)
            probabilities = assign_probabilities(num_nodes)
            
            # Select i distinct starting nodes for the robots
            start_nodes = random.sample(list(G.nodes), number_robots)
            # Choose a target node that is not one of the robot starting nodes
            potential_targets = [n for n in G.nodes if n not in start_nodes]
            if not potential_targets:
                continue  # Skip if no valid target found
            target_node = random.choice(potential_targets)
            
            # Run the simulation (not verbose during averaging)
            distances, winner, comp_ratio, perf_ratio, final_positions, _ = simulate_search(
                G, positions, probabilities, start_nodes, target_node, verbose=False)
            comp_ratios.append(comp_ratio)
            if perf_ratio is not None:
                perf_ratios.append(perf_ratio)
        
        avg_comp_ratio = sum(comp_ratios) / len(comp_ratios) if comp_ratios else None
        avg_perf_ratio = sum(perf_ratios) / len(perf_ratios) if perf_ratios else None
        
        print(f"Over {num_simulations} simulation runs:")
        if avg_comp_ratio is not None:
            print(f"  Average Comparative Ratio: {avg_comp_ratio:.2f}")
        if avg_perf_ratio is not None:
            print(f"  Average Performance Ratio: {avg_perf_ratio:.2f}")
        # Adding the avg comp ratio to the list 
        stored_comp_ratio.append(avg_comp_ratio)
        # Single simulation run with verbose output for testing and visualization of paths.
        # print("\nSingle simulation run for detailed visualization:")
        # G, positions = create_complete_graph(num_nodes)
        # probabilities = assign_probabilities(num_nodes)

        # start_nodes = random.sample(list(G.nodes), number_robots)

        # potential_targets = [n for n in G.nodes if n not in start_nodes]
        # if not potential_targets:
        #     raise Exception("No valid target available. All nodes are occupied by robots!")
 
        # target_node = random.choices(list(G.nodes), weights=probabilities.values(), k=1)[0]
        # print(f"Target node chosen: {target_node}")  
        
        # distances, winner, comp_ratio, perf_ratio, final_positions, paths = simulate_search(
        #     G, positions, probabilities, start_nodes, target_node, verbose=True)
        
        print(f"\nFinal Results:")
        print(f"  Starting nodes: {start_nodes}, Target node: {target_node}")
        print(f"  Distances traveled: {distances}")
        print(f"  Robot {winner} reached the target first.")
        print(f"  Comparative Ratio: {comp_ratio:.2f}")
        if perf_ratio is not None:
            print(f"  Performance Ratio: {perf_ratio:.2f}")
        
        # Save the graph in GML format (optional)
        save_graph_as_gml(G, "my_graph.gml")
        
        # # Visualize the final positions on the graph
        # visualize_graph(G, positions, robot_positions=final_positions, target=target_node)
        # # Visualize the full robot paths across all rounds
        # visualize_paths(G, positions, paths, target=target_node)


        # Create a figure for the boxplots
        # plt.figure(figsize=(8, 6))

        # # We put comp_ratios and perf_ratios in a list for boxplot
        # # Each element in the list corresponds to one box in the chart.
        # data_to_plot = [comp_ratios, perf_ratios]

        # # Optional: Customize the style of the boxplot
        # boxprops = dict(linewidth=1.5, color='black')
        # medianprops = dict(linewidth=1.5, color='red')
        # meanpointprops = dict(marker='x', markeredgecolor='blue', markerfacecolor='blue')

        # plt.boxplot(
        #     data_to_plot,
        #     labels=['Comparative Ratio', 'Performance Ratio'],
        #     showmeans=True,             # Show mean markers
        #     meanprops=meanpointprops,   # Style for the mean markers
        #     boxprops=boxprops,
        #     medianprops=medianprops
        # )

        # plt.title("Boxplots of Comparative and Performance Ratios Over 1000 Runs")
        # plt.ylabel("Ratio Value")
        # plt.grid(True, linestyle='--', alpha=0.7)
        # # plt.yscale('log')
        # plt.show()
        
        # comp_outlier_count, comp_outliers = count_outliers(comp_ratios)
        # perf_outlier_count, perf_outliers = count_outliers(perf_ratios)
        
        # print(f"Comparative Ratios Outliers Count: {comp_outlier_count}")
        # print(f"Performance Ratios Outliers Count: {perf_outlier_count}")
    
    # drawing the line graph for the x = n robots and y = CR 
    plt.figure(figsize=(10, 6))
    plt.plot(range(2, 21), stored_comp_ratio, marker='o')
    plt.title("Comparative Ratio vs. Number of Robots")
    plt.xlabel("Number of Robots")
    plt.ylabel("Comparative Ratio")
    plt.grid(True)
    plt.show()

    print(stored_comp_ratio)
# store the number of nodes, CR and number of robots and then you can get a 3d graph where you see the contour 
# it can be a 3d plot or other ways to represent this in 3d measures