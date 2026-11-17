import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'

/* ── API ─────────────────────────────────────────────────────── */
const api = {
  generate: (idea, file) =>
    fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_idea: idea, output_file: file }),
    }).then(r => r.json()),

  pollJob:     (id)  => fetch(`/api/jobs/${id}`).then(r => r.json()),
  history:     ()    => fetch('/api/history').then(r => r.json()),
  historyItem: (id)  => fetch(`/api/history/${id}`).then(r => r.json()),
  deleteRun:   (id)  => fetch(`/api/history/${id}`, { method: 'DELETE' }).then(r => r.json()),
  play:        (id)  => fetch(`/api/history/play/${id}`, { method: 'POST' }).then(r => r.json()),

  similar: (idea) =>
    fetch('/api/similar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_idea: idea, k: 3 }),
    }).then(r => r.json()),
}

/* ── Confetti burst on success ───────────────────────────────── */
function ConfettiBurst({ trigger }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!trigger) return
    const canvas = ref.current
    if (!canvas) return
    canvas.width  = window.innerWidth
    canvas.height = window.innerHeight
    const ctx = canvas.getContext('2d')

    const palette = ['#fafafa','#d4d4d8','#a1a1aa','#71717a','#e4e4e7','#52525b']
    const pieces  = Array.from({ length: 80 }, () => {
      const angle = Math.random() * Math.PI * 2
      const spd   = 3 + Math.random() * 9
      return {
        x: canvas.width * 0.55, y: canvas.height * 0.35,
        vx: Math.cos(angle) * spd,
        vy: Math.sin(angle) * spd - 4,
        r: 2 + Math.random() * 4,
        color: palette[Math.floor(Math.random() * palette.length)],
        alpha: 1, gravity: 0.18 + Math.random() * 0.08,
        rot: Math.random() * Math.PI, rotV: (Math.random() - 0.5) * 0.15,
        sq: Math.random() > 0.5,
      }
    })

    let raf
    const tick = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      let alive = 0
      for (const p of pieces) {
        p.x += p.vx; p.y += p.vy; p.vy += p.gravity
        p.vx *= 0.994; p.alpha *= 0.976; p.r *= 0.99; p.rot += p.rotV
        if (p.alpha < 0.02 || p.r < 0.3) continue
        alive++
        ctx.save()
        ctx.globalAlpha = p.alpha
        ctx.fillStyle   = p.color
        ctx.translate(p.x, p.y); ctx.rotate(p.rot)
        if (p.sq) ctx.fillRect(-p.r, -p.r * 0.35, p.r * 2, p.r * 0.7)
        else { ctx.beginPath(); ctx.arc(0,0,p.r,0,Math.PI*2); ctx.fill() }
        ctx.restore()
      }
      if (alive > 0) raf = requestAnimationFrame(tick)
      else ctx.clearRect(0,0,canvas.width,canvas.height)
    }
    tick()
    return () => cancelAnimationFrame(raf)
  }, [trigger])

  return <canvas ref={ref} className="confetti-canvas" aria-hidden />
}

/* ── Success notification ────────────────────────────────────── */
function SuccessPanel({ filename, desc, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 7000)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className="succ-panel" role="status">
      <div className="succ-gutter" />
      <div className="succ-body">
        <div className="succ-title">Build complete</div>
        <div className="succ-file">{filename}</div>
        {desc && <div className="succ-desc">{desc}</div>}
        <div className="succ-actions">
          <button className="succ-dismiss" onClick={onDismiss}>Dismiss</button>
        </div>
      </div>
      <div className="succ-progress" />
    </div>
  )
}

/* ── Terminal log ────────────────────────────────────────────── */
function TermLog({ lines, status }) {
  const bodyRef = useRef(null)
  useEffect(() => {
    if (bodyRef.current)
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [lines])

  const running = status === 'running' || status === 'queued'

  return (
    <div className="term">
      <div className="term-titlebar">
        <div className="term-dots">
          <span /><span /><span />
        </div>
        <span className="term-name">pipeline — {status}</span>
        <span className={`term-badge term-badge--${status}`}>{status}</span>
      </div>
      <div className="term-body" ref={bodyRef}>
        <div className="term-line term-line--dim">
          $ ideatogame run --agents designer,developer,qa
        </div>
        {lines.length === 0 && (
          <div className="term-line term-line--dim">waiting for agents…</div>
        )}
        {lines.map((ln, i) => (
          <div key={i} className="term-line">
            <span className="term-prompt">›</span>
            <span>{ln}</span>
          </div>
        ))}
        {running && <span className="term-cursor">█</span>}
        {status === 'done' && (
          <div className="term-line term-line--ok">
            <span className="term-prompt">✓</span>
            Process exited with code 0
          </div>
        )}
        {status === 'failed' && (
          <div className="term-line term-line--err">
            <span className="term-prompt">✗</span>
            Process exited with error
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Game Launch Modal ───────────────────────────────────────── */
function GameLaunchModal({ code, filename, onClose }) {
  const download = () => {
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(new Blob([code], { type: 'text/plain' })),
      download: filename || 'game.py',
    })
    a.click()
  }

  // Close on overlay click or Escape key
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="game-modal-overlay" onClick={onClose}>
      <div className="game-modal" onClick={e => e.stopPropagation()}>
        <div className="game-modal-hd">
          <span className="game-modal-title">How to play your game</span>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>

        <div className="game-modal-opts">
          <div className="game-modal-opt">
            <span className="game-modal-opt-icon">💻</span>
            <div>
              <div className="game-modal-opt-title">Run locally</div>
              <div className="game-modal-opt-desc">
                Download the file, then in your terminal run:<br />
                <code>pip install pygame &amp;&amp; python {filename || 'game.py'}</code>
              </div>
            </div>
          </div>

          <div className="game-modal-opt">
            <span className="game-modal-opt-icon">🔁</span>
            <div>
              <div className="game-modal-opt-title">Run on Replit</div>
              <div className="game-modal-opt-desc">
                Open a free Python environment online, paste your code, and click&nbsp;<strong>Run</strong>.
                Replit supports Pygame via VNC display.
              </div>
            </div>
          </div>

          <div className="game-modal-opt">
            <span className="game-modal-opt-icon">🌐</span>
            <div>
              <div className="game-modal-opt-title">Simple Pygame (Trinket)</div>
              <div className="game-modal-opt-desc">
                For beginner-level Pygame scripts, try{' '}
                <a href="https://trinket.io/pygame" target="_blank" rel="noreferrer">trinket.io/pygame</a>.
                Paste the code and hit Run.
              </div>
            </div>
          </div>
        </div>

        <div className="game-modal-actions">
          <button className="game-modal-dl" onClick={download}>
            ⬇&nbsp; Download {filename || 'game.py'}
          </button>
          <a
            className="game-modal-replit"
            href="https://replit.com/@replit/Python?v=1"
            target="_blank"
            rel="noreferrer"
          >
            ▶&nbsp; Open Replit
          </a>
        </div>
      </div>
    </div>
  )
}

/* ── Code viewer ─────────────────────────────────────────────── */
function CodeViewer({ code, filename, jobId }) {
  const [copied, setCopied] = useState(false)
  const [showModal, setShowModal] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  const download = () => {
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(new Blob([code], { type: 'text/plain' })),
      download: filename || 'game.py',
    })
    a.click()
  }

  const lines = code.split('\n')

  return (
    <>
      {showModal && (
        <GameLaunchModal
          code={code}
          filename={filename}
          onClose={() => setShowModal(false)}
        />
      )}
      <div className="editor">
        <div className="editor-bar">
          <div className="editor-tabs">
            <div className="editor-tab editor-tab--active">
              <span className="editor-tab-icon">⬡</span>
              {filename}
            </div>
          </div>
          <div className="editor-actions">
            <button className="e-btn" onClick={copy}>
              {copied ? '✓ copied' : 'Copy'}
            </button>
            <button className="e-btn" onClick={download}>⬇ Download</button>
            <button
              className="e-btn e-btn--run"
              onClick={() => setShowModal(true)}
            >
              ▶ Play
            </button>
          </div>
        </div>
        <div className="editor-body">
          <div className="editor-gutter">
            {lines.map((_, i) => (
              <div key={i} className="editor-ln">{i + 1}</div>
            ))}
          </div>
          <pre className="editor-code"><code>{code}</code></pre>
        </div>
      </div>
    </>
  )
}

/* ── History drawer ──────────────────────────────────────────── */
function HistoryDrawer({ onClose, onSelect }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [removing, setRemoving] = useState(null)

  useEffect(() => {
    api.history()
      .then(setItems).catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  const remove = async (e, id) => {
    e.stopPropagation()
    setRemoving(id)
    await api.deleteRun(id)
    setItems(p => p.filter(i => i.id !== id))
    setRemoving(null)
  }

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={e => e.stopPropagation()}>
        <div className="drawer-hd">
          <span className="drawer-title">Run history</span>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        {loading ? (
          <div className="drawer-msg">Loading…</div>
        ) : items.length === 0 ? (
          <div className="drawer-msg">No runs yet — generate your first game.</div>
        ) : (
          <ul className="drawer-list">
            {items.map(it => (
              <li key={it.id}
                  className={`ditem ${removing === it.id ? 'ditem--fade' : ''}`}
                  onClick={() => onSelect(it)}>
                <div className="ditem-top">
                  <span className={`ditem-status ditem-status--${it.status}`} />
                  <span className="ditem-idea">{it.game_idea || '—'}</span>
                  <button className="ditem-del" onClick={e => remove(e, it.id)}>
                    {removing === it.id ? '…' : '✕'}
                  </button>
                </div>
                <div className="ditem-meta">
                  <code className="ditem-file">{it.output_file}</code>
                  <span className="ditem-date">
                    {new Date(it.created_at).toLocaleDateString('en-GB', {
                      day:'2-digit', month:'short', year:'numeric'
                    })}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

/* ── App ─────────────────────────────────────────────────────── */
export default function App() {
  const [idea, setIdea]         = useState('')
  const [outFile, setOutFile]   = useState('game.py')
  const [jobId, setJobId]       = useState(null)
  const [job, setJob]           = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const [similar, setSimilar]   = useState('')
  const [simLoading, setSimLoading] = useState(false)
  const [burst, setBurst]       = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const pollRef = useRef(null)

  /* similar debounce */
  useEffect(() => {
    if (idea.length < 10) { setSimilar(''); return }
    const t = setTimeout(() => {
      setSimLoading(true)
      api.similar(idea)
        .then(r => setSimilar(r.results || ''))
        .catch(() => setSimilar(''))
        .finally(() => setSimLoading(false))
    }, 800)
    return () => clearTimeout(t)
  }, [idea])

  /* poll */
  const poll = useCallback((id) => {
    pollRef.current = setInterval(async () => {
      try {
        const d = await api.pollJob(id)
        setJob(d)
        if (d.status === 'done' || d.status === 'failed') {
          clearInterval(pollRef.current)
          if (d.status === 'done') {
            if (d.result?.run_id) setJobId(d.result.run_id)
            setBurst(true)
            setShowSuccess(true)
            setTimeout(() => setBurst(false), 3200)
          }
        }
      } catch { clearInterval(pollRef.current) }
    }, 2000)
  }, [])

  useEffect(() => () => clearInterval(pollRef.current), [])

  const generate = async () => {
    if (!idea.trim()) return
    setJob({ status: 'queued', progress: [], result: null })
    setJobId(null); setShowSuccess(false)
    clearInterval(pollRef.current)
    try {
      const r = await api.generate(idea.trim(), outFile.trim() || 'game.py')
      setJobId(r.job_id); poll(r.job_id)
    } catch (e) {
      setJob({ status: 'failed', progress: [`error: ${e.message}`], result: null })
    }
  }

  const isRunning = job?.status === 'queued' || job?.status === 'running'
  const isDone    = job?.status === 'done'
  const isFailed  = job?.status === 'failed'
  const isLoaded  = job?.status === 'loaded'
  const hasCode   = (isDone || isLoaded) && job?.result?.code

  return (
    <div className="root">
      <ConfettiBurst trigger={burst} />

      {/* ── Header ── */}
      <header className="hdr">
        <div className="hdr-left">
          <span className="hdr-logo">itg</span>
          <span className="hdr-sep">/</span>
          <span className="hdr-proj">IdeaToGame</span>
        </div>
        <div className="hdr-right">
          <button className="hdr-btn" onClick={() => setShowHistory(true)}>
            History
          </button>
        </div>
      </header>

      {/* ── Workspace ── */}
      <div className="workspace">

        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="sb-section">
            <label className="sb-label">Game idea</label>
            <textarea
              className="sb-ta"
              rows={6}
              placeholder="Describe your game idea in detail…"
              value={idea}
              onChange={e => setIdea(e.target.value)}
              disabled={isRunning}
            />
          </div>

          <div className="sb-section">
            <label className="sb-label">Output file</label>
            <input
              className="sb-input"
              value={outFile}
              onChange={e => setOutFile(e.target.value)}
              placeholder="game.py"
              disabled={isRunning}
            />
          </div>

          <button
            className={`run-btn ${isRunning ? 'run-btn--busy' : ''}`}
            onClick={generate}
            disabled={isRunning || !idea.trim()}
          >
            {isRunning ? (
              <><span className="run-spin" />Generating</>
            ) : 'Generate'}
          </button>

          {(similar || simLoading) && (
            <div className="sim-block">
              <div className="sim-hd">
                Similar games {simLoading && <span className="run-spin run-spin--sm" />}
              </div>
              {similar && <pre className="sim-pre">{similar}</pre>}
            </div>
          )}
        </aside>

        {/* ── Editor pane ── */}
        <main className="editor-pane">

          {/* Success */}
          {showSuccess && isDone && job?.result && (
            <SuccessPanel
              filename={job.result.output_file}
              desc={job.result.description}
              onDismiss={() => setShowSuccess(false)}
            />
          )}

          {/* Empty */}
          {!job && (
            <div className="empty">
              <div className="empty-code">
                <pre>{`# IdeaToGame
# Describe a game → AI builds it

$ itg generate "Space shooter with bosses"
  ↳ designer   writing GDD…
  ↳ developer  writing pygame code…
  ↳ qa         testing and patching…
  ✓ game.py    ready to run`}
                </pre>
              </div>
              <div className="empty-examples">
                {['Snake Evolution','Space Shooter','Tower Defense','Brick Breaker'].map(s => (
                  <button key={s} className="ex-chip" onClick={() => setIdea(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {/* Terminal log */}
          {job && (isRunning || isFailed || (isDone && job.progress?.length > 0)) && (
            <TermLog lines={job.progress || []} status={job.status} />
          )}

          {/* Code viewer */}
          {hasCode && (
            <CodeViewer
              code={job.result.code}
              filename={job.result.output_file}
              jobId={jobId}
            />
          )}
        </main>
      </div>

      {/* ── History drawer ── */}
      {showHistory && (
        <HistoryDrawer
          onClose={() => setShowHistory(false)}
          onSelect={async (item) => {
            setIdea(item.game_idea); setOutFile(item.output_file)
            setJobId(item.id); setShowHistory(false)
            try {
              const full = await api.historyItem(item.id)
              setJob({
                status: 'loaded', progress: [],
                result: {
                  code: full.game_code || '# code not found',
                  output_file: full.output_file,
                  description: full.description,
                  retries: full.retries,
                }
              })
            } catch {}
          }}
        />
      )}
    </div>
  )
}
