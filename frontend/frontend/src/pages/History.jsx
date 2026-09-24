import { useState } from 'react'
import RiskReport from '../components/RiskReport'

export default function History({ records }) {
  const [selected, setSelected] = useState(null)

  if (records.length === 0)
    return (
      <>
        <h1 className="page-title">History</h1>
        <div className="card"><p className="empty">No invoices analyzed yet.</p></div>
      </>
    )

  return (
    <>
      <h1 className="page-title">History</h1>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Invoice ID</th>
              <th>Vendor</th>
              <th>Amount</th>
              <th>Risk Score</th>
              <th>Level</th>
              <th>Decision</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => (
              <tr key={i}>
                <td>{r.invoice_id}</td>
                <td>{r.vendor}</td>
                <td>₹{r.amount.toLocaleString('en-IN')}</td>
                <td><strong>{r.risk_score}</strong></td>
                <td><span className={`badge badge-${r.risk_level}`}>{r.risk_level}</span></td>
                <td><span className={`rec-badge rec-${r.recommendation}`} style={{padding:'3px 10px',fontSize:12}}>{r.recommendation}</span></td>
                <td>
                  <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: 12 }}
                    onClick={() => setSelected(selected?.invoice_id === r.invoice_id ? null : r)}>
                    {selected?.invoice_id === r.invoice_id ? 'Hide' : 'View'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="card">
          <RiskReport report={selected} />
        </div>
      )}
    </>
  )
}
