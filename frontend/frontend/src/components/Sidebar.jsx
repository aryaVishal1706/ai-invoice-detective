export default function Sidebar({ page, setPage }) {
  const links = [
    { id: 'analyze', label: '🔍 Analyze Invoice' },
    { id: 'history', label: '📋 History' },
  ]

  return (
    <aside className="sidebar">
      <div className="logo">Invoice <span>Detective</span></div>
      {links.map(l => (
        <a
          key={l.id}
          className={page === l.id ? 'active' : ''}
          onClick={() => setPage(l.id)}
          style={{ cursor: 'pointer' }}
        >
          {l.label}
        </a>
      ))}
    </aside>
  )
}
