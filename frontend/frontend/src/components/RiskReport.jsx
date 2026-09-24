export default function RiskReport({ report }) {
  const { invoice_id, vendor, amount, risk_score, risk_level, flags, explanation, recommendation } = report

  return (
    <>
      {/* Score + Summary */}
      <div className="score-section">
        <div className={`score-ring ${risk_level}`}>
          <span className="score-num">{risk_score}</span>
          <span className="score-label">/ 100</span>
        </div>
        <div className="score-meta">
          <h2>{vendor}</h2>
          <p>Invoice: {invoice_id}</p>
          <p>Amount: ₹{amount.toLocaleString('en-IN')}</p>
          <span className={`badge badge-${risk_level}`}>{risk_level} RISK</span>
        </div>
      </div>

      {/* Flags */}
      {flags.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: '#555' }}>
            DETECTED FLAGS ({flags.length})
          </h3>
          <div className="flags-list">
            {flags.map((f, i) => (
              <div key={i} className={`flag-item ${f.severity}`}>
                <div>
                  <div className="flag-check">{f.check}</div>
                  <div className="flag-detail">{f.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Explanation */}
      <div>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: '#555' }}>
          AI EXPLANATION
        </h3>
        <div className="explanation-box">{explanation}</div>
        <div className={`rec-badge rec-${recommendation}`}>
          {recommendation === 'HOLD' ? '🚫' : recommendation === 'REVIEW' ? '⚠️' : '✅'} {recommendation}
        </div>
      </div>
    </>
  )
}
