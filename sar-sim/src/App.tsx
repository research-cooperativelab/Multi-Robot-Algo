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

const MODEL_DESC: Record<SimParams['model'], string> = {
  M1:  'Random — no coordination, infinite energy',
  M2:  'Auction + node-to-node, infinite energy',
  M3:  'Auction + single-node sorties, finite energy',
  M4:  'Auction + multi-node chain (p/d), finite energy',
  'M4*': 'Auction + multi-node chain (p/d²) — best performer',
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

// ── App ────────────────────────────────────────────────────────────────────────
export default function App() {
  const [params,    setParams]    = useState<SimParams>(DEFAULT_PARAMS)
  const [result,    setResult]    = useState<SimResult | null>(null)
  const [stepIdx,   setStepIdx]   = useState(0)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [playing,   setPlaying]   = useState(false)
  const [showTgt,   setShowTgt]   = useState(false)
  const playRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── helpers ──────────────────────────────────────────────────────────────────
  const setParam = <K extends keyof SimParams>(k: K, v: SimParams[K]) =>
    setParams(p => ({ ...p, [k]: v }))

  const totalRounds = result?.rounds.length ?? 0
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
    }, 600)
  }, [totalRounds, stopPlay])

  // cleanup on unmount
  useEffect(() => () => stopPlay(), [stopPlay])

  // auto-stop when we reach last step
  useEffect(() => {
    if (playing && stepIdx >= totalRounds - 1) stopPlay()
  }, [playing, stepIdx, totalRounds, stopPlay])

  // ── run simulation ────────────────────────────────────────────────────────────
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

  // ── derived stats for info panel ──────────────────────────────────────────────
  const targetFoundStep = result?.rounds.findIndex(r => r.target_found) ?? -1

  // ── render ───────────────────────────────────────────────────────────────────
  return (
    <div className="app-shell">

      {/* ── sidebar ── */}
      <aside className="sidebar">
        <h1 className="app-title">SAR Simulation</h1>
        <p className="app-subtitle">Multi-robot search &amp; rescue</p>

        {/* model selector */}
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
          <p className="model-desc">{MODEL_DESC[params.model]}</p>
        </section>

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
          {(params.model === 'M3' || params.model === 'M4' || params.model === 'M4*') && (
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
              <input
                type="number"
                className="seed-input"
                value={params.seed}
                onChange={e => setParam('seed', parseInt(e.target.value) || 0)}
              />
            </div>
          </div>
        </section>

        {/* run button */}
        <button
          className={`run-btn ${loading ? 'loading' : ''}`}
          onClick={runSimulation}
          disabled={loading}
        >
          {loading ? 'Running…' : '▶  Run Simulation'}
        </button>

        {error && <div className="error-box">{error}</div>}

        {/* info panel */}
        {result && (
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
                  {result.found ? `✓ round ${(targetFoundStep + 1)}` : '✗ not found'}
                </span>
              </div>
              <div className="info-cell">
                <span className="info-label">Final FCR</span>
                <span className="info-value highlight">
                  {result.final_fcr != null ? result.final_fcr.toFixed(2) : '—'}
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

        {/* show/hide target toggle */}
        {result && (
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
        {result ? (
          <>
            <SimCanvas
              instance={result.instance}
              round={currentRound}
              stepIndex={stepIdx}
              showTarget={showTgt || (currentRound?.target_found ?? false)}
            />

            {/* step controls */}
            <div className="step-controls">
              <button
                className="step-btn"
                onClick={() => { stopPlay(); setStepIdx(clampStep(0)) }}
                disabled={stepIdx === 0}
                title="First round"
              >⏮</button>

              <button
                className="step-btn"
                onClick={() => { stopPlay(); setStepIdx(s => clampStep(s - 1)) }}
                disabled={stepIdx === 0}
                title="Previous round"
              >◀ Prev</button>

              <button
                className="step-btn play-btn"
                onClick={playing ? stopPlay : startPlay}
                disabled={stepIdx >= totalRounds - 1 && !playing}
                title={playing ? 'Pause' : 'Play through rounds'}
              >
                {playing ? '⏸ Pause' : '▶ Play'}
              </button>

              <button
                className="step-btn"
                onClick={() => { stopPlay(); setStepIdx(s => clampStep(s + 1)) }}
                disabled={stepIdx >= totalRounds - 1}
                title="Next round"
              >Next ▶</button>

              <button
                className="step-btn"
                onClick={() => { stopPlay(); setStepIdx(clampStep(totalRounds - 1)) }}
                disabled={stepIdx >= totalRounds - 1}
                title="Last round"
              >⏭</button>
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
              <span className="progress-label">
                Round {stepIdx + 1} / {totalRounds}
                {currentRound?.target_found && (
                  <span className="found-badge"> ★ Target found!</span>
                )}
              </span>
            </div>
          </>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">🤖</div>
            <p>Configure parameters and click<br /><strong>Run Simulation</strong> to start.</p>
          </div>
        )}
      </main>
    </div>
  )
}
