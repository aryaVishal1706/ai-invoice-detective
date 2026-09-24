import { useState } from 'react'
import RiskReport from '../components/RiskReport'

const EMPTY = {
  invoice_id: '', vendor_name: '', vendor_gstin: '',
  amount: '', tax_amount: '', tax_rate: 0.18,
  invoice_date: '', submission_date: '',
  po_number: '', bank_account: '', payment_terms: 'Net 30'
}

const API = import.meta.env.VITE_API_URL || ''

export default function Analyze({ onResult }) {
  const [form, setForm]     = useState(EMPTY)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    setError(''); setLoading(true); setReport(null)
    try {
      const payload = {
        ...form,
        amount:     parseFloat(form.amount),
        tax_amount: parseFloat(form.tax_amount),
        tax_rate:   parseFloat(form.tax_rate),
        vendor_gstin:  form.vendor_gstin  || null,
        po_number:     form.po_number     || null,
        payment_terms: form.payment_terms || null,
      }
      const res = await fetch(`${API}/invoice/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setReport(data)
      onResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const valid = form.invoice_id && form.vendor_name && form.amount &&
                form.tax_amount && form.invoice_date && form.submission_date && form.bank_account

  return (
    <>
      <h1 className="page-title">Analyze Invoice</h1>

      <div className="card">
        <div className="form-grid">
          <div className="form-group">
            <label>Invoice ID *</label>
            <input placeholder="INV-2024-001" value={form.invoice_id} onChange={e => set('invoice_id', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Vendor Name *</label>
            <input placeholder="Wipro Technologies" value={form.vendor_name} onChange={e => set('vendor_name', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Vendor GSTIN</label>
            <input placeholder="27AABCT1332L1ZN" value={form.vendor_gstin} onChange={e => set('vendor_gstin', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Bank Account *</label>
            <input placeholder="ACC123456789" value={form.bank_account} onChange={e => set('bank_account', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Amount (₹) *</label>
            <input type="number" placeholder="500000" value={form.amount} onChange={e => set('amount', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Tax Amount (₹) *</label>
            <input type="number" placeholder="90000" value={form.tax_amount} onChange={e => set('tax_amount', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Invoice Date *</label>
            <input type="date" value={form.invoice_date} onChange={e => set('invoice_date', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Submission Date *</label>
            <input type="date" value={form.submission_date} onChange={e => set('submission_date', e.target.value)} />
          </div>
          <div className="form-group">
            <label>PO Number</label>
            <input placeholder="PO-1234-ABCD" value={form.po_number} onChange={e => set('po_number', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Payment Terms</label>
            <select value={form.payment_terms} onChange={e => set('payment_terms', e.target.value)}>
              <option>Net 30</option>
              <option>Net 45</option>
              <option>Net 60</option>
            </select>
          </div>
        </div>

        <div style={{ marginTop: 20 }}>
          <button className="btn btn-primary" onClick={submit} disabled={!valid || loading}>
            {loading ? 'Analyzing...' : '🔍 Analyze Invoice'}
          </button>
        </div>

        {error && <p style={{ color: 'red', marginTop: 12, fontSize: 13 }}>{error}</p>}
      </div>

      {loading && <div className="spinner" />}

      {report && (
        <div className="card">
          <RiskReport report={report} />
        </div>
      )}
    </>
  )
}
