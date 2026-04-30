import { useState, useEffect, useRef, useCallback } from 'react'
import SimCanvas from './SimCanvas'
import type { SimParams, SimResult, RoundState } from './types'
import './App.css'

// ── defaults ───────────────────────────────────────────────────────────────────
const DEFAULT_PARAMS: SimParams = {
  n_nodes:    20,
  n_robots:   3,
  energy:     15,
  area_scale: 10,
  seed:       42,
  model:      'M4*',
}

const MODEL_OPTIONS: SimParams['model'][] = ['M1', 'M2', 'M3', 'M4', 'M4*']

const MODEL_DESC: Record<SimParams['model'], { title: string; text: string }> = {
  M1: {
    title: 'Random — no coordination',
    text: 'Each rescuer picks a spot to search on their own, without talking to the others. They sometimes check the same rubble twice while other areas go unexplored.',
  },
  M2: {
    title: 'Unconstrained-energy auction',
    text: 'The rescuers have unlimited battery and walk straight from one site to the next. Every round they bid against each other to pick who checks what — the team picks the highest-value target first.',
  },
  M3: {
    title: 'Single-node sortie (limited battery)',
    text: 'Each rescuer must return to base to recharge after visiting a single site. Most of each trip is spent on travel to and from base; little budget is left for actual search.',
  },
  M4: {
    title: 'Multi-node sortie with p/d bid',
    text: 'Rescuers chain several sites into a single trip before returning. They pick the next site by weighing probability of the target being there against distance.',
  },
  'M4*': {
    title: 'Multi-node sortie with p/d\u00b2 bid',
    text: 'Same as M4, but the rescuers penalise distance twice as hard. A site twice as far away counts as four times as expensive. This finds survivors faster under tight battery budgets.',
  },
}

// ── bid function badge ─────────────────────────────────────────────────────────
function BidBadge({ model }: { model: SimParams['model'] }) {
  const isOptimal = model === 'M4*'
  const label = model === 'M4*' ? 'p\u2044d\u00b2' : model === 'M4' ? 'p\u2044d' : model
  return (
    <span
      className="bid-badge"
      style={{
        background: isOptimal ? 'rgba(74,222,128,0.15)' : 'rgba(100,116,139,0.15)',
        borderColor: isOptimal ? '#4ade80' : '#475569',
        color: isOptimal ? '#4ade80' : '#94a3b8',
      }}
    >
      {label}
    </span>
  )
}

// ── benchmark model colours ───────────────────────────────────────────────────
const MODEL_COLORS: Record<string, string> = {
  M1:   '#f87171',
  M2:   '#22d3ee',
  M3:   '#fbbf24',
  M4:   '#60a5fa',
  'M4*':'#4ade80',
}

// ── FCR timeline SVG ──────────────────────────────────────────────────────────
const IDEAL_FCR = 2.83
const TL_W = 320
const TL_H = 80
const TL_PAD = { t: 10, r: 12, b: 22, l: 36 }

function FcrTimeline({ rounds }: { rounds: RoundState[] }) {
  const fcrPoints = rounds.map(r => r.fcr).filter((f): f is number => f !== null)
  if (fcrPoints.length === 0) return null

  const maxVal = Math.max(...fcrPoints, IDEAL_FCR, 1)
  const minVal = 0

  const innerW = TL_W - TL_PAD.l - TL_PAD.r
  const innerH = TL_H - TL_PAD.t - TL_PAD.b

  const px = (i: number) => TL_PAD.l + (i / Math.max(fcrPoints.length - 1, 1)) * innerW
  const py = (v: number) => TL_PAD.t + (1 - (v - minVal) / (maxVal - minVal)) * innerH

  const idealY = py(IDEAL_FCR)

  // build polyline path
  const pts = fcrPoints.map((v, i) => `${px(i)},${py(v)}`).join(' ')

  return (
    <div className="fcr-timeline-wrap">
      <div className="fcr-timeline-label">FCR timeline</div>
      <svg width={TL_W} height={TL_H} className="fcr-timeline-svg">
        {/* ideal dashed line */}
        <line
          x1={TL_PAD.l} y1={idealY}
          x2={TL_W - TL_PAD.r} y2={idealY}
          stroke="#60a5fa" strokeWidth={1} strokeDasharray="4 3" opacity={0.5}
        />
        <text x={TL_PAD.l - 3} y={idealY + 4} fill="#60a5fa" fontSize={9} textAnchor="end" opacity={0.7}>
          {IDEAL_FCR}
        </text>

        {/* y-axis tick labels */}
        {[0, Math.round(maxVal)].map(v => (
          <text key={v} x={TL_PAD.l - 3} y={py(v) + 4}
            fill="#475569" fontSize={9} textAnchor="end">{v}</text>
        ))}

        {/* x-axis labels */}
        <text x={TL_PAD.l} y={TL_H - 4} fill="#475569" fontSize={9} textAnchor="middle">1</text>
        {fcrPoints.length > 1 && (
          <text x={TL_W - TL_PAD.r} y={TL_H - 4} fill="#475569" fontSize={9} textAnchor="middle">
            {fcrPoints.length}
          </text>
        )}

        {/* line */}
        {fcrPoints.length > 1 && (
          <polyline
            points={pts}
            fill="none"
            stroke="#6366f1"
            strokeWidth={1.5}
            opacity={0.7}
          />
        )}

        {/* dots */}
        {fcrPoints.map((v, i) => {
          const above = v > IDEAL_FCR
          return (
            <circle key={i}
              cx={px(i)} cy={py(v)} r={3.5}
              fill={above ? '#f87171' : '#4ade80'}
              stroke="rgba(0,0,0,0.4)"
              strokeWidth={1}
            />
          )
        })}
      </svg>
    </div>
  )
}

// ── Entropy timeline SVG ─────────────────────────────────────────────────────
function EntropyTimeline({ rounds }: { rounds: RoundState[] }) {
  const pts = rounds
    .map(r => r.entropy_before)
    .filter((e): e is number => e != null)
  if (pts.length < 2) return null

  const maxVal = pts[0]   // entropy starts high
  const minVal = 0
  const innerW = TL_W - TL_PAD.l - TL_PAD.r
  const innerH = TL_H - TL_PAD.t - TL_PAD.b
  const px = (i: number) => TL_PAD.l + (i / Math.max(pts.length - 1, 1)) * innerW
  const py = (v: number) => TL_PAD.t + (1 - (v - minVal) / Math.max(maxVal - minVal, 0.01)) * innerH
  const polyPts = pts.map((v, i) => `${px(i)},${py(v)}`).join(' ')

  return (
    <div className="fcr-timeline-wrap">
      <div className="fcr-timeline-label">Entropy (bits) — Bayesian belief collapse</div>
      <svg width={TL_W} height={TL_H} className="fcr-timeline-svg">
        {[0, Math.round(maxVal * 10) / 10].map(v => (
          <text key={v} x={TL_PAD.l - 3} y={py(v) + 4}
            fill="#475569" fontSize={9} textAnchor="end">{v.toFixed(1)}</text>
        ))}
        <text x={TL_PAD.l} y={TL_H - 4} fill="#475569" fontSize={9} textAnchor="middle">1</text>
        {pts.length > 1 && (
          <text x={TL_W - TL_PAD.r} y={TL_H - 4} fill="#475569" fontSize={9} textAnchor="middle">
            {pts.length}
          </text>
        )}
        <polyline points={polyPts} fill="none" stroke="#a78bfa" strokeWidth={1.5} opacity={0.8} />
        {pts.map((v, i) => (
          <circle key={i} cx={px(i)} cy={py(v)} r={3}
            fill="#a78bfa" stroke="rgba(0,0,0,0.4)" strokeWidth={1} />
        ))}
      </svg>
    </div>
  )
}

// ── Benchmark view ────────────────────────────────────────────────────────────
function BenchmarkView({
  results, loading,
}: {
  results: Partial<Record<string, SimResult>>
  loading: boolean
}) {
  const entries = MODEL_OPTIONS
    .map(m => ({ model: m, result: results[m] ?? null }))
    .filter(e => e.result?.final_fcr != null)
    .sort((a, b) => (a.result!.final_fcr ?? 999) - (b.result!.final_fcr ?? 999))

  const maxFcr = Math.max(...entries.map(e => e.result!.final_fcr!), 1)

  if (loading) {
    return (
      <div className="bench-empty">
        <div className="bench-spinner" />
        <p>Running all 5 models on the same instance…</p>
      </div>
    )
  }

  if (entries.length === 0) {
    return (
      <div className="bench-empty">
        <div className="empty-icon">📊</div>
        <p>Set parameters and click <strong>Run Benchmark</strong> to compare all 5 models.</p>
      </div>
    )
  }

  const bestFcr  = entries[0].result!.final_fcr!
  const worstFcr = entries[entries.length - 1].result!.final_fcr!
  const gainPct  = ((worstFcr - bestFcr) / worstFcr * 100).toFixed(1)

  return (
    <div className="bench-view">
      <div className="bench-title">All 5 Models · Same Instance · Sorted by FCR</div>
      <div className="bench-gain-callout">
        Best model wins by <strong>{gainPct}%</strong> over worst
        &nbsp;·&nbsp; {entries[0].model} FCR {bestFcr.toFixed(2)}
        &nbsp;vs&nbsp; {entries[entries.length - 1].model} FCR {worstFcr.toFixed(2)}
      </div>

      <div className="bench-rows">
        {entries.map(({ model, result }, rank) => {
          const fcr    = result!.final_fcr!
          const pct    = (fcr / maxFcr) * 100
          const color  = MODEL_COLORS[model] ?? '#94a3b8'
          const isOptimal = model === 'M4*'
          return (
            <div key={model} className={`bench-row ${isOptimal ? 'optimal' : ''}`}>
              <div className="bench-rank">#{rank + 1}</div>
              <div className="bench-model-name" style={{ color }}>
                {model}
                {isOptimal && <span className="bench-star"> ★</span>}
              </div>
              <div className="bench-bar-wrap">
                <div
                  className="bench-bar"
                  style={{ width: `${pct}%`, background: color }}
                />
              </div>
              <div className="bench-fcr-val">{fcr.toFixed(2)}</div>
              <div className="bench-rounds-val">{result!.total_iterations}r</div>
            </div>
          )
        })}
      </div>

      {/* per-model FCR details */}
      <div className="bench-detail-grid">
        {MODEL_OPTIONS.map(m => {
          const r = results[m]
          return (
            <div key={m} className="bench-detail-cell" style={{ borderColor: MODEL_COLORS[m] ?? '#2d3a50' }}>
              <div className="bench-detail-model" style={{ color: MODEL_COLORS[m] ?? '#94a3b8' }}>{m}</div>
              <div className="bench-detail-fcr">
                {r?.final_fcr != null ? r.final_fcr.toFixed(2) : '—'}
              </div>
              <div className="bench-detail-sub">
                {r ? (r.found ? `✓ found · ${r.total_iterations} rounds` : '✗ not found') : 'pending'}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── round counter display ─────────────────────────────────────────────────────
function RoundCounter({
  round, totalRounds, result,
}: {
  round: RoundState | null
  totalRounds: number
  result: SimResult
}) {
  const targetFoundIdx = result.rounds.findIndex(r => r.target_found)

  if (!round) return null

  const isFound = round.target_found

  return (
    <div className="round-counter-wrap">
      {isFound ? (
        <div className="found-box">
          🎯 Found in round {targetFoundIdx + 1} &mdash; FCR:&nbsp;
          <strong>{round.fcr != null ? round.fcr.toFixed(2) : result.final_fcr?.toFixed(2) ?? '—'}</strong>
        </div>
      ) : (
        <div className="round-counter">
          <span className="round-counter-label">Round</span>
          <span className="round-counter-value">{round.round}&nbsp;/&nbsp;{totalRounds}</span>
          {round.fcr != null && (
            <>
              <span className="round-counter-sep">·</span>
              <span className="round-counter-label">FCR</span>
              <span className="round-counter-fcr">{round.fcr.toFixed(2)}</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ── SliderRow ──────────────────────────────────────────────────────────────────
function SliderRow({
  label, value, min, max, step = 1,
  onChange, format = (v: number) => String(v),
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (v: number) => void
  format?: (v: number) => string
}) {
  return (
    <div className="slider-row">
      <div className="slider-header">
        <span className="slider-label">{label}</span>
        <span className="slider-value">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
      />
    </div>
  )
}

// ── ModelDescription ───────────────────────────────────────────────────────────
function ModelDescription({ model }: { model: SimParams['model'] }) {
  const desc = MODEL_DESC[model]
  return (
    <div className="model-desc-box">
      <div className="model-desc-heading">
        {model} · {desc.title}
        <BidBadge model={model} />
      </div>
      <p className="model-desc-text">{desc.text}</p>
    </div>
  )
}

// ── animation speed options ───────────────────────────────────────────────────
const SPEED_OPTIONS = [
  { label: '0.5×', ms: 2400 },
  { label: '1×',   ms: 1200 },
  { label: '2×',   ms:  600 },
  { label: '4×',   ms:  300 },
]

type AppMode = 'single' | 'compare' | 'benchmark' | 'demo' | 'honors'

// ── Honors Thesis Slide Viewer ────────────────────────────────────────────────
const HONORS_SLIDES = Array.from({ length: 13 }, (_, i) => `/uhp-slides/${String(i + 1).padStart(2, '0')}.png`)

function HonorsSlides() {
  const [cur, setCur] = useState(0)
  const N = HONORS_SLIDES.length

  const go = (n: number) => setCur(Math.max(0, Math.min(N - 1, n)))

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); go(cur + 1) }
      if (e.key === 'ArrowLeft')                   { e.preventDefault(); go(cur - 1) }
      if (e.key === 'Home')                        { e.preventDefault(); go(0) }
      if (e.key === 'End')                         { e.preventDefault(); go(N - 1) }
      if (e.key === 'f' || e.key === 'F') {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen()
        else document.exitFullscreen()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [cur])

  return (
    <div className="honors-wrap">
      {/* slide image */}
      <div className="honors-stage" onClick={() => go(cur + 1)}>
        <img
          key={cur}
          src={HONORS_SLIDES[cur]}
          alt={`Slide ${cur + 1}`}
          className="honors-img"
          draggable={false}
        />
      </div>

      {/* controls */}
      <div className="honors-controls">
        <button className="step-btn" onClick={() => go(0)}           disabled={cur === 0}>First</button>
        <button className="step-btn" onClick={() => go(cur - 1)}     disabled={cur === 0}>Prev</button>
        <span className="honors-counter">{cur + 1} / {N}</span>
        <button className="step-btn play-btn" onClick={() => go(cur + 1)} disabled={cur === N - 1}>Next</button>
        <button className="step-btn" onClick={() => go(N - 1)}       disabled={cur === N - 1}>Last</button>
        <button
          className="step-btn"
          title="Fullscreen (F)"
          onClick={() => {
            if (!document.fullscreenElement) document.documentElement.requestFullscreen()
            else document.exitFullscreen()
          }}
        >⛶ Full</button>
      </div>

      <p className="honors-hint">← → navigate &nbsp;·&nbsp; click slide to advance &nbsp;·&nbsp; F for fullscreen</p>
    </div>
  )
}

const DEMO_MODELS = ['M1', 'M4', 'M4*'] as const
type DemoModel = typeof DEMO_MODELS[number]

// ── App ────────────────────────────────────────────────────────────────────────
export default function App() {
  const [params,    setParams]    = useState<SimParams>(DEFAULT_PARAMS)
  const [result,    setResult]    = useState<SimResult | null>(null)
  const [stepIdx,   setStepIdx]   = useState(0)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [playing,   setPlaying]   = useState(false)
  const [showTgt,   setShowTgt]   = useState(false)
  const [animMs,    setAnimMs]    = useState(1200)
  const [appMode,   setAppMode]   = useState<AppMode>('single')
  const playRef   = useRef<ReturnType<typeof setInterval> | null>(null)
  const shellRef  = useRef<HTMLDivElement>(null)

  // derived booleans for existing code
  const compareMode = appMode === 'compare'
  const benchMode   = appMode === 'benchmark'

  // ── URL state sync ───────────────────────────────────────────────────────────
  useEffect(() => {
    const sp = new URLSearchParams(window.location.search)
    const updates: Partial<SimParams> = {}
    if (sp.has('n'))     updates.n_nodes    = parseInt(sp.get('n')!)
    if (sp.has('r'))     updates.n_robots   = parseInt(sp.get('r')!)
    if (sp.has('e'))     updates.energy     = parseFloat(sp.get('e')!)
    if (sp.has('L'))     updates.area_scale = parseFloat(sp.get('L')!)
    if (sp.has('seed'))  updates.seed       = parseInt(sp.get('seed')!)
    if (sp.has('model') && MODEL_OPTIONS.includes(sp.get('model') as SimParams['model']))
      updates.model = sp.get('model') as SimParams['model']
    if (sp.has('mode')) {
      const m = sp.get('mode') as AppMode
      if (['single', 'compare', 'benchmark'].includes(m)) setAppMode(m)
    }
    if (Object.keys(updates).length > 0)
      setParams(p => ({ ...p, ...updates }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const sp = new URLSearchParams({
      n:     String(params.n_nodes),
      r:     String(params.n_robots),
      e:     String(params.energy),
      L:     String(params.area_scale),
      seed:  String(params.seed),
      model: params.model,
      mode:  appMode,
    })
    window.history.replaceState(null, '', '?' + sp.toString())
  }, [params, appMode])

  // ── comparison mode state ────────────────────────────────────────────────────
  const [leftModel,      setLeftModel]      = useState<SimParams['model']>('M1')
  const [rightModel,     setRightModel]     = useState<SimParams['model']>('M4*')
  const [leftResult,     setLeftResult]     = useState<SimResult | null>(null)
  const [rightResult,    setRightResult]    = useState<SimResult | null>(null)
  const [leftStepIdx,    setLeftStepIdx]    = useState(0)
  const [rightStepIdx,   setRightStepIdx]   = useState(0)
  const [comparePlaying, setComparePlaying] = useState(false)
  const comparePlayRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── benchmark mode state ─────────────────────────────────────────────────────
  const [benchResults,  setBenchResults]  = useState<Partial<Record<string, SimResult>>>({})
  const [benchLoading,  setBenchLoading]  = useState(false)

  // ── demo mode state ───────────────────────────────────────────────────────────
  const [demoModel,      setDemoModel]      = useState<DemoModel>('M4*')
  const [demoCompare,    setDemoCompare]    = useState(false)
  const [demoLoading,    setDemoLoading]    = useState(false)
  const [demoStatus,     setDemoStatus]     = useState('')
  const [demoFrames,     setDemoFrames]     = useState(0)
  const [demoError,      setDemoError]      = useState<string | null>(null)
  const demoCanvasRef  = useRef<HTMLCanvasElement>(null)
  const demoWsRef      = useRef<WebSocket | null>(null)

  // ── helpers ──────────────────────────────────────────────────────────────────
  const setParam = <K extends keyof SimParams>(k: K, v: SimParams[K]) =>
    setParams(p => ({ ...p, [k]: v }))

  const totalRounds  = result?.rounds.length ?? 0
  const currentRound: RoundState | null = result?.rounds[stepIdx] ?? null

  const clampStep = (n: number) => Math.max(0, Math.min(totalRounds - 1, n))

  const stopPlay = useCallback(() => {
    if (playRef.current) { clearInterval(playRef.current); playRef.current = null }
    setPlaying(false)
  }, [])

  const startPlay = useCallback(() => {
    setPlaying(true)
    playRef.current = setInterval(() => {
      setStepIdx(s => {
        if (s >= totalRounds - 1) {
          stopPlay()
          return s
        }
        return s + 1
      })
    }, animMs + 200)
  }, [totalRounds, stopPlay, animMs])

  const stopComparePlay = useCallback(() => {
    if (comparePlayRef.current) { clearInterval(comparePlayRef.current); comparePlayRef.current = null }
    setComparePlaying(false)
  }, [])

  const startComparePlay = useCallback((lTotal: number, rTotal: number) => {
    setComparePlaying(true)
    comparePlayRef.current = setInterval(() => {
      setLeftStepIdx(s  => (s  < lTotal - 1 ? s + 1 : s))
      setRightStepIdx(s => (s < rTotal - 1 ? s + 1 : s))
    }, animMs + 200)
  }, [animMs])

  // cleanup on unmount
  useEffect(() => () => { stopPlay(); stopComparePlay() }, [stopPlay, stopComparePlay])

  // auto-stop single play when we reach last step
  useEffect(() => {
    if (playing && stepIdx >= totalRounds - 1) stopPlay()
  }, [playing, stepIdx, totalRounds, stopPlay])

  // auto-stop compare play when both reach end
  useEffect(() => {
    if (comparePlaying
      && leftStepIdx  >= (leftResult?.rounds.length  ?? 1) - 1
      && rightStepIdx >= (rightResult?.rounds.length ?? 1) - 1) {
      stopComparePlay()
    }
  }, [comparePlaying, leftStepIdx, rightStepIdx, leftResult, rightResult, stopComparePlay])

  const leftTotal   = leftResult?.rounds.length  ?? 0
  const rightTotal  = rightResult?.rounds.length ?? 0

  // ── keyboard shortcuts ───────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // only when not focused on an input/select
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return

      if (!result && !leftResult && !rightResult) return

      if (e.key === 'ArrowRight') {
        e.preventDefault()
        stopPlay(); stopComparePlay()
        if (!compareMode) {
          setStepIdx(s => clampStep(s + 1))
        } else {
          setLeftStepIdx(s  => Math.min(s + 1, (leftResult?.rounds.length  ?? 1) - 1))
          setRightStepIdx(s => Math.min(s + 1, (rightResult?.rounds.length ?? 1) - 1))
        }
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        stopPlay(); stopComparePlay()
        if (!compareMode) {
          setStepIdx(s => clampStep(s - 1))
        } else {
          setLeftStepIdx(s  => Math.max(0, s - 1))
          setRightStepIdx(s => Math.max(0, s - 1))
        }
      } else if (e.key === ' ') {
        e.preventDefault()
        if (!compareMode) {
          if (playing) stopPlay()
          else if (stepIdx < totalRounds - 1) startPlay()
        } else {
          if (comparePlaying) stopComparePlay()
          else startComparePlay(leftTotal, rightTotal)
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [result, leftResult, rightResult, compareMode, playing, comparePlaying,
      stepIdx, totalRounds, leftTotal, rightTotal,
      stopPlay, startPlay, stopComparePlay, startComparePlay, clampStep])

  // ── single-model simulation ──────────────────────────────────────────────────
  const runSimulation = async () => {
    stopPlay()
    setLoading(true)
    setError(null)
    setResult(null)
    setStepIdx(0)
    setShowTgt(false)
    try {
      const res = await fetch('/api/simulate', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(params),
      })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(`Server error ${res.status}: ${msg}`)
      }
      const data: SimResult = await res.json()
      setResult(data)
      setStepIdx(0)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  // ── comparison simulation ────────────────────────────────────────────────────
  const runComparison = async () => {
    stopPlay()
    stopComparePlay()
    setLoading(true)
    setError(null)
    setLeftResult(null)
    setRightResult(null)
    setLeftStepIdx(0)
    setRightStepIdx(0)
    setShowTgt(false)
    try {
      const fetchOne = async (m: SimParams['model']): Promise<SimResult> => {
        const res = await fetch('/api/simulate', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ ...params, model: m }),
        })
        if (!res.ok) {
          const msg = await res.text()
          throw new Error(`Server error ${res.status} (model ${m}): ${msg}`)
        }
        return res.json() as Promise<SimResult>
      }
      const [left, right] = await Promise.all([fetchOne(leftModel), fetchOne(rightModel)])
      setLeftResult(left)
      setRightResult(right)
      setLeftStepIdx(0)
      setRightStepIdx(0)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  // ── benchmark simulation ─────────────────────────────────────────────────────
  const runBenchmark = async () => {
    stopPlay(); stopComparePlay()
    setBenchLoading(true)
    setError(null)
    setBenchResults({})
    try {
      const fetchModel = async (m: SimParams['model']): Promise<[string, SimResult]> => {
        const res = await fetch('/api/simulate', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ ...params, model: m }),
        })
        if (!res.ok) throw new Error(`${m}: server error ${res.status}`)
        const data: SimResult = await res.json()
        return [m, data]
      }
      const all = await Promise.all(MODEL_OPTIONS.map(fetchModel))
      setBenchResults(Object.fromEntries(all))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBenchLoading(false)
    }
  }

  // cleanup WS on unmount
  useEffect(() => () => { demoWsRef.current?.close() }, [])

  // ── demo live stream ──────────────────────────────────────────────────────────
  const startLiveDemo = () => {
    demoWsRef.current?.close()
    setDemoLoading(true)
    setDemoError(null)
    setDemoStatus('Connecting...')
    setDemoFrames(0)

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${window.location.host}/api/pybullet/ws`)
    demoWsRef.current = ws

    ws.onopen = () => {
      setDemoStatus('Starting simulation...')
      ws.send(JSON.stringify({
        model:   demoModel.replace('M4*', 'M4star'),
        seed:    params.seed,
        n:       Math.min(params.n_nodes, 30),
        r:       params.n_robots,
        e:       params.energy,
        compare: demoCompare,
      }))
    }

    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === 'string') {
        const msg = JSON.parse(event.data) as { status: string; message?: string; total?: number }
        if (msg.status === 'done')      { setDemoLoading(false); setDemoStatus('Complete') }
        else if (msg.status === 'streaming') setDemoStatus('Rendering frames...')
        else if (msg.status === 'error') { setDemoError(msg.message ?? 'Unknown error'); setDemoLoading(false) }
      } else {
        const blob = new Blob([event.data as ArrayBuffer], { type: 'image/jpeg' })
        const url  = URL.createObjectURL(blob)
        const img  = new Image()
        img.onload = () => {
          const canvas = demoCanvasRef.current
          if (canvas) {
            if (canvas.width !== img.width || canvas.height !== img.height) {
              canvas.width  = img.width
              canvas.height = img.height
            }
            canvas.getContext('2d')?.drawImage(img, 0, 0)
          }
          URL.revokeObjectURL(url)
          setDemoFrames(f => f + 1)
        }
        img.src = url
      }
    }

    ws.onerror = () => { setDemoError('WebSocket connection failed — is the backend running?'); setDemoLoading(false) }
    ws.onclose = () => { setDemoLoading(false); demoWsRef.current = null }
  }

  // ── comparison step helpers ─────────────────────────────────���────────────────
  const leftRound:  RoundState | null = leftResult?.rounds[leftStepIdx]   ?? null
  const rightRound: RoundState | null = rightResult?.rounds[rightStepIdx] ?? null

  const advanceBoth = () => {
    stopComparePlay()
    setLeftStepIdx(s  => (s  < leftTotal  - 1 ? s + 1 : s))
    setRightStepIdx(s => (s < rightTotal - 1 ? s + 1 : s))
  }
  const resetBoth = () => {
    stopComparePlay()
    setLeftStepIdx(0)
    setRightStepIdx(0)
  }
  const jumpEndBoth = () => {
    stopComparePlay()
    setLeftStepIdx(Math.max(0, leftTotal - 1))
    setRightStepIdx(Math.max(0, rightTotal - 1))
  }

  const canAdvanceEither =
    (leftResult  != null && leftStepIdx  < leftTotal  - 1) ||
    (rightResult != null && rightStepIdx < rightTotal - 1)

  // ── derived stats ────────────────────────────────────────────────────────────
  const targetFoundStep = result?.rounds.findIndex(r => r.target_found) ?? -1

  // ── render ───────────────────────────────────────────────────────────────────
  return (
    <div className="app-shell" ref={shellRef}>

      {/* ── sidebar ── */}
      <aside className="sidebar">
        <h1 className="app-title">SearchFCR</h1>
        <p className="app-subtitle">Multi-robot search &amp; rescue simulator</p>

        {/* Honors thesis slides button */}
        <button
          className={`thesis-slides-btn ${appMode === 'honors' ? 'active' : ''}`}
          onClick={() => { setAppMode(appMode === 'honors' ? 'single' : 'honors'); setError(null) }}
        >
          🎓 Honors Thesis Slides
        </button>

        {/* nav links */}
        <div className="nav-links">
          <a href="https://github.com/research-cooperativelab/Multi-Robot-Algo" target="_blank" rel="noopener noreferrer" className="nav-link">GitHub</a>
          <a href="/api/health" target="_blank" rel="noopener noreferrer" className="nav-link">API Status</a>
        </div>

        {/* mode selector — hidden in honors mode */}
        {appMode !== 'honors' && <section className="panel">
          <h2 className="panel-title">Mode</h2>
          <div className="mode-btns">
            {(['single', 'compare', 'benchmark', 'demo'] as AppMode[]).map(m => (
              <button
                key={m}
                className={`mode-btn ${appMode === m ? 'active' : ''}`}
                onClick={() => { setAppMode(m); setError(null) }}
              >
                {m === 'single' ? 'Single' : m === 'compare' ? 'Compare' : m === 'benchmark' ? 'Benchmark' : '3D Demo'}
              </button>
            ))}
          </div>
        </section>}

        {/* model selector(s) */}
        {!compareMode ? (
          <section className="panel">
            <h2 className="panel-title">Model</h2>
            <div className="model-buttons">
              {MODEL_OPTIONS.map(m => (
                <button
                  key={m}
                  className={`model-btn ${params.model === m ? 'active' : ''}`}
                  onClick={() => setParam('model', m)}
                >
                  {m}
                </button>
              ))}
            </div>
            <ModelDescription model={params.model} />
          </section>
        ) : (
          <section className="panel">
            <h2 className="panel-title">Models</h2>
            <div className="compare-pick-row">
              <label className="compare-pick-label">Left</label>
              <select
                className="compare-select"
                value={leftModel}
                onChange={e => setLeftModel(e.target.value as SimParams['model'])}
              >
                {MODEL_OPTIONS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <ModelDescription model={leftModel} />
            <div className="compare-pick-row">
              <label className="compare-pick-label">Right</label>
              <select
                className="compare-select"
                value={rightModel}
                onChange={e => setRightModel(e.target.value as SimParams['model'])}
              >
                {MODEL_OPTIONS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <ModelDescription model={rightModel} />
          </section>
        )}

        {/* parameters */}
        <section className="panel">
          <h2 className="panel-title">Parameters</h2>

          <SliderRow
            label="Search sites (n)"
            value={params.n_nodes}
            min={5} max={80}
            onChange={v => setParam('n_nodes', v)}
          />
          <SliderRow
            label="Robots (R)"
            value={params.n_robots}
            min={1} max={8}
            onChange={v => setParam('n_robots', v)}
          />
          {(compareMode ||
            params.model === 'M3' || params.model === 'M4' || params.model === 'M4*') && (
            <SliderRow
              label="Energy (E)"
              value={params.energy}
              min={2} max={100} step={1}
              onChange={v => setParam('energy', v)}
              format={v => v.toFixed(0)}
            />
          )}
          <SliderRow
            label="Area scale (L)"
            value={params.area_scale}
            min={2} max={30} step={1}
            onChange={v => setParam('area_scale', v)}
          />
          <div className="slider-row">
            <div className="slider-header">
              <span className="slider-label">Seed</span>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <input
                  type="number"
                  className="seed-input"
                  value={params.seed}
                  onChange={e => setParam('seed', parseInt(e.target.value) || 0)}
                />
                <button
                  className="step-btn"
                  style={{ padding: '3px 8px', fontSize: '0.7rem' }}
                  title="Random seed"
                  onClick={() => setParam('seed', Math.floor(Math.random() * 100000))}
                >Random</button>
              </div>
            </div>
          </div>
        </section>

        {/* animation speed */}
        <section className="panel">
          <h2 className="panel-title">Animation Speed</h2>
          <div className="speed-btns">
            {SPEED_OPTIONS.map(opt => (
              <button
                key={opt.label}
                className={`speed-btn ${animMs === opt.ms ? 'active' : ''}`}
                onClick={() => setAnimMs(opt.ms)}
              >{opt.label}</button>
            ))}
          </div>
        </section>

        {/* demo mode controls */}
        {appMode === 'demo' && (
          <section className="panel">
            <h2 className="panel-title">Model</h2>
            <div className="model-buttons">
              {DEMO_MODELS.map(m => (
                <button
                  key={m}
                  className={`model-btn ${demoModel === m ? 'active' : ''}`}
                  onClick={() => setDemoModel(m)}
                >{m}</button>
              ))}
            </div>
            <label className="demo-compare-label">
              <input
                type="checkbox"
                checked={demoCompare}
                onChange={e => setDemoCompare(e.target.checked)}
              />
              Compare M1 vs selected model
            </label>
          </section>
        )}

        {/* run button */}
        {appMode !== 'demo' && appMode !== 'honors' && (
          <button
            className={`run-btn ${(loading || benchLoading) ? 'loading' : ''}`}
            onClick={benchMode ? runBenchmark : compareMode ? runComparison : runSimulation}
            disabled={loading || benchLoading}
          >
            {(loading || benchLoading)
              ? 'Running...'
              : benchMode
                ? 'Run Benchmark'
                : compareMode
                  ? 'Run Both'
                  : 'Run Simulation'}
          </button>
        )}

        {appMode === 'demo' && (
          <button
            className={`run-btn ${demoLoading ? 'loading' : ''}`}
            onClick={startLiveDemo}
            disabled={demoLoading}
          >
            {demoLoading ? 'Rendering 3D Demo...' : 'Generate 3D Demo'}
          </button>
        )}

        {error && <div className="error-box">{error}</div>}
        {demoError && <div className="error-box">{demoError}</div>}

        {/* keyboard shortcut hint */}
        {(result || leftResult || rightResult) && (
          <div className="kbd-hint">
            <span className="kbd">&#x2190;</span><span className="kbd">&#x2192;</span> rounds
            &nbsp;&nbsp;
            <span className="kbd">Space</span> play/pause
          </div>
        )}

        {/* info panel (single mode) */}
        {!compareMode && result && (
          <section className="panel info-panel">
            <h2 className="panel-title">Results</h2>
            <div className="info-grid">
              <div className="info-cell">
                <span className="info-label">Model</span>
                <span className="info-value highlight">{result.model}</span>
              </div>
              <div className="info-cell">
                <span className="info-label">Total rounds</span>
                <span className="info-value">{result.total_iterations}</span>
              </div>
              <div className="info-cell">
                <span className="info-label">Target found</span>
                <span className={`info-value ${result.found ? 'good' : 'bad'}`}>
                  {result.found ? `\u2713 round ${(targetFoundStep + 1)}` : '\u2717 not found'}
                </span>
              </div>
              <div className="info-cell">
                <span className="info-label">Final FCR</span>
                <span className="info-value highlight">
                  {result.final_fcr != null ? result.final_fcr.toFixed(2) : '\u2014'}
                </span>
              </div>
              <div className="info-cell">
                <span className="info-label">Optimal dist</span>
                <span className="info-value">{result.instance.optimal_dist.toFixed(2)}</span>
              </div>
            </div>

            {/* current round stats */}
            {currentRound && (
              <>
                <div className="divider" />
                <div className="info-grid">
                  <div className="info-cell">
                    <span className="info-label">Viewing round</span>
                    <span className="info-value">{currentRound.round} / {totalRounds}</span>
                  </div>
                  <div className="info-cell">
                    <span className="info-label">Visited so far</span>
                    <span className="info-value">
                      {currentRound.all_visited.length} / {result.instance.nodes.length}
                    </span>
                  </div>
                  {currentRound.fcr != null && (
                    <div className="info-cell full-width">
                      <span className="info-label">FCR at discovery</span>
                      <span className="info-value highlight">{currentRound.fcr.toFixed(3)}</span>
                    </div>
                  )}
                  <div className="info-cell full-width">
                    <span className="info-label">Robot distances</span>
                    <div className="robot-dists">
                      {Object.entries(currentRound.robot_total_dist).map(([r, d]) => (
                        <span key={r} className="robot-dist-badge">
                          R{r}: {(d as number).toFixed(1)}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}
          </section>
        )}

        {/* compact comparison summary */}
        {compareMode && (leftResult || rightResult) && (
          <section className="panel info-panel">
            <h2 className="panel-title">Comparison</h2>
            <div className="compare-summary">
              {[
                { side: 'Left',  res: leftResult,  idx: leftStepIdx,  total: leftTotal },
                { side: 'Right', res: rightResult, idx: rightStepIdx, total: rightTotal },
              ].map(({ side, res, idx, total }) => (
                <div key={side} className="compare-summary-cell">
                  <div className="info-label">{side} · {res?.model ?? '\u2014'}</div>
                  <div className="info-value">
                    Round {total > 0 ? idx + 1 : 0} / {total}
                  </div>
                  <div className="info-value highlight">
                    FCR: {res?.final_fcr != null ? res.final_fcr.toFixed(2) : '\u2014'}
                  </div>
                  <div className={`info-value ${res?.found ? 'good' : 'bad'}`}>
                    {res ? (res.found ? '\u2713 found' : '\u2717 not found') : '\u2014'}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* show/hide target toggle */}
        {(result || leftResult || rightResult) && (
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showTgt}
              onChange={e => setShowTgt(e.target.checked)}
            />
            Reveal target location
          </label>
        )}
      </aside>

      {/* ── canvas area ── */}
      <main className="canvas-area">
        {appMode === 'honors' ? (
          <HonorsSlides />
        ) : appMode === 'demo' ? (
          <div className="demo-view">
            <h2 className="demo-heading">3D Physics Demo</h2>
            <p className="demo-desc">
              Streams a live PyBullet physics simulation frame-by-frame.
              Uses the same seed and parameters as the main simulator.
            </p>

            <canvas
              ref={demoCanvasRef}
              className="demo-canvas"
              style={{ display: demoFrames > 0 ? 'block' : 'none' }}
            />

            {demoLoading && (
              <div className="demo-status">
                <div className="bench-spinner" />
                <span>{demoStatus}{demoFrames > 0 ? ` — ${demoFrames} frames` : ''}</span>
              </div>
            )}

            {!demoLoading && demoFrames > 0 && (
              <p className="demo-caption">
                {demoCompare ? `M1 vs ${demoModel} (side-by-side)` : demoModel}
                &nbsp;·&nbsp;seed {params.seed}
                &nbsp;·&nbsp;{demoFrames} frames rendered
              </p>
            )}

            {!demoLoading && demoFrames === 0 && !demoError && (
              <div className="empty-state">
                <div className="empty-icon" />
                <p>Select a model and click <strong>Generate 3D Demo</strong> to stream a live physics simulation.</p>
              </div>
            )}
          </div>
        ) : benchMode ? (
          <BenchmarkView results={benchResults} loading={benchLoading} />
        ) : !compareMode ? (
          result ? (
            <>
              <SimCanvas
                instance={result.instance}
                round={currentRound}
                stepIndex={stepIdx}
                showTarget={showTgt || (currentRound?.target_found ?? false)}
                animDuration={animMs}
              />

              {/* round counter + found box */}
              <RoundCounter round={currentRound} totalRounds={totalRounds} result={result} />

              {/* FCR + entropy timelines */}
              <div className="timelines-row">
                <FcrTimeline rounds={result.rounds.slice(0, stepIdx + 1)} />
                <EntropyTimeline rounds={result.rounds.slice(0, stepIdx + 1)} />
              </div>

              {/* step controls */}
              <div className="step-controls">
                <button
                  className="step-btn"
                  onClick={() => { stopPlay(); setStepIdx(clampStep(0)) }}
                  disabled={stepIdx === 0}
                  title="First round"
                >First</button>

                <button
                  className="step-btn"
                  onClick={() => { stopPlay(); setStepIdx(s => clampStep(s - 1)) }}
                  disabled={stepIdx === 0}
                  title="Previous round"
                >Prev</button>

                <button
                  className="step-btn play-btn"
                  onClick={playing ? stopPlay : startPlay}
                  disabled={stepIdx >= totalRounds - 1 && !playing}
                  title={playing ? 'Pause' : 'Play through rounds'}
                >
                  {playing ? 'Pause' : 'Play'}
                </button>

                <button
                  className="step-btn"
                  onClick={() => { stopPlay(); setStepIdx(s => clampStep(s + 1)) }}
                  disabled={stepIdx >= totalRounds - 1}
                  title="Next round"
                >Next</button>

                <button
                  className="step-btn"
                  onClick={() => { stopPlay(); setStepIdx(clampStep(totalRounds - 1)) }}
                  disabled={stepIdx >= totalRounds - 1}
                  title="Last round"
                >Last</button>
              </div>

              {/* round progress bar */}
              <div className="progress-bar-wrap">
                <input
                  type="range"
                  className="progress-bar"
                  min={0}
                  max={Math.max(0, totalRounds - 1)}
                  value={stepIdx}
                  onChange={e => { stopPlay(); setStepIdx(Number(e.target.value)) }}
                />
              </div>
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon"></div>
              <p>Configure parameters and click<br /><strong>Run Simulation</strong> to start.</p>
            </div>
          )
        ) : (
          // ── comparison mode canvas area ──
          (leftResult || rightResult) ? (
            <>
              <div className="compare-canvas-row">
                {[
                  {
                    key: 'left',
                    res: leftResult,
                    round: leftRound,
                    idx: leftStepIdx,
                    total: leftTotal,
                  },
                  {
                    key: 'right',
                    res: rightResult,
                    round: rightRound,
                    idx: rightStepIdx,
                    total: rightTotal,
                  },
                ].map(({ key, res, round, idx, total }) => (
                  <div key={key} className="compare-canvas-cell">
                    <div className="compare-canvas-header">
                      <span className="compare-model-tag">
                        {res?.model ?? '\u2014'}
                        {res && <BidBadge model={res.model as SimParams['model']} />}
                      </span>
                      <span className="compare-round">
                        Round {total > 0 ? idx + 1 : 0} / {total}
                      </span>
                      <span className="compare-fcr">
                        FCR: {res?.final_fcr != null ? res.final_fcr.toFixed(2) : '\u2014'}
                        {round?.target_found && (
                          <span className="found-badge"> \u2605</span>
                        )}
                      </span>
                    </div>
                    {res ? (
                      <>
                        <SimCanvas
                          instance={res.instance}
                          round={round}
                          stepIndex={idx}
                          showTarget={showTgt || (round?.target_found ?? false)}
                          size={460}
                          animDuration={animMs}
                        />
                        <FcrTimeline rounds={res.rounds.slice(0, idx + 1)} />
                      </>
                    ) : (
                      <div className="empty-state small"><p>\u2014</p></div>
                    )}
                  </div>
                ))}
              </div>

              {/* FCR winner callout */}
              {leftResult?.final_fcr != null && rightResult?.final_fcr != null && (() => {
                const lf = leftResult.final_fcr!
                const rf = rightResult.final_fcr!
                const diff = Math.abs(lf - rf)
                const pct  = ((diff / Math.max(lf, rf)) * 100).toFixed(1)
                const winner = lf < rf ? leftModel : rightModel
                const winnerFcr = lf < rf ? lf : rf
                return (
                  <div className="fcr-winner-callout">
                    <span className="fcr-winner-label">
                      <span className="fcr-winner-model">{winner}</span> wins
                      &nbsp;·&nbsp;FCR {winnerFcr.toFixed(2)}
                      &nbsp;·&nbsp;<span className="fcr-winner-pct">{pct}% better</span>
                    </span>
                  </div>
                )
              })()}

              {/* step controls (shared) */}
              <div className="step-controls">
                <button
                  className="step-btn"
                  onClick={resetBoth}
                  disabled={leftStepIdx === 0 && rightStepIdx === 0}
                  title="First round (both)"
                >First</button>

                <button
                  className="step-btn"
                  onClick={() => {
                    stopComparePlay()
                    setLeftStepIdx(s  => Math.max(0, s - 1))
                    setRightStepIdx(s => Math.max(0, s - 1))
                  }}
                  disabled={leftStepIdx === 0 && rightStepIdx === 0}
                  title="Previous round (both)"
                >Prev</button>

                <button
                  className="step-btn play-btn"
                  onClick={() => {
                    if (comparePlaying) stopComparePlay()
                    else startComparePlay(leftTotal, rightTotal)
                  }}
                  disabled={!canAdvanceEither && !comparePlaying}
                  title={comparePlaying ? 'Pause' : 'Play both'}
                >
                  {comparePlaying ? 'Pause' : 'Play'}
                </button>

                <button
                  className="step-btn"
                  onClick={advanceBoth}
                  disabled={!canAdvanceEither}
                  title="Next round (both)"
                >Next</button>

                <button
                  className="step-btn"
                  onClick={jumpEndBoth}
                  disabled={!canAdvanceEither}
                  title="Last round (both)"
                >Last</button>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon"></div>
              <p>
                Pick two models and click<br />
                <strong>Run Both</strong> to compare them on the same seed.
              </p>
            </div>
          )
        )}
      </main>
    </div>
  )
}
