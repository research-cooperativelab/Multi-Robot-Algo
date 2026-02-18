"""
Multi-Robot Search and Rescue: Unified Simulation Framework
============================================================
Three models compared via competitive ratio analysis:
  Model 1: Infinite Energy + No Communication (Random Baseline)
  Model 2: Infinite Energy + Full Communication (Auction)
  Model 3: Finite Energy + Communication at Base (Single-Node Sorties)
  Model 4: Finite Energy + Optimized Multi-Node Sorties

Metrics:
  Finder CR  = Distance traveled by the robot that found the target / Optimal
               (primary metric — measures algorithm quality)
  Team CR    = Total distance of ALL robots / Optimal
               (secondary — measures total resource expenditure)
  Optimal    = min distance from any robot's base to target (one-way, omniscient)
  Iterations = Number of search rounds until target found (maps to time)

"""

import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import statistics as stats
import random
import json
import os

# ============================================================
# Utility Functions
# ============================================================

def euclidean_distance(p1, p2):
    """Euclidean distance between two 2D points."""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def generate_instance(n_nodes, n_robots, area_scale, seed=None):
    """
    Generate a search instance: node positions, probabilities, 
    robot bases, and a hidden target.
    
    Returns dict with:
        node_positions: {node_id: (x, y)}
        node_probs:     {node_id: probability}
        bases:          {robot_id: (x, y)}
        target:         node_id of hidden target
        optimal_dist:   min distance from any base to target (one-way)
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    
    # Generate node positions
    node_positions = {
        i: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
        for i in range(n_nodes)
    }
    
    # Generate probabilities (normalized random values)
    raw_values = {i: np.random.uniform(0.1, 1.0) for i in range(n_nodes)}
    total = sum(raw_values.values())
    node_probs = {i: raw_values[i] / total for i in range(n_nodes)}
    
    # Generate robot base positions
    bases = {
        r: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
        for r in range(n_robots)
    }
    
    # Choose target weighted by probability
    target = random.choices(
        list(node_probs.keys()),
        weights=list(node_probs.values()),
        k=1
    )[0]
    
    # Optimal: closest robot goes straight to target (one-way)
    optimal_dist = min(
        euclidean_distance(bases[r], node_positions[target])
        for r in range(n_robots)
    )
    
    return {
        'node_positions': node_positions,
        'node_probs': node_probs,
        'bases': bases,
        'target': target,
        'optimal_dist': optimal_dist,
    }


# ============================================================
# Auction Resolution (shared by Models 1, 3, 4)
# ============================================================

def run_auction(robot_bids):
    """
    Resolve auction conflicts. Each robot has a sorted list of (node, bid_value, distance).
    Returns dict: {robot_id: (node, distance)}
    
    Algorithm:
    - Each robot proposes its top-choice node
    - If multiple robots want the same node, highest bid wins
    - Losers move to their next candidate
    - Repeat until all robots are assigned or out of candidates
    """
    assigned = {}
    idx = {r: 0 for r in robot_bids}
    unresolved = set(robot_bids.keys())
    
    max_iterations = 1000  # safety limit
    iteration = 0
    
    while unresolved and iteration < max_iterations:
        iteration += 1
        proposals = {}
        
        for r in list(unresolved):
            if idx[r] < len(robot_bids[r]):
                node, bid_val, dist = robot_bids[r][idx[r]]
                proposals.setdefault(node, []).append((r, bid_val, dist))
            else:
                # Robot has no more candidates
                unresolved.discard(r)
        
        if not proposals:
            break
        
        for node, runners in proposals.items():
            # Highest bid wins
            winner_r, _, winner_dist = max(runners, key=lambda x: x[1])
            assigned[winner_r] = (node, winner_dist)
            unresolved.discard(winner_r)
            
            # Losers move to next candidate
            for r, _, _ in runners:
                if r != winner_r:
                    idx[r] += 1
    
    return assigned


# ============================================================
# Model 1: Random Baseline (Infinite Energy, No Communication)
# ============================================================

def model1_random_baseline(instance, verbose=False):
    """
    Model 1: Random Baseline — Infinite Energy, No Communication
    
    Each round:
    1. Each robot independently picks a random available node 
       (weighted by probability priors — not completely blind)
    2. NO collision avoidance — two robots CAN pick the same node
    3. Each robot travels base -> node -> base (round trip)
    4. If target found, stop (last leg is one-way)
    5. Duplicate visits: both robots pay travel cost, node removed once
    
    This is the "floor" — any good algorithm must beat this.
    """
    node_positions = instance['node_positions']
    node_probs = instance['node_probs']
    bases = instance['bases']
    target = instance['target']
    optimal_dist = instance['optimal_dist']
    
    n_robots = len(bases)
    available = set(node_positions.keys())
    robot_paths = {r: [] for r in range(n_robots)}
    robot_dists = {r: 0.0 for r in range(n_robots)}
    
    iteration = 0
    
    while available:
        iteration += 1
        
        if verbose:
            print(f"\n--- Model 1 (Random), Round {iteration} ---")
            print(f"  Available nodes: {len(available)}")
        
        # Each robot independently picks a random node (probability-weighted)
        avail_list = list(available)
        weights = [node_probs[n] for n in avail_list]
        
        choices = {}  # {robot: (node, distance)}
        for r in range(n_robots):
            chosen_node = random.choices(avail_list, weights=weights, k=1)[0]
            d = euclidean_distance(bases[r], node_positions[chosen_node])
            choices[r] = (chosen_node, d)
        
        if verbose:
            for r, (n, d) in choices.items():
                print(f"  Robot {r} randomly picks Node {n} (dist={d:.2f})")
        
        # Execute — all robots travel simultaneously
        found = False
        finder = None
        visited_this_round = set()
        
        for r, (n, d) in choices.items():
            robot_paths[r].append(n)
            visited_this_round.add(n)
            
            if n == target:
                robot_dists[r] += d  # one-way to target
                found = True
                finder = r
            else:
                robot_dists[r] += 2 * d  # round trip
        
        # Remove all visited nodes
        available -= visited_this_round
        
        if found:
            total_dist = sum(robot_dists.values())
            comp_ratio = total_dist / optimal_dist if optimal_dist > 0 else float('inf')
            
            if verbose:
                print(f"\n  TARGET FOUND by Robot {finder} at Node {target}!")
                print(f"  Total distance: {total_dist:.2f}")
                print(f"  Competitive ratio: {comp_ratio:.2f}")
            
            return {
                'total_dist': total_dist,
                'optimal_dist': optimal_dist,
                'comp_ratio': comp_ratio,
                'iterations': iteration,
                'robot_paths': robot_paths,
                'robot_dists': dict(robot_dists),
                'found_by': finder,
            }
    
    raise RuntimeError("Target not found — all nodes exhausted without finding target")


# ============================================================
# Model 2: Infinite Energy + Full Communication (Auction, Node-to-Node)
# ============================================================

def model2_infinite_auction(instance, verbose=False):
    """
    Model 2: Infinite Energy + Full Communication (Auction, Node-to-Node)
    
    Key difference from Models 3/4: robots do NOT return to base.
    They move from node to node, since they have infinite energy.
    
    Each round:
    1. All robots compute bids from their CURRENT position:
       bid = prob[node] / dist(current_pos, node)
    2. Auction resolves conflicts (highest bid wins, full communication)
    3. Each robot moves current_pos -> assigned_node (one-way, no return)
    4. Robot's position updates to the visited node
    5. If target found, stop
    
    Finder CR = total chain distance (base -> n1 -> n2 -> ... -> target) / optimal
    """
    node_positions = instance['node_positions']
    node_probs = instance['node_probs']
    bases = instance['bases']
    target = instance['target']
    optimal_dist = instance['optimal_dist']
    
    n_robots = len(bases)
    available = set(node_positions.keys())
    robot_paths = {r: [] for r in range(n_robots)}
    robot_dists = {r: 0.0 for r in range(n_robots)}
    # Current positions — start at bases, update as robots move
    robot_pos = {r: bases[r] for r in range(n_robots)}
    
    iteration = 0
    
    while available:
        iteration += 1
        
        if verbose:
            print(f"\n--- Model 2 (Auction Node-to-Node), Round {iteration} ---")
            print(f"  Available nodes: {len(available)}")
        
        # 1. Each robot computes bids from CURRENT POSITION
        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d = euclidean_distance(robot_pos[r], node_positions[n])
                if d > 0:
                    bid_val = node_probs[n] / d
                else:
                    bid_val = float('inf')
                bids.append((n, bid_val, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids
        
        # 2. Auction resolution
        assigned = run_auction(robot_bids)
        
        if not assigned:
            if verbose:
                print("  No assignments possible, ending.")
            break
        
        if verbose:
            for r, (n, d) in assigned.items():
                print(f"  Robot {r} at {robot_pos[r]} -> Node {n} (dist={d:.2f})")
        
        # 3. Execute — all robots move simultaneously (one-way, no return)
        found = False
        finder = None
        for r, (n, d) in assigned.items():
            robot_paths[r].append(n)
            available.discard(n)
            robot_dists[r] += d  # one-way travel (no return to base)
            robot_pos[r] = node_positions[n]  # update position
            
            if n == target:
                found = True
                finder = r
        
        if found:
            total_dist = sum(robot_dists.values())
            comp_ratio = total_dist / optimal_dist if optimal_dist > 0 else float('inf')
            
            if verbose:
                print(f"\n  TARGET FOUND by Robot {finder} at Node {target}!")
                print(f"  Total distance: {total_dist:.2f}")
                print(f"  Competitive ratio: {comp_ratio:.2f}")
            
            return {
                'total_dist': total_dist,
                'optimal_dist': optimal_dist,
                'comp_ratio': comp_ratio,
                'iterations': iteration,
                'robot_paths': robot_paths,
                'robot_dists': dict(robot_dists),
                'found_by': finder,
            }
    
    raise RuntimeError("Target not found — possible bug in instance generation")


# ============================================================
# Model 3: Finite Energy + Communication at Base (Single-Node Sorties)
# ============================================================

def model3_finite_single(instance, energy, verbose=False):
    """
    Model 3: Finite Energy + Communication at Base (Single-Node Sorties)
    
    Same as Model 1, but with energy constraint:
    - A robot can only visit node n if 2 * dist(base, node) <= energy
    - Each round, robots recharge at base (full energy)
    - Robots only bid on reachable nodes
    
    Returns same dict as model1.
    """
    node_positions = instance['node_positions']
    node_probs = instance['node_probs']
    bases = instance['bases']
    target = instance['target']
    optimal_dist = instance['optimal_dist']
    
    n_robots = len(bases)
    available = set(node_positions.keys())
    robot_paths = {r: [] for r in range(n_robots)}
    robot_dists = {r: 0.0 for r in range(n_robots)}
    
    iteration = 0
    
    while available:
        iteration += 1
        
        if verbose:
            print(f"\n--- Model 3, Round {iteration} ---")
            print(f"  Available nodes: {len(available)}, Energy: {energy}")
        
        # 1. Each robot computes bids for reachable nodes only
        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d = euclidean_distance(bases[r], node_positions[n])
                # Energy filter: must be able to go there and come back
                if 2 * d <= energy and d > 0:
                    bid_val = node_probs[n] / d
                    bids.append((n, bid_val, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids
        
        # Check if any robot has candidates
        if all(len(b) == 0 for b in robot_bids.values()):
            if verbose:
                print("  No reachable nodes for any robot!")
            break
        
        # 2. Auction resolution
        assigned = run_auction(robot_bids)
        
        if not assigned:
            if verbose:
                print("  No assignments made.")
            break
        
        if verbose:
            for r, (n, d) in assigned.items():
                print(f"  Robot {r} -> Node {n} (dist={d:.2f}, energy_cost={2*d:.2f})")
        
        # 3. Execute assignments (all robots move simultaneously)
        found = False
        finder = None
        for r, (n, d) in assigned.items():
            robot_paths[r].append(n)
            available.discard(n)
            
            if n == target:
                robot_dists[r] += d  # one-way
                found = True
                finder = r
            else:
                robot_dists[r] += 2 * d  # round trip
        
        if found:
            total_dist = sum(robot_dists.values())
            comp_ratio = total_dist / optimal_dist if optimal_dist > 0 else float('inf')
            
            if verbose:
                print(f"\n  TARGET FOUND by Robot {finder} at Node {target}!")
                print(f"  Total distance: {total_dist:.2f}")
                print(f"  Competitive ratio: {comp_ratio:.2f}")
            
            return {
                'total_dist': total_dist,
                'optimal_dist': optimal_dist,
                'comp_ratio': comp_ratio,
                'iterations': iteration,
                'robot_paths': robot_paths,
                'robot_dists': dict(robot_dists),
                'found_by': finder,
            }
    
    # Target unreachable due to energy constraints
    return {
        'total_dist': float('inf'),
        'optimal_dist': optimal_dist,
        'comp_ratio': float('inf'),
        'iterations': iteration,
        'robot_paths': robot_paths,
        'robot_dists': dict(robot_dists),
        'found_by': None,
    }


# ============================================================
# Model 4: Finite Energy + Optimized Multi-Node Sorties
# ============================================================

def model4_finite_multi(instance, energy, verbose=False):
    """
    Model 4: Finite Energy + Optimized Multi-Node Sorties
    
    Key difference from Model 3: robots can visit MULTIPLE nodes per sortie.
    
    Each round:
    1. Auction assigns each robot a TOUR of nodes (greedy chain):
       - Start from base
       - Greedily pick best next node (prob/dist ratio) that still allows
         returning to base with remaining energy
       - Continue until no more reachable nodes
    2. Robots execute their tours
    3. If target found mid-tour, stop immediately
    4. Return to base, recharge, run new auction with updated available nodes
    
    Communication happens at base between sorties (robots share which 
    nodes they visited).
    
    Returns same dict as model1.
    """
    node_positions = instance['node_positions']
    node_probs = instance['node_probs']
    bases = instance['bases']
    target = instance['target']
    optimal_dist = instance['optimal_dist']
    
    n_robots = len(bases)
    available = set(node_positions.keys())
    robot_paths = {r: [] for r in range(n_robots)}
    robot_dists = {r: 0.0 for r in range(n_robots)}
    
    iteration = 0
    
    while available:
        iteration += 1
        
        if verbose:
            print(f"\n--- Model 4, Round {iteration} ---")
            print(f"  Available nodes: {len(available)}, Energy: {energy}")
        
        # Phase 1: Auction for FIRST node of each robot's tour
        # (coordination happens here — robots communicate at base)
        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d = euclidean_distance(bases[r], node_positions[n])
                # Must be able to visit and return
                if 2 * d <= energy and d > 0:
                    bid_val = node_probs[n] / d
                    bids.append((n, bid_val, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids
        
        if all(len(b) == 0 for b in robot_bids.values()):
            if verbose:
                print("  No reachable nodes for any robot!")
            break
        
        # Auction for first nodes
        first_assigned = run_auction(robot_bids)
        
        if not first_assigned:
            if verbose:
                print("  No assignments made.")
            break
        
        # Phase 2: Each robot greedily extends its tour
        # ALL first-assigned nodes are claimed — no other robot can visit them
        all_claimed = set(n for n, d in first_assigned.values())
        
        robot_tours = {}  # {robot_id: [(node, dist_from_prev), ...]}
        
        for r, (first_node, first_dist) in first_assigned.items():
            tour = [(first_node, first_dist)]
            current_pos = node_positions[first_node]
            remaining_energy = energy - first_dist  # energy used to get to first node
            
            # Nodes available for this robot's extension:
            # all available nodes minus anything claimed by ANY robot so far
            tour_available = available - all_claimed
            
            while tour_available:
                best_node = None
                best_bid = -1
                best_d = 0
                
                for n in tour_available:
                    d_to_node = euclidean_distance(current_pos, node_positions[n])
                    d_node_to_base = euclidean_distance(node_positions[n], bases[r])
                    
                    # Can we visit this node AND still return to base?
                    if d_to_node + d_node_to_base <= remaining_energy and d_to_node > 0:
                        bid_val = node_probs[n] / d_to_node
                        if bid_val > best_bid:
                            best_bid = bid_val
                            best_d = d_to_node
                            best_node = n
                
                if best_node is None:
                    break
                
                tour.append((best_node, best_d))
                tour_available.discard(best_node)
                all_claimed.add(best_node)  # claim it globally
                remaining_energy -= best_d
                current_pos = node_positions[best_node]
            
            robot_tours[r] = tour
        
        if verbose:
            for r, tour in robot_tours.items():
                nodes = [n for n, d in tour]
                total_tour_d = sum(d for n, d in tour)
                return_d = euclidean_distance(
                    node_positions[tour[-1][0]], bases[r]
                )
                print(f"  Robot {r} tour: {nodes} (tour_dist={total_tour_d:.2f}, return={return_d:.2f})")
        
        # Phase 3: Execute all tours simultaneously
        # All robots travel at the same time. We need to check if ANY robot
        # finds the target on their tour.
        target_found = False
        finder = None
        
        for r, tour in robot_tours.items():
            for node, d in tour:
                robot_dists[r] += d
                robot_paths[r].append(node)
                available.discard(node)
                
                if node == target:
                    target_found = True
                    finder = r
                    break  # This robot stops mid-tour
            
            if target_found and r == finder:
                # Finder stops mid-tour, no return trip
                pass
            else:
                # Non-finder completes full tour and returns to base
                if tour:
                    last_node = tour[-1][0]
                    return_dist = euclidean_distance(node_positions[last_node], bases[r])
                    robot_dists[r] += return_dist
        
        if target_found:
            total_dist = sum(robot_dists.values())
            comp_ratio = total_dist / optimal_dist if optimal_dist > 0 else float('inf')
            
            if verbose:
                print(f"\n  TARGET FOUND by Robot {finder} at Node {target} mid-tour!")
                print(f"  Total distance: {total_dist:.2f}")
                print(f"  Competitive ratio: {comp_ratio:.2f}")
            
            return {
                'total_dist': total_dist,
                'optimal_dist': optimal_dist,
                'comp_ratio': comp_ratio,
                'iterations': iteration,
                'robot_paths': robot_paths,
                'robot_dists': dict(robot_dists),
                'found_by': finder,
            }
    
    # Target unreachable
    return {
        'total_dist': float('inf'),
        'optimal_dist': optimal_dist,
        'comp_ratio': float('inf'),
        'iterations': iteration,
        'robot_paths': robot_paths,
        'robot_dists': dict(robot_dists),
        'found_by': None,
    }


# ============================================================
# Simulation Runner
# ============================================================

def _extract_metrics(result):
    """Extract both team CR and finder CR from a model result."""
    if result['found_by'] is None:
        return None
    finder = result['found_by']
    finder_dist = result['robot_dists'][finder]
    opt = result['optimal_dist']
    finder_cr = finder_dist / opt if opt > 0 else float('inf')
    return {
        'team_cr': result['comp_ratio'],
        'finder_cr': finder_cr,
        'iterations': result['iterations'],
        'total_dist': result['total_dist'],
        'finder_dist': finder_dist,
        'optimal_dist': opt,
    }


def _append_metrics(data_dict, metrics):
    """Append extracted metrics to a results data dict."""
    _MAP = {
        'finder_crs': 'finder_cr', 'team_crs': 'team_cr',
        'iterations': 'iterations', 'total_dists': 'total_dist',
        'finder_dists': 'finder_dist', 'optimal_dists': 'optimal_dist',
    }
    for key, metric_key in _MAP.items():
        data_dict[key].append(metrics[metric_key])


def run_trials(n_nodes, n_robots, area_scale, energy, n_trials=200, seed_base=42):
    """
    Run multiple trials for all 4 models on the SAME instances.
    Returns results dict with lists of metrics per model.
    Tracks both finder CR (primary) and team CR (secondary).
    """
    empty_data = lambda: {
        'finder_crs': [], 'team_crs': [], 'iterations': [],
        'total_dists': [], 'finder_dists': [], 'optimal_dists': [],
    }
    results = {mn: empty_data() for mn in MODEL_ORDER}
    
    failed = {mn: 0 for mn in MODEL_ORDER}
    
    for trial in range(n_trials):
        # Same instance for all models (fair comparison)
        instance = generate_instance(n_nodes, n_robots, area_scale, seed=seed_base + trial)
        
        # Model 1: Random baseline
        r1 = model1_random_baseline(instance)
        m1 = _extract_metrics(r1)
        _append_metrics(results['model1'], m1)
        
        # Model 2: Infinite energy + auction (node-to-node)
        r2 = model2_infinite_auction(instance)
        m2 = _extract_metrics(r2)
        _append_metrics(results['model2'], m2)
        
        # Model 3: Finite energy, single-node sorties
        r3 = model3_finite_single(instance, energy)
        m3 = _extract_metrics(r3)
        if m3 is not None:
            _append_metrics(results['model3'], m3)
        else:
            failed['model3'] += 1
        
        # Model 4: Finite energy, multi-node sorties
        r4 = model4_finite_multi(instance, energy)
        m4 = _extract_metrics(r4)
        if m4 is not None:
            _append_metrics(results['model4'], m4)
        else:
            failed['model4'] += 1
    
    results['meta'] = {
        'n_nodes': n_nodes,
        'n_robots': n_robots,
        'area_scale': area_scale,
        'energy': energy,
        'n_trials': n_trials,
    }
    for mn in MODEL_ORDER:
        results['meta'][f'failed_{mn}'] = failed[mn]
    
    return results


MODEL_LABELS = {
    'model1': 'Model 1: Random Baseline',
    'model2': 'Model 2: Infinite Energy + Auction (Node-to-Node)',
    'model3': 'Model 3: Finite Energy + Single Sortie',
    'model4': 'Model 4: Finite Energy + Multi-Node Sortie',
}
MODEL_LABELS_SHORT = {
    'model1': 'M1 (Random)',
    'model2': 'M2 (Auction N2N)',
    'model3': 'M3 (Single Sortie)',
    'model4': 'M4 (Multi Sortie)',
}
MODEL_COLORS = {
    'model1': '#E91E63',  # pink/red
    'model2': '#2196F3',  # blue
    'model3': '#FF9800',  # orange
    'model4': '#4CAF50',  # green
}
MODEL_ORDER = ['model1', 'model2', 'model3', 'model4']


def print_summary(results):
    """Print summary statistics for all models (both finder and team CR)."""
    meta = results['meta']
    print("=" * 70)
    print(f"SIMULATION SUMMARY")
    print(f"  Nodes={meta['n_nodes']}, Robots={meta['n_robots']}, "
          f"Area={meta['area_scale']}, Energy={meta['energy']}, "
          f"Trials={meta['n_trials']}")
    print("=" * 70)
    
    for model_name in MODEL_ORDER:
        data = results[model_name]
        if not data['finder_crs']:
            print(f"\n{MODEL_LABELS[model_name]}: No successful trials")
            continue
        
        fcr = data['finder_crs']
        tcr = data['team_crs']
        it = data['iterations']
        td = data['total_dists']
        fd = data['finder_dists']
        
        failed = meta.get(f'failed_{model_name}', 0)
        
        print(f"\n{MODEL_LABELS[model_name]}")
        print(f"  Successful trials: {len(fcr)}/{meta['n_trials']}"
              + (f" ({failed} failed)" if failed > 0 else ""))
        print(f"  Finder CR (primary): mean={np.mean(fcr):.3f}, "
              f"median={np.median(fcr):.3f}, "
              f"std={np.std(fcr):.3f}, "
              f"max={np.max(fcr):.3f}")
        print(f"  Team CR (secondary): mean={np.mean(tcr):.3f}, "
              f"median={np.median(tcr):.3f}, "
              f"std={np.std(tcr):.3f}")
        print(f"  Iterations:          mean={np.mean(it):.2f}, "
              f"median={np.median(it):.1f}, "
              f"max={np.max(it)}")
        print(f"  Total Distance:      mean={np.mean(td):.2f}")
        print(f"  Finder Distance:     mean={np.mean(fd):.2f}")


# ============================================================
# Plotting Functions
# ============================================================

def plot_results(results, save_dir=None):
    """Generate comparison plots for all models (both finder and team CR)."""
    
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    
    # --- Plot 1: Finder CR Histograms (PRIMARY) ---
    fig, axes = plt.subplots(1, 4, figsize=(18, 4), sharey=True)
    fig.suptitle('Distribution of Finder Competitive Ratios (Primary Metric)', fontsize=13)
    
    for ax, mn in zip(axes, MODEL_ORDER):
        data = results[mn]['finder_crs']
        if data:
            ax.hist(data, bins=25, color=MODEL_COLORS[mn], edgecolor='black', alpha=0.7)
            ax.axvline(np.mean(data), color='red', linestyle='--', linewidth=1.5,
                      label=f'Mean={np.mean(data):.2f}')
            ax.axvline(np.median(data), color='darkred', linestyle=':', linewidth=1.5,
                      label=f'Median={np.median(data):.2f}')
            ax.legend(fontsize=8)
        ax.set_title(MODEL_LABELS_SHORT[mn], fontsize=10)
        ax.set_xlabel('Finder CR')
        ax.grid(True, alpha=0.3)
    
    axes[0].set_ylabel('Frequency')
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'finder_cr_histograms.png'), dpi=150, bbox_inches='tight')
    plt.show()
    
    # --- Plot 2: Box Plot — Finder CR and Team CR side by side ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for ax, cr_key, title in [
        (axes[0], 'finder_crs', 'Finder Competitive Ratio (Primary)'),
        (axes[1], 'team_crs', 'Team Competitive Ratio (Secondary)'),
    ]:
        box_data = []
        box_labels = []
        box_colors = []
        for mn in MODEL_ORDER:
            data = results[mn][cr_key]
            if data:
                box_data.append(data)
                box_labels.append(MODEL_LABELS_SHORT[mn].split('(')[1].rstrip(')'))
                box_colors.append(MODEL_COLORS[mn])
        
        bp = ax.boxplot(box_data, labels=box_labels, patch_artist=True, 
                        showfliers=False)  # hide outliers for cleaner view
        for patch, color in zip(bp['boxes'], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        
        # Add mean markers
        for i, data in enumerate(box_data):
            ax.scatter(i + 1, np.mean(data), color='red', marker='D', s=40, zorder=5)
        
        ax.set_ylabel('Competitive Ratio')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'cr_boxplots.png'), dpi=150, bbox_inches='tight')
    plt.show()
    
    # --- Plot 3: Iterations vs Finder CR (scatter) ---
    fig, ax = plt.subplots(figsize=(8, 5))
    for mn in MODEL_ORDER:
        data = results[mn]
        if data['finder_crs']:
            ax.scatter(data['iterations'], data['finder_crs'],
                      alpha=0.4, color=MODEL_COLORS[mn],
                      label=MODEL_LABELS_SHORT[mn], s=20)
    
    ax.set_xlabel('Iterations to Find Target')
    ax.set_ylabel('Finder Competitive Ratio')
    ax.set_title('Finder CR vs. Search Duration')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'finder_cr_vs_iterations.png'), dpi=150, bbox_inches='tight')
    plt.show()
    
    # --- Plot 4: CDF of Finder CR ---
    fig, ax = plt.subplots(figsize=(8, 5))
    for mn in MODEL_ORDER:
        data = sorted(results[mn]['finder_crs'])
        if data:
            cdf = np.arange(1, len(data) + 1) / len(data)
            ax.plot(data, cdf, color=MODEL_COLORS[mn], linewidth=2,
                   label=MODEL_LABELS_SHORT[mn])
    
    ax.set_xlabel('Finder Competitive Ratio')
    ax.set_ylabel('Cumulative Probability')
    ax.set_title('CDF of Finder Competitive Ratios')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'finder_cr_cdf.png'), dpi=150, bbox_inches='tight')
    plt.show()
    
    # --- Plot 5: Total Distance and Finder Distance comparison ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for ax, dist_key, title in [
        (axes[0], 'total_dists', 'Total Team Distance'),
        (axes[1], 'finder_dists', 'Finder Robot Distance'),
    ]:
        box_data = []
        box_labels = []
        box_colors = []
        for mn in MODEL_ORDER:
            data = results[mn][dist_key]
            if data:
                box_data.append(data)
                box_labels.append(MODEL_LABELS_SHORT[mn].split('(')[1].rstrip(')'))
                box_colors.append(MODEL_COLORS[mn])
        
        bp = ax.boxplot(box_data, labels=box_labels, patch_artist=True,
                        showfliers=False)
        for patch, color in zip(bp['boxes'], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        for i, data in enumerate(box_data):
            ax.scatter(i + 1, np.mean(data), color='red', marker='D', s=40, zorder=5)
        
        ax.set_ylabel('Distance')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'distance_boxplots.png'), dpi=150, bbox_inches='tight')
    plt.show()


# ============================================================
# Parameter Sweep
# ============================================================

def sweep_energy(n_nodes, n_robots, area_scale, energy_values, n_trials=100, seed_base=42):
    """Sweep over energy values to see how battery capacity affects performance."""
    sweep_results = {}
    
    for E in energy_values:
        print(f"  Running E={E}...", end=' ', flush=True)
        results = run_trials(n_nodes, n_robots, area_scale, E, n_trials, seed_base)
        sweep_results[E] = results
        
        for m in MODEL_ORDER:
            fcr = results[m]['finder_crs']
            failed = results['meta'].get(f'failed_{m}', 0)
            if fcr:
                print(f"{MODEL_LABELS_SHORT[m]}: FCR={np.mean(fcr):.2f}", end='  ')
                if failed > 0:
                    print(f"(fail={failed})", end='  ')
        print()
    
    return sweep_results


def sweep_robots(n_nodes, robot_values, area_scale, energy, n_trials=100, seed_base=42):
    """Sweep over number of robots."""
    sweep_results = {}
    
    for R in robot_values:
        print(f"  Running R={R}...", end=' ', flush=True)
        results = run_trials(n_nodes, R, area_scale, energy, n_trials, seed_base)
        sweep_results[R] = results
        
        for m in MODEL_ORDER:
            fcr = results[m]['finder_crs']
            if fcr:
                print(f"{MODEL_LABELS_SHORT[m]}: FCR={np.mean(fcr):.2f}", end='  ')
        print()
    
    return sweep_results


def plot_energy_sweep(sweep_results, save_dir=None):
    """Plot results of energy sweep — finder CR, team CR, and failure rate."""
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    
    energy_vals = sorted(sweep_results.keys())
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Plot 1: Finder CR vs energy
    ax = axes[0]
    for mn in MODEL_ORDER:
        means, stds, valid_E = [], [], []
        for E in energy_vals:
            fcr = sweep_results[E][mn]['finder_crs']
            if fcr:
                means.append(np.mean(fcr))
                stds.append(np.std(fcr))
                valid_E.append(E)
        if means:
            ax.errorbar(valid_E, means, yerr=stds, marker='o',
                       color=MODEL_COLORS[mn], label=MODEL_LABELS_SHORT[mn],
                       capsize=3, linewidth=2, markersize=5)
    ax.set_xlabel('Energy Budget')
    ax.set_ylabel('Mean Finder CR')
    ax.set_title('Finder CR vs. Energy Budget')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Team CR vs energy
    ax = axes[1]
    for mn in MODEL_ORDER:
        means, valid_E = [], []
        for E in energy_vals:
            tcr = sweep_results[E][mn]['team_crs']
            if tcr:
                means.append(np.mean(tcr))
                valid_E.append(E)
        if means:
            ax.plot(valid_E, means, marker='o', color=MODEL_COLORS[mn],
                   label=MODEL_LABELS_SHORT[mn], linewidth=2, markersize=5)
    ax.set_xlabel('Energy Budget')
    ax.set_ylabel('Mean Team CR')
    ax.set_title('Team CR vs. Energy Budget')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Failure rate vs energy (only finite-energy models)
    ax = axes[2]
    for mn in ['model3', 'model4']:
        fail_rates = []
        for E in energy_vals:
            nt = sweep_results[E]['meta']['n_trials']
            failed = sweep_results[E]['meta'].get(f'failed_{mn}', 0)
            fail_rates.append(failed / nt * 100)
        ax.plot(energy_vals, fail_rates, marker='s', color=MODEL_COLORS[mn],
               label=MODEL_LABELS_SHORT[mn], linewidth=2, markersize=5)
    ax.set_xlabel('Energy Budget')
    ax.set_ylabel('Failure Rate (%)')
    ax.set_title('Target Unreachable Rate vs. Energy')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'energy_sweep.png'), dpi=150, bbox_inches='tight')
    plt.show()


def plot_robot_sweep(sweep_results, save_dir=None):
    """Plot results of robot count sweep — finder CR, team CR, and iterations."""
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    
    robot_vals = sorted(sweep_results.keys())
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Plot 1: Finder CR vs robots
    ax = axes[0]
    for mn in MODEL_ORDER:
        means, valid_R = [], []
        for R in robot_vals:
            fcr = sweep_results[R][mn]['finder_crs']
            if fcr:
                means.append(np.mean(fcr))
                valid_R.append(R)
        if means:
            ax.plot(valid_R, means, marker='o', color=MODEL_COLORS[mn],
                   label=MODEL_LABELS_SHORT[mn], linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Mean Finder CR')
    ax.set_title('Finder CR vs. Number of Robots')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Team CR vs robots
    ax = axes[1]
    for mn in MODEL_ORDER:
        means, valid_R = [], []
        for R in robot_vals:
            tcr = sweep_results[R][mn]['team_crs']
            if tcr:
                means.append(np.mean(tcr))
                valid_R.append(R)
        if means:
            ax.plot(valid_R, means, marker='o', color=MODEL_COLORS[mn],
                   label=MODEL_LABELS_SHORT[mn], linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Mean Team CR')
    ax.set_title('Team CR vs. Number of Robots')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Iterations vs robots
    ax = axes[2]
    for mn in MODEL_ORDER:
        means, valid_R = [], []
        for R in robot_vals:
            it = sweep_results[R][mn]['iterations']
            if it:
                means.append(np.mean(it))
                valid_R.append(R)
        if means:
            ax.plot(valid_R, means, marker='o', color=MODEL_COLORS[mn],
                   label=MODEL_LABELS_SHORT[mn], linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Mean Iterations')
    ax.set_title('Search Duration vs. Number of Robots')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'robot_sweep.png'), dpi=150, bbox_inches='tight')
    plt.show()


# ============================================================
# Main Execution
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("Multi-Robot Search & Rescue Simulation Framework")
    print("=" * 70)
    
    # --- Default Parameters ---
    N_NODES = 20
    N_ROBOTS = 3
    AREA_SCALE = 10
    ENERGY = 18
    N_TRIALS = 500
    SAVE_DIR = 'figures'
    
    # --- Run Main Simulation ---
    print(f"\nRunning {N_TRIALS} trials with {N_NODES} nodes, {N_ROBOTS} robots, "
          f"area={AREA_SCALE}, energy={ENERGY}...")
    results = run_trials(N_NODES, N_ROBOTS, AREA_SCALE, ENERGY, N_TRIALS)
    print_summary(results)
    
    # --- Generate Plots ---
    print("\nGenerating plots...")
    plot_results(results, save_dir=SAVE_DIR)
    
    # --- Energy Sweep ---
    print("\n" + "=" * 70)
    print("Energy Sweep")
    print("=" * 70)
    energy_values = [10, 12, 15, 18, 20, 25, 30, 40, 50]
    energy_sweep = sweep_energy(N_NODES, N_ROBOTS, AREA_SCALE, energy_values,
                                n_trials=200, seed_base=42)
    plot_energy_sweep(energy_sweep, save_dir=SAVE_DIR)
    
    # --- Robot Sweep ---
    print("\n" + "=" * 70)
    print("Robot Count Sweep")
    print("=" * 70)
    robot_values = [1, 2, 3, 4, 5, 6]
    robot_sweep = sweep_robots(N_NODES, robot_values, AREA_SCALE, ENERGY,
                               n_trials=200, seed_base=42)
    plot_robot_sweep(robot_sweep, save_dir=SAVE_DIR)
    
    print("\nDone! Figures saved to:", SAVE_DIR)