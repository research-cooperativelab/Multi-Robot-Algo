import { useEffect, useRef } from 'react'
import type { InstanceData, RoundState } from './types'

interface Props {
  instance: InstanceData
  round: RoundState | null
  stepIndex: number        // 0-based; -1 = initial (no round played yet)
  showTarget: boolean
  size?: number            // canvas pixel size (default 600)
}

// ── colour palette ─────────────────────────────────────────────────────────────
const ROBOT_COLORS = [
  '#f97316', // orange
  '#22d3ee', // cyan
  '#a78bfa', // violet
  '#34d399', // emerald
  '#fb7185', // rose
  '#fbbf24', // amber
  '#60a5fa', // sky-blue
  '#e879f9', // fuchsia
]

const DEFAULT_SIZE  = 580
const MARGIN        = 48

// ── helpers ────────────────────────────────────────────────────────────────────
function probColor(p: number): string {
  // low prob → muted blue, high prob → vivid indigo/violet
  const t   = Math.pow(Math.max(0, Math.min(1, p)), 0.4)
  const r   = Math.round(30  + t * 100)
  const g   = Math.round(100 + t * 20)
  const b   = Math.round(220 - t * 30)
  const a   = 0.25 + t * 0.75
  return `rgba(${r},${g},${b},${a})`
}

function probRadius(p: number): number {
  return 4 + 18 * Math.sqrt(Math.max(0, p))
}

function drawArrow(
  ctx: CanvasRenderingContext2D,
  x1: number, y1: number,
  x2: number, y2: number,
  headLen = 10,
) {
  const angle = Math.atan2(y2 - y1, x2 - x1)
  ctx.beginPath()
  ctx.moveTo(x1, y1)
  ctx.lineTo(x2, y2)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(x2, y2)
  ctx.lineTo(
    x2 - headLen * Math.cos(angle - Math.PI / 7),
    y2 - headLen * Math.sin(angle - Math.PI / 7),
  )
  ctx.lineTo(
    x2 - headLen * Math.cos(angle + Math.PI / 7),
    y2 - headLen * Math.sin(angle + Math.PI / 7),
  )
  ctx.closePath()
  ctx.fill()
}

function drawX(
  ctx: CanvasRenderingContext2D,
  cx: number, cy: number, size: number,
) {
  const h = size * 0.6
  ctx.beginPath()
  ctx.moveTo(cx - h, cy - h); ctx.lineTo(cx + h, cy + h)
  ctx.moveTo(cx + h, cy - h); ctx.lineTo(cx - h, cy + h)
  ctx.stroke()
}

function drawStar(
  ctx: CanvasRenderingContext2D,
  cx: number, cy: number, r: number, color: string,
) {
  const spikes = 5
  const inner  = r * 0.45
  ctx.beginPath()
  for (let i = 0; i < spikes * 2; i++) {
    const angle  = (i * Math.PI) / spikes - Math.PI / 2
    const radius = i % 2 === 0 ? r : inner
    const x = cx + Math.cos(angle) * radius
    const y = cy + Math.sin(angle) * radius
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  }
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
  ctx.strokeStyle = '#fff'
  ctx.lineWidth   = 1.5
  ctx.stroke()
}

// ── main component ─────────────────────────────────────────────────────────────
export default function SimCanvas({ instance, round, stepIndex, showTarget, size = DEFAULT_SIZE }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const CANVAS_SIZE = size
  const DRAW_AREA   = CANVAS_SIZE - MARGIN * 2

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const scale = DRAW_AREA / instance.area_scale
    const tx    = (x: number) => MARGIN + x * scale
    const ty    = (y: number) => CANVAS_SIZE - MARGIN - y * scale

    // Determine current probs, visited sets
    const probs: Record<number, number> = {}
    if (round) {
      for (const [k, v] of Object.entries(round.probs_before)) {
        probs[parseInt(k)] = v
      }
    } else {
      for (const n of instance.nodes) probs[n.id] = n.prob
    }

    const allVisited      = new Set<number>(round?.all_visited ?? [])
    const thisRoundVisited = new Set<number>(round?.visited_this_round ?? [])

    // ── clear ──────────────────────────────────────────────────────────────────
    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

    // background
    ctx.fillStyle = '#0f1117'
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

    // subtle grid
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'
    ctx.lineWidth   = 1
    const gridStep  = scale
    for (let i = 0; i <= instance.area_scale; i++) {
      ctx.beginPath()
      ctx.moveTo(tx(i), MARGIN)
      ctx.lineTo(tx(i), CANVAS_SIZE - MARGIN)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(MARGIN, ty(i))
      ctx.lineTo(CANVAS_SIZE - MARGIN, ty(i))
      ctx.stroke()
    }
    void gridStep  // suppress unused

    // ── tour paths ─────────────────────────────────────────────────────────────
    if (round) {
      for (const [rIdStr, tour] of Object.entries(round.robot_tours)) {
        if (!tour || tour.length === 0) continue
        const rId    = parseInt(rIdStr)
        const color  = ROBOT_COLORS[rId % ROBOT_COLORS.length]
        const base   = instance.bases[rId]
        if (!base) continue

        ctx.strokeStyle = color
        ctx.fillStyle   = color
        ctx.lineWidth   = 2
        ctx.setLineDash([6, 4])
        ctx.globalAlpha = 0.75

        // base → first node
        const firstNode = instance.nodes.find(n => n.id === tour[0])
        if (firstNode) {
          drawArrow(ctx, tx(base.x), ty(base.y), tx(firstNode.x), ty(firstNode.y))
        }

        // node → node (M4 chains)
        for (let i = 0; i < tour.length - 1; i++) {
          const from = instance.nodes.find(n => n.id === tour[i])
          const to   = instance.nodes.find(n => n.id === tour[i + 1])
          if (from && to) {
            drawArrow(ctx, tx(from.x), ty(from.y), tx(to.x), ty(to.y))
          }
        }

        // last node → base (return trip, except if target found in this round by this robot)
        const targetInTour = tour.includes(instance.target) && round.target_found && round.finder === rId
        if (!targetInTour) {
          const lastNode = instance.nodes.find(n => n.id === tour[tour.length - 1])
          if (lastNode) {
            ctx.setLineDash([3, 6])
            ctx.globalAlpha = 0.35
            drawArrow(ctx, tx(lastNode.x), ty(lastNode.y), tx(base.x), ty(base.y))
          }
        }

        ctx.setLineDash([])
        ctx.globalAlpha = 1
      }
    }

    // ── nodes ──────────────────────────────────────────────────────────────────
    for (const node of instance.nodes) {
      const cx = tx(node.x)
      const cy = ty(node.y)
      const p  = probs[node.id] ?? 0
      const r  = probRadius(p)
      const isVisited      = allVisited.has(node.id)
      const isJustVisited  = thisRoundVisited.has(node.id)
      const isTarget       = node.id === instance.target

      if (isTarget && showTarget && round?.target_found) {
        // draw star when found
        drawStar(ctx, cx, cy, r + 6, '#fde047')
        continue
      }

      if (isVisited) {
        // greyed-out visited circle
        ctx.beginPath()
        ctx.arc(cx, cy, Math.max(5, r * 0.6), 0, Math.PI * 2)
        ctx.fillStyle   = isJustVisited ? 'rgba(120,120,180,0.5)' : 'rgba(80,80,100,0.35)'
        ctx.fill()
        ctx.strokeStyle = isJustVisited ? 'rgba(160,160,220,0.8)' : 'rgba(100,100,130,0.5)'
        ctx.lineWidth   = 1
        ctx.stroke()
        // X mark
        ctx.strokeStyle = isJustVisited ? 'rgba(200,200,255,0.9)' : 'rgba(120,120,150,0.7)'
        ctx.lineWidth   = isJustVisited ? 2 : 1.5
        drawX(ctx, cx, cy, Math.max(4, r * 0.5))
      } else {
        // probability circle
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.fillStyle   = probColor(p)
        ctx.fill()
        ctx.strokeStyle = `rgba(150,180,255,${0.3 + p * 0.5})`
        ctx.lineWidth   = 1.5
        ctx.stroke()

        // node ID label for larger nodes
        if (r > 9) {
          ctx.fillStyle  = 'rgba(255,255,255,0.6)'
          ctx.font       = `${Math.round(8 + r * 0.25)}px monospace`
          ctx.textAlign  = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(String(node.id), cx, cy)
        }
      }
    }

    // hidden target marker (show '?' before found)
    if (!round?.target_found && !showTarget) {
      const tgt = instance.nodes.find(n => n.id === instance.target)
      if (tgt && !allVisited.has(tgt.id)) {
        const cx = tx(tgt.x)
        const cy = ty(tgt.y)
        const p  = probs[tgt.id] ?? 0
        const r  = probRadius(p)
        ctx.beginPath()
        ctx.arc(cx, cy, r + 3, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(253,224,71,0.2)'
        ctx.lineWidth   = 2
        ctx.setLineDash([4, 4])
        ctx.stroke()
        ctx.setLineDash([])
      }
    }

    // ── bases ──────────────────────────────────────────────────────────────────
    for (const base of instance.bases) {
      const bx    = tx(base.x)
      const by    = ty(base.y)
      const color = ROBOT_COLORS[base.id % ROBOT_COLORS.length]
      const size  = 10

      ctx.fillStyle   = color
      ctx.strokeStyle = '#fff'
      ctx.lineWidth   = 2
      ctx.beginPath()
      ctx.moveTo(bx,          by - size)
      ctx.lineTo(bx + size,   by + size)
      ctx.lineTo(bx - size,   by + size)
      ctx.closePath()
      ctx.fill()
      ctx.stroke()

      // robot index label
      ctx.fillStyle    = '#fff'
      ctx.font         = '10px monospace'
      ctx.textAlign    = 'center'
      ctx.textBaseline = 'bottom'
      ctx.fillText(`R${base.id}`, bx, by - size - 3)
    }

    // ── legend ─────────────────────────────────────────────────────────────────
    const lx = MARGIN
    let   ly = 14
    ctx.font      = '11px monospace'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'middle'

    const legendItems = [
      { color: 'rgba(60,120,220,0.7)',  label: 'Unvisited node (size ∝ prob)' },
      { color: 'rgba(80,80,100,0.5)',   label: 'Visited node' },
      { color: '#fde047',               label: 'Target found ★' },
    ]
    for (const item of legendItems) {
      ctx.fillStyle = item.color
      ctx.fillRect(lx, ly - 5, 12, 10)
      ctx.fillStyle = 'rgba(255,255,255,0.55)'
      ctx.fillText(item.label, lx + 16, ly)
      ly += 16
    }
  }, [instance, round, stepIndex, showTarget])

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      style={{ borderRadius: 8, display: 'block', maxWidth: '100%' }}
    />
  )
}
