import { useEffect, useRef, useCallback } from 'react'
import type { InstanceData, RoundState } from './types'

interface Props {
  instance: InstanceData
  round: RoundState | null
  stepIndex: number        // 0-based; -1 = initial (no round played yet)
  showTarget: boolean
  size?: number            // canvas pixel size (default 600)
  animDuration?: number    // ms for travel animation (default 1200)
  onHover?: (nodeId: number | null) => void
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

const DEFAULT_SIZE      = 580
const MARGIN            = 48
const DEFAULT_ANIM_MS   = 1200
const PULSE_DURATION    = 800   // ms for target-found pulse

// ── lerp helper ───────────────────────────────────────────────────────────────
function lerp(a: number, b: number, t: number) { return a + (b - a) * t }

// ── easing ────────────────────────────────────────────────────────────────────
function easeInOut(t: number) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t }

// ── colour helpers ─────────────────────────────────────────────────────────────
function probColor(p: number): string {
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

// ── drawing helpers ────────────────────────────────────────────────────────────
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

function drawArrowPartial(
  ctx: CanvasRenderingContext2D,
  x1: number, y1: number,
  x2: number, y2: number,
  progress: number,   // 0–1, how far to draw
  headLen = 10,
) {
  if (progress <= 0) return
  const ex = lerp(x1, x2, progress)
  const ey = lerp(y1, y2, progress)
  const angle = Math.atan2(y2 - y1, x2 - x1)
  ctx.beginPath()
  ctx.moveTo(x1, y1)
  ctx.lineTo(ex, ey)
  ctx.stroke()
  if (progress >= 0.8) {
    const fade = (progress - 0.8) / 0.2
    ctx.save()
    ctx.globalAlpha = ctx.globalAlpha * fade
    ctx.beginPath()
    ctx.moveTo(ex, ey)
    ctx.lineTo(
      ex - headLen * Math.cos(angle - Math.PI / 7),
      ey - headLen * Math.sin(angle - Math.PI / 7),
    )
    ctx.lineTo(
      ex - headLen * Math.cos(angle + Math.PI / 7),
      ey - headLen * Math.sin(angle + Math.PI / 7),
    )
    ctx.closePath()
    ctx.fill()
    ctx.restore()
  }
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
  scale = 1,
) {
  const spikes = 5
  const inner  = r * 0.45
  ctx.save()
  ctx.translate(cx, cy)
  ctx.scale(scale, scale)
  ctx.beginPath()
  for (let i = 0; i < spikes * 2; i++) {
    const angle  = (i * Math.PI) / spikes - Math.PI / 2
    const radius = i % 2 === 0 ? r : inner
    const x = Math.cos(angle) * radius
    const y = Math.sin(angle) * radius
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  }
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
  ctx.strokeStyle = '#fff'
  ctx.lineWidth   = 1.5
  ctx.stroke()
  ctx.restore()
}

// ── build robot path segments for a single robot ──────────────────────────────
interface Segment { x1: number; y1: number; x2: number; y2: number; isReturn: boolean }

function buildSegments(
  rId: number,
  tour: number[],
  instance: InstanceData,
  tx: (x: number) => number,
  ty: (y: number) => number,
): Segment[] {
  const base = instance.bases[rId]
  if (!base || tour.length === 0) return []
  const segments: Segment[] = []
  const nodeMap = new Map(instance.nodes.map(n => [n.id, n]))

  const bx = tx(base.x)
  const by = ty(base.y)

  // base → first node
  const first = nodeMap.get(tour[0])
  if (first) segments.push({ x1: bx, y1: by, x2: tx(first.x), y2: ty(first.y), isReturn: false })

  // node → node
  for (let i = 0; i < tour.length - 1; i++) {
    const from = nodeMap.get(tour[i])
    const to   = nodeMap.get(tour[i + 1])
    if (from && to) {
      segments.push({ x1: tx(from.x), y1: ty(from.y), x2: tx(to.x), y2: ty(to.y), isReturn: false })
    }
  }

  // return trip (last node → base)
  const last = nodeMap.get(tour[tour.length - 1])
  if (last) segments.push({ x1: tx(last.x), y1: ty(last.y), x2: bx, y2: by, isReturn: true })

  return segments
}

// ── get robot position at animation progress t (0→1) ─────────────────────────
function robotPosAtT(segments: Segment[], t: number): { x: number; y: number } | null {
  if (segments.length === 0) return null
  const segT = t * segments.length
  const segIdx = Math.min(Math.floor(segT), segments.length - 1)
  const segProgress = segT - segIdx
  const seg = segments[segIdx]
  return { x: lerp(seg.x1, seg.x2, segProgress), y: lerp(seg.y1, seg.y2, segProgress) }
}

// ── draw tooltip ──────────────────────────────────────────────────────────────
function drawTooltip(
  ctx: CanvasRenderingContext2D,
  mx: number, my: number,
  lines: string[],
  canvasSize: number,
) {
  const padding  = 10
  const lineH    = 16
  const fontSize = 11
  const width    = 180
  const height   = padding * 2 + lines.length * lineH

  // keep tooltip inside canvas
  let tx = mx + 14
  let ty = my - height / 2
  if (tx + width > canvasSize - 4) tx = mx - width - 14
  if (ty < 4) ty = 4
  if (ty + height > canvasSize - 4) ty = canvasSize - height - 4

  // backdrop
  ctx.save()
  ctx.shadowColor = 'rgba(0,0,0,0.6)'
  ctx.shadowBlur  = 12
  ctx.fillStyle   = 'rgba(10,14,24,0.92)'
  const r = 7
  ctx.beginPath()
  ctx.moveTo(tx + r, ty)
  ctx.lineTo(tx + width - r, ty)
  ctx.quadraticCurveTo(tx + width, ty, tx + width, ty + r)
  ctx.lineTo(tx + width, ty + height - r)
  ctx.quadraticCurveTo(tx + width, ty + height, tx + width - r, ty + height)
  ctx.lineTo(tx + r, ty + height)
  ctx.quadraticCurveTo(tx, ty + height, tx, ty + height - r)
  ctx.lineTo(tx, ty + r)
  ctx.quadraticCurveTo(tx, ty, tx + r, ty)
  ctx.closePath()
  ctx.fill()
  ctx.shadowBlur = 0
  ctx.strokeStyle = 'rgba(100,130,200,0.3)'
  ctx.lineWidth   = 1
  ctx.stroke()
  ctx.restore()

  // text lines
  ctx.font         = `${fontSize}px monospace`
  ctx.textBaseline = 'top'
  ctx.textAlign    = 'left'
  for (let i = 0; i < lines.length; i++) {
    ctx.fillStyle = i === 0 ? '#e2e8f0' : '#94a3b8'
    ctx.fillText(lines[i], tx + padding, ty + padding + i * lineH)
  }
}

// ── main component ─────────────────────────────────────────────────────────────
export default function SimCanvas({
  instance, round, stepIndex, showTarget,
  size = DEFAULT_SIZE, animDuration = DEFAULT_ANIM_MS, onHover,
}: Props) {
  const canvasRef   = useRef<HTMLCanvasElement>(null)
  const animRef     = useRef<number | null>(null)
  const animStart   = useRef<number | null>(null)
  const prevStep    = useRef<number>(-999)
  const hoverNode   = useRef<number | null>(null)
  const mousePos    = useRef<{ x: number; y: number } | null>(null)
  const pulseStart  = useRef<number | null>(null)
  const pulsing     = useRef(false)
  const prevFoundRef = useRef(false)

  const CANVAS_SIZE = size
  const DRAW_AREA   = CANVAS_SIZE - MARGIN * 2

  // ── core draw function ───────────────────────────────────────────────────────
  const draw = useCallback((animProgress: number, pulseProgress: number | null) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const scale = DRAW_AREA / instance.area_scale
    const txFn  = (x: number) => MARGIN + x * scale
    const tyFn  = (y: number) => CANVAS_SIZE - MARGIN - y * scale

    // Determine current probs, visited sets
    const probs: Record<number, number> = {}
    if (round) {
      for (const [k, v] of Object.entries(round.probs_before)) {
        probs[parseInt(k)] = v
      }
    } else {
      for (const n of instance.nodes) probs[n.id] = n.prob
    }

    const allVisited       = new Set<number>(round?.all_visited ?? [])
    const thisRoundVisited = new Set<number>(round?.visited_this_round ?? [])

    // ── clear + background ───────────────────────────────────────────────────
    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)
    ctx.fillStyle = '#0f1117'
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

    // subtle grid
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'
    ctx.lineWidth   = 1
    for (let i = 0; i <= instance.area_scale; i++) {
      ctx.beginPath()
      ctx.moveTo(txFn(i), MARGIN)
      ctx.lineTo(txFn(i), CANVAS_SIZE - MARGIN)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(MARGIN, tyFn(i))
      ctx.lineTo(CANVAS_SIZE - MARGIN, tyFn(i))
      ctx.stroke()
    }

    // ── tour paths (animated draw) ───────────────────────────────────────────
    if (round) {
      for (const [rIdStr, tour] of Object.entries(round.robot_tours)) {
        if (!tour || tour.length === 0) continue
        const rId    = parseInt(rIdStr)
        const color  = ROBOT_COLORS[rId % ROBOT_COLORS.length]
        const base   = instance.bases[rId]
        if (!base) continue

        const segments = buildSegments(rId, tour, instance, txFn, tyFn)
        const totalSegs = segments.length
        if (totalSegs === 0) continue

        // each segment draws in proportion to animation progress
        const pathT = animProgress  // 0→1 means we've drawn this fraction of path
        const drawnSegs = pathT * totalSegs

        ctx.strokeStyle = color
        ctx.fillStyle   = color
        ctx.lineWidth   = 2

        for (let si = 0; si < totalSegs; si++) {
          const seg = segments[si]
          const segDrawn = Math.max(0, Math.min(1, drawnSegs - si))
          if (segDrawn <= 0) continue

          if (seg.isReturn) {
            ctx.setLineDash([3, 6])
            ctx.globalAlpha = 0.35
          } else {
            ctx.setLineDash([6, 4])
            ctx.globalAlpha = 0.75
          }

          drawArrowPartial(ctx, seg.x1, seg.y1, seg.x2, seg.y2, segDrawn)
        }

        ctx.setLineDash([])
        ctx.globalAlpha = 1
      }
    }

    // ── nodes ────────────────────────────────────────────────────────────────
    for (const node of instance.nodes) {
      const cx = txFn(node.x)
      const cy = tyFn(node.y)
      const p  = probs[node.id] ?? 0
      const r  = probRadius(p)
      const isVisited      = allVisited.has(node.id)
      const isJustVisited  = thisRoundVisited.has(node.id)
      const isTarget       = node.id === instance.target
      const isHovered      = hoverNode.current === node.id

      // hover ring highlight
      if (isHovered) {
        ctx.save()
        ctx.beginPath()
        ctx.arc(cx, cy, r + 6, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(255,255,255,0.25)'
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.restore()
      }

      if (isTarget && showTarget && round?.target_found) {
        // pulsing star when found
        const starScale = pulseProgress !== null
          ? lerp(0.5, 1.3, easeInOut(pulseProgress))
          : 1.0
        // glow
        ctx.save()
        ctx.shadowColor = '#fde04788'
        ctx.shadowBlur  = 20 + (pulseProgress ?? 0) * 15
        drawStar(ctx, cx, cy, r + 6, '#fde047', starScale)
        ctx.restore()
        continue
      }

      if (isVisited) {
        ctx.beginPath()
        ctx.arc(cx, cy, Math.max(5, r * 0.6), 0, Math.PI * 2)
        ctx.fillStyle   = isJustVisited ? 'rgba(120,120,180,0.5)' : 'rgba(80,80,100,0.35)'
        ctx.fill()
        ctx.strokeStyle = isJustVisited ? 'rgba(160,160,220,0.8)' : 'rgba(100,100,130,0.5)'
        ctx.lineWidth   = 1
        ctx.stroke()
        ctx.strokeStyle = isJustVisited ? 'rgba(200,200,255,0.9)' : 'rgba(120,120,150,0.7)'
        ctx.lineWidth   = isJustVisited ? 2 : 1.5
        drawX(ctx, cx, cy, Math.max(4, r * 0.5))
      } else {
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.fillStyle   = probColor(p)
        ctx.fill()
        ctx.strokeStyle = `rgba(150,180,255,${0.3 + p * 0.5})`
        ctx.lineWidth   = 1.5
        ctx.stroke()
        if (r > 9) {
          ctx.fillStyle    = 'rgba(255,255,255,0.6)'
          ctx.font         = `${Math.round(8 + r * 0.25)}px monospace`
          ctx.textAlign    = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(String(node.id), cx, cy)
        }
      }
    }

    // hidden target marker (show '?' before found)
    if (!round?.target_found && !showTarget) {
      const tgt = instance.nodes.find(n => n.id === instance.target)
      if (tgt && !allVisited.has(tgt.id)) {
        const cx = txFn(tgt.x)
        const cy = tyFn(tgt.y)
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

    // ── animated robot circles ───────────────────────────────────────────────
    if (round) {
      for (const [rIdStr, tour] of Object.entries(round.robot_tours)) {
        if (!tour || tour.length === 0) continue
        const rId    = parseInt(rIdStr)
        const color  = ROBOT_COLORS[rId % ROBOT_COLORS.length]
        const base   = instance.bases[rId]
        if (!base) continue

        const segments = buildSegments(rId, tour, instance, txFn, tyFn)
        if (segments.length === 0) continue

        const targetInTour =
          tour.includes(instance.target) &&
          round.target_found &&
          round.finder === rId

        // cap robot at last forward segment if finder
        let effectiveT = animProgress
        if (targetInTour) {
          // stop at the target node position (don't return)
          const forwardSegs = segments.filter(s => !s.isReturn).length
          const maxT = forwardSegs / segments.length
          effectiveT = Math.min(animProgress, maxT)
        }

        const pos = robotPosAtT(segments, effectiveT)
        if (!pos) continue

        // glow shadow
        ctx.save()
        ctx.shadowColor = color
        ctx.shadowBlur  = 12

        // filled circle
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, 9, 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()

        // white stroke
        ctx.shadowBlur  = 0
        ctx.strokeStyle = '#fff'
        ctx.lineWidth   = 2
        ctx.stroke()

        ctx.restore()

        // robot index label on circle
        ctx.fillStyle    = '#fff'
        ctx.font         = 'bold 8px monospace'
        ctx.textAlign    = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(`R${rId}`, pos.x, pos.y)
      }
    }

    // ── bases ────────────────────────────────────────────────────────────────
    for (const base of instance.bases) {
      const bx    = txFn(base.x)
      const by    = tyFn(base.y)
      const color = ROBOT_COLORS[base.id % ROBOT_COLORS.length]
      const sz    = 10

      ctx.fillStyle   = color
      ctx.strokeStyle = '#fff'
      ctx.lineWidth   = 2
      ctx.beginPath()
      ctx.moveTo(bx,        by - sz)
      ctx.lineTo(bx + sz,   by + sz)
      ctx.lineTo(bx - sz,   by + sz)
      ctx.closePath()
      ctx.fill()
      ctx.stroke()

      ctx.fillStyle    = '#fff'
      ctx.font         = '10px monospace'
      ctx.textAlign    = 'center'
      ctx.textBaseline = 'bottom'
      ctx.fillText(`R${base.id}`, bx, by - sz - 3)
    }

    // ── legend ───────────────────────────────────────────────────────────────
    const lx = MARGIN
    let   ly = 14
    ctx.font         = '11px monospace'
    ctx.textAlign    = 'left'
    ctx.textBaseline = 'middle'
    const legendItems = [
      { color: 'rgba(60,120,220,0.7)',  label: 'Unvisited node (size \u221d prob)' },
      { color: 'rgba(80,80,100,0.5)',   label: 'Visited node' },
      { color: '#fde047',               label: 'Target found \u2605' },
    ]
    for (const item of legendItems) {
      ctx.fillStyle = item.color
      ctx.fillRect(lx, ly - 5, 12, 10)
      ctx.fillStyle = 'rgba(255,255,255,0.55)'
      ctx.fillText(item.label, lx + 16, ly)
      ly += 16
    }

    // ── hover tooltip ────────────────────────────────────────────────────────
    if (hoverNode.current !== null && mousePos.current) {
      const node = instance.nodes.find(n => n.id === hoverNode.current)
      if (node) {
        const p    = probs[node.id] ?? 0
        const dist = Math.sqrt(
          Math.pow(node.x - (instance.bases[0]?.x ?? 0), 2) +
          Math.pow(node.y - (instance.bases[0]?.y ?? 0), 2)
        )
        const visitedRound = round?.all_visited.includes(node.id)
          ? `round ${round.round}`
          : 'unvisited'
        const lines = [
          `Node #${node.id}`,
          `prob: ${p.toFixed(3)}`,
          `dist from base: ${dist.toFixed(2)}m`,
          `visited: ${visitedRound}`,
        ]
        drawTooltip(ctx, mousePos.current.x, mousePos.current.y, lines, CANVAS_SIZE)
      }
    }
  }, [instance, round, DRAW_AREA, CANVAS_SIZE])

  // ── animation loop ────────────────────────────────────────────────────────
  const startAnim = useCallback(() => {
    if (animRef.current) cancelAnimationFrame(animRef.current)
    animStart.current = null

    const loop = (now: number) => {
      if (animStart.current === null) animStart.current = now
      const elapsed = now - animStart.current

      // robot travel progress
      const t = Math.min(1, elapsed / animDuration)

      // pulse progress (for target found)
      let pulseP: number | null = null
      if (pulsing.current && pulseStart.current !== null) {
        const pe = now - pulseStart.current
        if (pe < PULSE_DURATION) {
          pulseP = pe / PULSE_DURATION
        } else {
          pulsing.current = false
          pulseP = 1
        }
      }

      draw(t, pulseP)

      if (t < 1 || (pulsing.current)) {
        animRef.current = requestAnimationFrame(loop)
      } else {
        draw(1, pulseP)
        animRef.current = null
      }
    }
    animRef.current = requestAnimationFrame(loop)
  }, [draw, animDuration])

  // ── trigger animation when stepIndex changes ──────────────────────────────
  useEffect(() => {
    if (stepIndex !== prevStep.current) {
      prevStep.current = stepIndex

      // check if target was just found this round
      const justFound = round?.target_found && !prevFoundRef.current
      prevFoundRef.current = round?.target_found ?? false

      if (justFound) {
        pulsing.current    = true
        pulseStart.current = performance.now()
      }

      startAnim()
    }
  }, [stepIndex, round, startAnim])

  // ── initial draw (no animation) ───────────────────────────────────────────
  useEffect(() => {
    draw(1, null)
  }, [draw])

  // ── cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current)
    }
  }, [])

  // ── hover / mouse events ──────────────────────────────────────────────────
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width  / rect.width
    const scaleY = canvas.height / rect.height
    const mx = (e.clientX - rect.left) * scaleX
    const my = (e.clientY - rect.top)  * scaleY

    mousePos.current = { x: mx, y: my }

    const scale = DRAW_AREA / instance.area_scale
    const txFn  = (x: number) => MARGIN + x * scale
    const tyFn  = (y: number) => CANVAS_SIZE - MARGIN - y * scale

    let found: number | null = null
    for (const node of instance.nodes) {
      const cx = txFn(node.x)
      const cy = tyFn(node.y)
      const dx = mx - cx
      const dy = my - cy
      const p  = (round
        ? (round.probs_before[String(node.id)] ?? 0)
        : node.prob)
      const r = probRadius(p) + 4
      if (dx * dx + dy * dy <= r * r) {
        found = node.id
        break
      }
    }

    if (found !== hoverNode.current) {
      hoverNode.current = found
      onHover?.(found)
      // redraw immediately to show/hide tooltip
      if (!animRef.current) {
        draw(1, pulsing.current ? 1 : null)
      }
    }
  }, [instance, round, DRAW_AREA, CANVAS_SIZE, draw, onHover])

  const handleMouseLeave = useCallback(() => {
    mousePos.current  = null
    hoverNode.current = null
    onHover?.(null)
    if (!animRef.current) {
      draw(1, pulsing.current ? 1 : null)
    }
  }, [draw, onHover])

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      style={{ borderRadius: 8, display: 'block', maxWidth: '100%', cursor: 'crosshair' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    />
  )
}
