"""
Multi-Robot Search and Rescue: Unified Simulation Framework
============================================================
Three models compared via competitive ratio analysis:
  Model 1: Infinite Energy + No Communication (Random Baseline)
  Model 2: Infinite Energy + Full Communication (Auction, Node-to-Node)
  Model 3: Finite Energy + Communication at Base (Single-Node Sorties)
  Model 4: Finite Energy + Optimized Multi-Node Sorties

Metrics:
  Finder CR  = Distance traveled by the robot that found the target / Optimal
               (primary metric — measures algorithm quality)
  Team CR    = Total distance of ALL robots / Optimal
               (secondary — measures total resource expenditure)
  Optimal    = min distance from any robot's base to target (one-way, omniscient)
  Iterations = Number of search rounds until target found (maps to time)

Usage:
  python main.py                          # Run all models with defaults
  python main.py --model 1 --verbose      # Test Model 1 interactively
  python main.py --model 4 --trials 500   # Run Model 4 with 500 trials
  python main.py --sweep energy            # Energy parameter sweep
  python main.py --sweep robots            # Robot count sweep
  python main.py --verify-bounds           # Check theoretical bounds
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import statistics as stats
import random
import json
import os
import sys

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

    node_positions = {
        i: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
        for i in range(n_nodes)
    }

    raw_values = {i: np.random.uniform(0.1, 1.0) for i in range(n_nodes)}
    total = sum(raw_values.values())
    node_probs = {i: raw_values[i] / total for i in range(n_nodes)}

    bases = {
        r: (np.random.uniform(0, area_scale), np.random.uniform(0, area_scale))
        for r in range(n_robots)
    }

    target = random.choices(
        list(node_probs.keys()),
        weights=list(node_probs.values()),
        k=1
    )[0]

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
# Auction Resolution (shared by Models 2, 3, 4)
# ============================================================

def run_auction(robot_bids):
    """
    Resolve auction conflicts. Each robot has a sorted list of (node, bid_value, distance).
    Returns dict: {robot_id: (node, distance)}

    Algorithm (sequential single-item auction):
    - Each robot proposes its top-choice node
    - If multiple robots want the same node, highest bid wins
    - Losers move to their next candidate
    - Repeat until all robots are assigned or out of candidates

    Note: A robot that wins node X is removed from contention. The remaining
    robots continue proposing. A loser only bumps its index when it LOST a
    conflict, not when it proposed unopposed (in that case it wins immediately).
    """
    assigned = {}
    idx = {r: 0 for r in robot_bids}
    unresolved = set(robot_bids.keys())
    taken_nodes = set()  # track assigned nodes to prevent double-assignment

    max_iterations = 1000
    iteration = 0

    while unresolved and iteration < max_iterations:
        iteration += 1
        proposals = {}

        for r in list(unresolved):
            # Skip past any candidates whose nodes are already taken
            while idx[r] < len(robot_bids[r]) and robot_bids[r][idx[r]][0] in taken_nodes:
                idx[r] += 1

            if idx[r] < len(robot_bids[r]):
                node, bid_val, dist = robot_bids[r][idx[r]]
                proposals.setdefault(node, []).append((r, bid_val, dist))
            else:
                unresolved.discard(r)

        if not proposals:
            break

        for node, runners in proposals.items():
            winner_r, _, winner_dist = max(runners, key=lambda x: x[1])
            assigned[winner_r] = (node, winner_dist)
            taken_nodes.add(node)
            unresolved.discard(winner_r)

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
    4. If target found, stop (last leg is one-way for finder)
    5. Duplicate visits: both robots pay travel cost, node removed once
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

        avail_list = list(available)
        weights = [node_probs[n] for n in avail_list]

        choices = {}
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
        finder_dist = float('inf')
        visited_this_round = set()

        for r, (n, d) in choices.items():
            robot_paths[r].append(n)
            visited_this_round.add(n)

            if n == target:
                robot_dists[r] += d  # one-way to target
                # FIX: if multiple robots find target simultaneously,
                # pick the one with the shortest distance (closest base)
                if not found or d < finder_dist:
                    finder = r
                    finder_dist = d
                found = True
            else:
                robot_dists[r] += 2 * d  # round trip

        available -= visited_this_round

        if found:
            total_dist = sum(robot_dists.values())
            comp_ratio = total_dist / optimal_dist if optimal_dist > 0 else float('inf')

            if verbose:
                print(f"\n  TARGET FOUND by Robot {finder} at Node {target}!")
                print(f"  Finder distance: {robot_dists[finder]:.2f}")
                print(f"  Total team distance: {total_dist:.2f}")
                print(f"  Optimal distance: {optimal_dist:.2f}")
                print(f"  Team CR: {comp_ratio:.2f}")

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
    robot_pos = {r: bases[r] for r in range(n_robots)}

    iteration = 0

    while available:
        iteration += 1

        if verbose:
            print(f"\n--- Model 2 (Auction Node-to-Node), Round {iteration} ---")
            print(f"  Available nodes: {len(available)}")

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

        assigned = run_auction(robot_bids)

        if not assigned:
            if verbose:
                print("  No assignments possible, ending.")
            break

        if verbose:
            for r, (n, d) in assigned.items():
                print(f"  Robot {r} at ({robot_pos[r][0]:.1f},{robot_pos[r][1]:.1f}) "
                      f"-> Node {n} (dist={d:.2f})")

        found = False
        finder = None
        for r, (n, d) in assigned.items():
            robot_paths[r].append(n)
            available.discard(n)
            robot_dists[r] += d
            robot_pos[r] = node_positions[n]

            if n == target:
                found = True
                finder = r

        if found:
            total_dist = sum(robot_dists.values())
            comp_ratio = total_dist / optimal_dist if optimal_dist > 0 else float('inf')

            if verbose:
                print(f"\n  TARGET FOUND by Robot {finder} at Node {target}!")
                print(f"  Finder distance: {robot_dists[finder]:.2f}")
                print(f"  Total team distance: {total_dist:.2f}")
                print(f"  Optimal distance: {optimal_dist:.2f}")
                print(f"  Team CR: {comp_ratio:.2f}")

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

    Each round:
    - Robots recharge at base (full energy)
    - Auction assigns each robot one reachable node (2*d <= energy)
    - Each robot travels base -> node -> base (round trip)
    - Finder pays one-way only
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
            print(f"\n--- Model 3 (Single Sortie), Round {iteration} ---")
            print(f"  Available nodes: {len(available)}, Energy: {energy}")

        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d = euclidean_distance(bases[r], node_positions[n])
                if 2 * d <= energy and d > 0:
                    bid_val = node_probs[n] / d
                    bids.append((n, bid_val, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids

        if all(len(b) == 0 for b in robot_bids.values()):
            if verbose:
                print("  No reachable nodes for any robot!")
            break

        assigned = run_auction(robot_bids)

        if not assigned:
            if verbose:
                print("  No assignments made.")
            break

        if verbose:
            for r, (n, d) in assigned.items():
                print(f"  Robot {r} -> Node {n} (dist={d:.2f}, energy_cost={2*d:.2f})")

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
                print(f"  Finder distance: {robot_dists[finder]:.2f}")
                print(f"  Total team distance: {total_dist:.2f}")
                print(f"  Optimal distance: {optimal_dist:.2f}")
                print(f"  Team CR: {comp_ratio:.2f}")

            return {
                'total_dist': total_dist,
                'optimal_dist': optimal_dist,
                'comp_ratio': comp_ratio,
                'iterations': iteration,
                'robot_paths': robot_paths,
                'robot_dists': dict(robot_dists),
                'found_by': finder,
            }

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

    Each round:
    1. Auction assigns each robot a FIRST node (coordination at base)
    2. Each robot greedily extends its tour: pick best next node
       (prob/dist ratio) that still allows returning to base
    3. Tour extensions use ROUND-ROBIN ordering to avoid bias
    4. Robots execute tours; finder stops mid-tour
    5. Return to base, recharge, new auction with updated available nodes
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
            print(f"\n--- Model 4 (Multi-Node Sortie), Round {iteration} ---")
            print(f"  Available nodes: {len(available)}, Energy: {energy}")

        # Phase 1: Auction for first node of each robot's tour
        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d = euclidean_distance(bases[r], node_positions[n])
                if 2 * d <= energy and d > 0:
                    bid_val = node_probs[n] / d
                    bids.append((n, bid_val, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids

        if all(len(b) == 0 for b in robot_bids.values()):
            if verbose:
                print("  No reachable nodes for any robot!")
            break

        first_assigned = run_auction(robot_bids)

        if not first_assigned:
            if verbose:
                print("  No assignments made.")
            break

        # Phase 2: Round-robin greedy tour extension
        # (FIX: use round-robin instead of sequential to avoid ordering bias)
        all_claimed = set(n for n, d in first_assigned.values())

        robot_tours = {}
        robot_remaining_energy = {}
        robot_current_pos = {}

        for r, (first_node, first_dist) in first_assigned.items():
            robot_tours[r] = [(first_node, first_dist)]
            robot_current_pos[r] = node_positions[first_node]
            robot_remaining_energy[r] = energy - first_dist

        # Round-robin extension: each robot picks one node per sub-round
        active_robots = set(first_assigned.keys())
        while active_robots:
            made_progress = False
            for r in list(active_robots):
                tour_available = available - all_claimed
                best_node = None
                best_bid = -1
                best_d = 0

                for n in tour_available:
                    d_to_node = euclidean_distance(robot_current_pos[r], node_positions[n])
                    d_node_to_base = euclidean_distance(node_positions[n], bases[r])

                    if d_to_node + d_node_to_base <= robot_remaining_energy[r] and d_to_node > 0:
                        bid_val = node_probs[n] / d_to_node
                        if bid_val > best_bid:
                            best_bid = bid_val
                            best_d = d_to_node
                            best_node = n

                if best_node is None:
                    active_robots.discard(r)
                else:
                    robot_tours[r].append((best_node, best_d))
                    all_claimed.add(best_node)
                    robot_remaining_energy[r] -= best_d
                    robot_current_pos[r] = node_positions[best_node]
                    made_progress = True

            if not made_progress:
                break

        if verbose:
            for r, tour in robot_tours.items():
                nodes = [n for n, d in tour]
                total_tour_d = sum(d for n, d in tour)
                return_d = euclidean_distance(node_positions[tour[-1][0]], bases[r])
                print(f"  Robot {r} tour: {nodes} "
                      f"(tour_dist={total_tour_d:.2f}, return={return_d:.2f})")

        # Phase 3: Execute all tours simultaneously
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
                    break  # Finder stops mid-tour

            if target_found and r == finder:
                pass  # No return trip for finder
            else:
                if tour:
                    last_node = tour[-1][0]
                    return_dist = euclidean_distance(node_positions[last_node], bases[r])
                    robot_dists[r] += return_dist

        if target_found:
            total_dist = sum(robot_dists.values())
            comp_ratio = total_dist / optimal_dist if optimal_dist > 0 else float('inf')

            if verbose:
                print(f"\n  TARGET FOUND by Robot {finder} at Node {target} mid-tour!")
                print(f"  Finder distance: {robot_dists[finder]:.2f}")
                print(f"  Total team distance: {total_dist:.2f}")
                print(f"  Optimal distance: {optimal_dist:.2f}")
                print(f"  Team CR: {comp_ratio:.2f}")

            return {
                'total_dist': total_dist,
                'optimal_dist': optimal_dist,
                'comp_ratio': comp_ratio,
                'iterations': iteration,
                'robot_paths': robot_paths,
                'robot_dists': dict(robot_dists),
                'found_by': finder,
            }

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
# Theoretical Bounds (unchanged from original)
# ============================================================

def compute_theoretical_bounds(n, R, L, E):
    """Compute theoretical upper bounds on expected finder CR for each model."""
    d_avg = 0.5214 * L
    d_nn = L / (2 * np.sqrt(n))
    d_opt_approx = d_avg / np.sqrt(R)

    E_K_uniform = sum((i - 1) // R + 1 for i in range(1, n + 1)) / n

    d_hop = L / np.sqrt(n)
    bound_m2 = E_K_uniform * d_hop / d_opt_approx

    bound_m3 = (2 * E_K_uniform - 1) * d_avg / d_opt_approx

    S_provable = max((E - 2 * d_avg) / d_hop, 1) if E > 2 * d_avg else 1
    RS_provable = max(int(R * S_provable), R)
    E_K_m4_provable = sum((i - 1) // RS_provable + 1 for i in range(1, n + 1)) / n
    bound_m4_provable = E * E_K_m4_provable / d_opt_approx

    S_empirical = max(0.33 * np.sqrt(n) * E / L, 1)
    RS_empirical = max(int(R * S_empirical), R)
    E_K_m4_emp = sum((i - 1) // RS_empirical + 1 for i in range(1, n + 1)) / n
    bound_m4_empirical = E * E_K_m4_emp / d_opt_approx

    p_find_per_round = 1 - ((n - 1) / n) ** R
    E_K_random = 1 / p_find_per_round
    bound_m1 = (2 * E_K_random - 1) * d_avg / d_opt_approx

    improvement = bound_m3 / bound_m4_provable if bound_m4_provable > 0 else float('inf')

    return {
        'd_avg': d_avg, 'd_nn': d_nn, 'd_hop': d_hop,
        'd_opt_approx': d_opt_approx, 'E_K_uniform': E_K_uniform,
        'E_K_random': E_K_random, 'S_provable': S_provable,
        'S_empirical': S_empirical, 'bound_m1': bound_m1,
        'bound_m2': bound_m2, 'bound_m3': bound_m3,
        'bound_m4': bound_m4_provable, 'bound_m4_tight': bound_m4_empirical,
        'improvement_m4_over_m3': improvement,
    }


# ============================================================
# Simulation Runner
# ============================================================

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
    'model1': '#E91E63',
    'model2': '#2196F3',
    'model3': '#FF9800',
    'model4': '#4CAF50',
}
MODEL_ORDER = ['model1', 'model2', 'model3', 'model4']
MODEL_NUM_MAP = {'1': 'model1', '2': 'model2', '3': 'model3', '4': 'model4'}


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
    _MAP = {
        'finder_crs': 'finder_cr', 'team_crs': 'team_cr',
        'iterations': 'iterations', 'total_dists': 'total_dist',
        'finder_dists': 'finder_dist', 'optimal_dists': 'optimal_dist',
    }
    for key, metric_key in _MAP.items():
        data_dict[key].append(metrics[metric_key])


def _empty_data():
    return {
        'finder_crs': [], 'team_crs': [], 'iterations': [],
        'total_dists': [], 'finder_dists': [], 'optimal_dists': [],
    }


def run_single_model(model_name, n_nodes, n_robots, area_scale, energy,
                     n_trials=200, seed_base=42, verbose=False):
    """Run trials for a single model. Returns results dict."""
    data = _empty_data()
    failed = 0

    for trial in range(n_trials):
        instance = generate_instance(n_nodes, n_robots, area_scale, seed=seed_base + trial)

        if model_name == 'model1':
            result = model1_random_baseline(instance, verbose=verbose and trial == 0)
        elif model_name == 'model2':
            result = model2_infinite_auction(instance, verbose=verbose and trial == 0)
        elif model_name == 'model3':
            result = model3_finite_single(instance, energy, verbose=verbose and trial == 0)
        elif model_name == 'model4':
            result = model4_finite_multi(instance, energy, verbose=verbose and trial == 0)
        else:
            raise ValueError(f"Unknown model: {model_name}")

        metrics = _extract_metrics(result)
        if metrics is not None:
            _append_metrics(data, metrics)
        else:
            failed += 1

    data['meta'] = {
        'model': model_name, 'n_nodes': n_nodes, 'n_robots': n_robots,
        'area_scale': area_scale, 'energy': energy, 'n_trials': n_trials,
        'failed': failed,
    }
    return data


def run_trials(n_nodes, n_robots, area_scale, energy, n_trials=200,
               seed_base=42, models=None):
    """
    Run multiple trials for specified models on the SAME instances.
    If models is None, runs all 4.
    """
    if models is None:
        models = MODEL_ORDER

    results = {mn: _empty_data() for mn in models}
    failed = {mn: 0 for mn in models}

    for trial in range(n_trials):
        instance = generate_instance(n_nodes, n_robots, area_scale, seed=seed_base + trial)

        for mn in models:
            if mn == 'model1':
                r = model1_random_baseline(instance)
            elif mn == 'model2':
                r = model2_infinite_auction(instance)
            elif mn == 'model3':
                r = model3_finite_single(instance, energy)
            elif mn == 'model4':
                r = model4_finite_multi(instance, energy)

            m = _extract_metrics(r)
            if m is not None:
                _append_metrics(results[mn], m)
            else:
                failed[mn] += 1

    results['meta'] = {
        'n_nodes': n_nodes, 'n_robots': n_robots,
        'area_scale': area_scale, 'energy': energy,
        'n_trials': n_trials,
    }
    for mn in models:
        results['meta'][f'failed_{mn}'] = failed[mn]

    return results


def print_summary(results, models=None):
    """Print summary statistics."""
    if models is None:
        models = [mn for mn in MODEL_ORDER if mn in results and mn != 'meta']
    meta = results['meta']
    print("=" * 70)
    print(f"SIMULATION SUMMARY")
    print(f"  Nodes={meta['n_nodes']}, Robots={meta['n_robots']}, "
          f"Area={meta['area_scale']}, Energy={meta['energy']}, "
          f"Trials={meta['n_trials']}")
    print("=" * 70)

    for mn in models:
        data = results[mn]
        if not data['finder_crs']:
            print(f"\n{MODEL_LABELS[mn]}: No successful trials")
            continue

        fcr = data['finder_crs']
        tcr = data['team_crs']
        it = data['iterations']
        failed = meta.get(f'failed_{mn}', 0)

        print(f"\n{MODEL_LABELS[mn]}")
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


# ============================================================
# Plotting Functions
# ============================================================

def plot_results(results, save_dir=None, models=None):
    """Generate comparison plots. Removed redundant distance boxplots (Plot 5)."""
    if models is None:
        models = [mn for mn in MODEL_ORDER if mn in results and mn != 'meta']

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    # --- Plot 1: Finder CR Histograms ---
    n_models = len(models)
    fig, axes = plt.subplots(1, n_models, figsize=(4.5 * n_models, 4), sharey=True)
    if n_models == 1:
        axes = [axes]
    fig.suptitle('Distribution of Finder Competitive Ratios', fontsize=13)

    for ax, mn in zip(axes, models):
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

    # --- Plot 2: Box Plot — Finder CR and Team CR ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, cr_key, title in [
        (axes[0], 'finder_crs', 'Finder Competitive Ratio (Primary)'),
        (axes[1], 'team_crs', 'Team Competitive Ratio (Secondary)'),
    ]:
        box_data, box_labels, box_colors = [], [], []
        for mn in models:
            data = results[mn][cr_key]
            if data:
                box_data.append(data)
                box_labels.append(MODEL_LABELS_SHORT[mn].split('(')[1].rstrip(')'))
                box_colors.append(MODEL_COLORS[mn])

        if box_data:
            bp = ax.boxplot(box_data, tick_labels=box_labels, patch_artist=True,
                            showfliers=False)
            for patch, color in zip(bp['boxes'], box_colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
            for i, data in enumerate(box_data):
                ax.scatter(i + 1, np.mean(data), color='red', marker='D', s=40, zorder=5)

        ax.set_ylabel('Competitive Ratio')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'cr_boxplots.png'), dpi=150, bbox_inches='tight')
    plt.show()

    # --- Plot 3: Iterations vs Finder CR ---
    fig, ax = plt.subplots(figsize=(8, 5))
    for mn in models:
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
    for mn in models:
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


# ============================================================
# Parameter Sweeps
# ============================================================

def sweep_energy(n_nodes, n_robots, area_scale, energy_values, n_trials=100, seed_base=42):
    """Sweep over energy values."""
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
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    energy_vals = sorted(sweep_results.keys())

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

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
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    robot_vals = sorted(sweep_results.keys())

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

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
# Bounds Verification
# ============================================================

def verify_bounds(n_nodes, n_robots, area_scale, energy, n_trials=500, seed_base=42):
    """Run simulations and verify theoretical bounds hold."""
    print("=" * 70)
    print(f"THEORETICAL BOUNDS VERIFICATION")
    print(f"  n={n_nodes}, R={n_robots}, L={area_scale}, E={energy}, Trials={n_trials}")
    print("=" * 70)

    bounds = compute_theoretical_bounds(n_nodes, n_robots, area_scale, energy)

    print(f"\nIntermediate quantities:")
    print(f"  d_avg  = {bounds['d_avg']:.3f}")
    print(f"  d_nn   = {bounds['d_nn']:.3f}")
    print(f"  d_hop  = {bounds['d_hop']:.3f}")
    print(f"  d_opt  = {bounds['d_opt_approx']:.3f}")
    print(f"  E[K] (uniform)  = {bounds['E_K_uniform']:.3f}")
    print(f"  E[K] (random)   = {bounds['E_K_random']:.3f}")
    print(f"  S (provable)    = {bounds['S_provable']:.2f}")
    print(f"  S (empirical)   = {bounds['S_empirical']:.2f}")

    results = run_trials(n_nodes, n_robots, area_scale, energy, n_trials, seed_base)

    print(f"\n{'Model':<16} {'Empirical FCR':>14} {'Theo. Bound':>12} {'Holds?':>8} {'Tightness':>10}")
    print("-" * 65)

    for mn, bound_key, label in [
        ('model1', 'bound_m1', 'M1 Random'),
        ('model2', 'bound_m2', 'M2 Auction'),
        ('model3', 'bound_m3', 'M3 Single'),
        ('model4', 'bound_m4', 'M4 (provable)'),
        ('model4', 'bound_m4_tight', 'M4 (empirical)'),
    ]:
        fcr = results[mn]['finder_crs']
        if fcr:
            emp = np.mean(fcr)
            bnd = bounds[bound_key]
            holds = "✓ YES" if emp <= bnd else "✗ NO"
            tightness = f"{emp/bnd:.3f}" if bnd > 0 else "N/A"
            print(f"{label:<16} {emp:>14.3f} {bnd:>12.3f} {holds:>8} {tightness:>10}")

    print(f"\nModel 4 improvement over Model 3 (bound): {bounds['improvement_m4_over_m3']:.2f}x")
    return results, bounds


# ============================================================
# CLI Argument Parser
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        description='Multi-Robot Search & Rescue Simulation Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                 Run all models with defaults
  %(prog)s --model 1 --verbose             Test Model 1, verbose first trial
  %(prog)s --model 3 4 --trials 500        Compare Models 3 & 4
  %(prog)s --model 4 --verbose --trials 1  Single verbose run of Model 4
  %(prog)s --sweep energy                  Energy parameter sweep
  %(prog)s --sweep robots                  Robot count sweep
  %(prog)s --verify-bounds                 Verify theoretical bounds
  %(prog)s --no-plots                      Run without generating plots
        """
    )

    # Model selection
    parser.add_argument(
        '--model', '-m', type=int, nargs='+', choices=[1, 2, 3, 4],
        help='Which model(s) to run (1-4). Default: all.'
    )

    # Instance parameters
    parser.add_argument('--nodes', '-n', type=int, default=30,
                        help='Number of search nodes (default: 30)')
    parser.add_argument('--robots', '-r', type=int, default=3,
                        help='Number of robots (default: 3)')
    parser.add_argument('--area', '-a', type=float, default=10.0,
                        help='Area scale [0, L]^2 (default: 10)')
    parser.add_argument('--energy', '-e', type=float, default=14.0,
                        help='Energy budget for finite models (default: 14)')
    parser.add_argument('--trials', '-t', type=int, default=500,
                        help='Number of trials (default: 500)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Base random seed (default: 42)')

    # Modes
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output for first trial (step-by-step)')
    parser.add_argument('--sweep', choices=['energy', 'robots'],
                        help='Run a parameter sweep instead of fixed trials')
    parser.add_argument('--verify-bounds', action='store_true',
                        help='Run theoretical bounds verification')

    # Sweep parameters
    parser.add_argument('--energy-values', type=float, nargs='+',
                        default=[8, 10, 12, 14, 16, 18, 20, 25, 30],
                        help='Energy values for sweep (default: 8 10 12 ... 30)')
    parser.add_argument('--robot-values', type=int, nargs='+',
                        default=[1, 2, 3, 4, 5, 6],
                        help='Robot counts for sweep (default: 1 2 3 4 5 6)')

    # Output
    parser.add_argument('--save-dir', type=str, default='figures',
                        help='Directory to save plots (default: figures)')
    parser.add_argument('--no-plots', action='store_true',
                        help='Skip plot generation')

    return parser


# ============================================================
# Main
# ============================================================

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Resolve which models to run
    if args.model:
        models = [f'model{m}' for m in args.model]
    else:
        models = MODEL_ORDER

    save_dir = args.save_dir if not args.no_plots else None

    print("=" * 70)
    print("Multi-Robot Search & Rescue Simulation Framework")
    print("=" * 70)

    # --- Mode: Verify Bounds ---
    if args.verify_bounds:
        verify_bounds(args.nodes, args.robots, args.area, args.energy,
                      n_trials=args.trials, seed_base=args.seed)
        return

    # --- Mode: Parameter Sweep ---
    if args.sweep == 'energy':
        print(f"\nEnergy Sweep: nodes={args.nodes}, robots={args.robots}, "
              f"area={args.area}")
        print(f"  Energy values: {args.energy_values}")
        sweep = sweep_energy(args.nodes, args.robots, args.area,
                             args.energy_values, n_trials=args.trials,
                             seed_base=args.seed)
        if not args.no_plots:
            plot_energy_sweep(sweep, save_dir=save_dir)
        return

    if args.sweep == 'robots':
        print(f"\nRobot Sweep: nodes={args.nodes}, energy={args.energy}, "
              f"area={args.area}")
        print(f"  Robot values: {args.robot_values}")
        sweep = sweep_robots(args.nodes, args.robot_values, args.area,
                             args.energy, n_trials=args.trials,
                             seed_base=args.seed)
        if not args.no_plots:
            plot_robot_sweep(sweep, save_dir=save_dir)
        return

    # --- Mode: Verbose single-model test ---
    if args.verbose and len(models) == 1:
        mn = models[0]
        print(f"\nVerbose test of {MODEL_LABELS[mn]}:")
        print(f"  nodes={args.nodes}, robots={args.robots}, area={args.area}, "
              f"energy={args.energy}")

        if args.trials == 1:
            # Single verbose run
            instance = generate_instance(args.nodes, args.robots, args.area,
                                         seed=args.seed)
            print(f"\n  Target: Node {instance['target']}")
            print(f"  Optimal dist: {instance['optimal_dist']:.3f}")

            if mn == 'model1':
                result = model1_random_baseline(instance, verbose=True)
            elif mn == 'model2':
                result = model2_infinite_auction(instance, verbose=True)
            elif mn == 'model3':
                result = model3_finite_single(instance, args.energy, verbose=True)
            elif mn == 'model4':
                result = model4_finite_multi(instance, args.energy, verbose=True)
            return

        # Multiple trials, verbose on first
        print(f"  Running {args.trials} trials (verbose on trial 1)...\n")
        data = run_single_model(mn, args.nodes, args.robots, args.area,
                                args.energy, args.trials, args.seed,
                                verbose=True)
        # Print summary manually
        if data['finder_crs']:
            fcr = data['finder_crs']
            print(f"\n{'='*50}")
            print(f"Results for {MODEL_LABELS[mn]}:")
            print(f"  Trials: {len(fcr)}/{args.trials}"
                  f" ({data['meta']['failed']} failed)" if data['meta']['failed'] else "")
            print(f"  Finder CR: mean={np.mean(fcr):.3f}, "
                  f"median={np.median(fcr):.3f}, std={np.std(fcr):.3f}")
        return

    # --- Mode: Standard multi-model comparison ---
    print(f"\nRunning {args.trials} trials: nodes={args.nodes}, robots={args.robots}, "
          f"area={args.area}, energy={args.energy}")
    print(f"Models: {', '.join(MODEL_LABELS_SHORT[m] for m in models)}")

    results = run_trials(args.nodes, args.robots, args.area, args.energy,
                         args.trials, args.seed, models=models)
    print_summary(results, models=models)

    if not args.no_plots:
        print("\nGenerating plots...")
        plot_results(results, save_dir=save_dir, models=models)


if __name__ == '__main__':
    main()