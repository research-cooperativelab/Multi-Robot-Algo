export interface NodeInfo {
  id: number
  x: number
  y: number
  prob: number
}

export interface BaseInfo {
  id: number
  x: number
  y: number
}

export interface InstanceData {
  nodes: NodeInfo[]
  bases: BaseInfo[]
  target: number
  area_scale: number
  optimal_dist: number
}

export interface RoundState {
  round: number
  probs_before: Record<string, number>
  robot_tours: Record<string, number[]>       // robotId → [nodeId, ...]
  robot_positions?: Record<string, [number, number]>  // M2 only
  visited_this_round: number[]
  all_visited: number[]
  target_found: boolean
  finder: number | null
  fcr: number | null
  robot_total_dist: Record<string, number>
}

export interface SimResult {
  model: string
  instance: InstanceData
  rounds: RoundState[]
  found: boolean
  final_fcr: number | null
  total_iterations: number
}

export interface SimParams {
  n_nodes: number
  n_robots: number
  energy: number
  area_scale: number
  seed: number
  model: 'M1' | 'M2' | 'M3' | 'M4' | 'M4*'
}
