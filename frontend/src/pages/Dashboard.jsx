import { useState, useEffect, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Terminal, LogOut, Plus, RefreshCw, Sun, Moon,
  Ticket, Clock, AlertCircle, CheckCircle, User, Filter, Search, X
} from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'
import axios from 'axios'

// The Winning Team Logo - Dart from Southeast (we see back/fins)
const WinningTeamLogo = ({ size = 24 }) => (
  <svg viewBox="0 0 120 120" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
    <circle cx="60" cy="60" r="52" fill="#1a1a2e" stroke="currentColor" strokeWidth="2"/>
    <circle cx="60" cy="60" r="42" fill="#0d0d1a" stroke="currentColor" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="32" fill="#1a1a2e" stroke="currentColor" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="22" fill="#0d0d1a" stroke="currentColor" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="12" fill="#1a1a2e" stroke="currentColor" strokeWidth="1" strokeOpacity="0.5"/>
    <circle cx="60" cy="60" r="6" fill="currentColor" opacity="0.5"/>
    <circle cx="60" cy="60" r="3" fill="currentColor" opacity="0.8"/>
    <g transform="translate(60, 62) rotate(12)">
      <path d="M-14,-22 L-11,-6 Q-11,7 0,11 Q11,7 11,-6 L14,-22 Z" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
      <path d="M-14,-17 Q-21,-17 -21,-9 Q-21,-1 -14,-1" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      <path d="M14,-17 Q21,-17 21,-9 Q21,-1 14,-1" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      <line x1="0" y1="11" x2="0" y2="19" stroke="currentColor" strokeWidth="2.5"/>
      <path d="M-9,19 L9,19 L11,24 L-11,24 Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <polygon points="0,-14 1.5,-9 7,-9 2.5,-5 4,1 0,-2 -4,1 -2.5,-5 -7,-9 -1.5,-9" fill="currentColor" opacity="0.9"/>
    </g>
    {/* DART - From SOUTHEAST */}
    <g transform="translate(60, 60)">
      <line x1="0" y1="0" x2="32" y2="32" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
      <line x1="18" y1="18" x2="26" y2="26" stroke="currentColor" strokeWidth="6" strokeLinecap="round"/>
      <g transform="translate(32, 32) rotate(45)">
        <path d="M0,0 L0,-18 L6,-12 L0,-6 L-6,-12 Z" fill="currentColor" opacity="0.9"/>
        <path d="M0,0 L-18,0 L-12,-6 L-6,0 L-12,6 Z" fill="currentColor" opacity="0.7"/>
        <path d="M0,0 L18,0 L12,-6 L6,0 L12,6 Z" fill="currentColor" opacity="0.7"/>
      </g>
    </g>
    <g transform="translate(60, 60)">
      <line x1="-5" y1="-5" x2="-12" y2="-12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.8"/>
      <line x1="0" y1="-7" x2="0" y2="-14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.7"/>
      <line x1="-7" y1="0" x2="-14" y2="0" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.7"/>
    </g>
  </svg>
)

function Dashboard() {
  const { user, token, logout, theme, toggleTheme } = useContext(AuthContext)
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()

  const fetchTickets = async () => {
    setLoading(true)
    setError('')
    try {
      const url = statusFilter ? `${API_CONFIG.baseUrl}/tickets?status=${statusFilter}` : `${API_CONFIG.baseUrl}/tickets`
      const response = await axios.get(url, { headers: { Authorization: token } })
      setTickets(response.data.tickets || [])
    } catch (err) {
      if (err.response?.status === 401) { logout(); navigate('/login') }
      else setError('Failed to load tickets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchTickets() }, [statusFilter])

  const handleLogout = () => { logout(); navigate('/login') }

  // Filter tickets by search query
  const filteredTickets = tickets.filter(ticket => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      ticket.title.toLowerCase().includes(query) ||
      ticket.description.toLowerCase().includes(query) ||
      ticket.category.toLowerCase().includes(query)
    )
  })

  const getStatusIcon = (status) => {
    switch (status) {
      case 'OPEN': return <AlertCircle size={14} />
      case 'IN_PROGRESS': return <Clock size={14} />
      case 'RESOLVED': case 'CLOSED': return <CheckCircle size={14} />
      default: return <Ticket size={14} />
    }
  }

  const getStatusClass = (status) => {
    const classes = { OPEN: 'badge-open', IN_PROGRESS: 'badge-in-progress', WAITING: 'badge-waiting', RESOLVED: 'badge-resolved', CLOSED: 'badge-closed' }
    return classes[status] || ''
  }

  const getPriorityClass = (priority) => {
    const classes = { LOW: 'badge-low', MEDIUM: 'badge-medium', HIGH: 'badge-high', CRITICAL: 'badge-critical' }
    return classes[priority] || ''
  }

  const formatDate = (dateString) => new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo"><WinningTeamLogo size={28} /><span>THE_WINNING_TEAM</span></div>
        </div>
        <nav className="sidebar-nav">
          <a href="#" className="nav-item active"><Ticket size={18} /><span>All Tickets</span></a>
          <a href="#" className="nav-item"><AlertCircle size={18} /><span>Open</span></a>
          <a href="#" className="nav-item"><Clock size={18} /><span>In Progress</span></a>
          <a href="#" className="nav-item"><CheckCircle size={18} /><span>Resolved</span></a>
        </nav>
        <div className="sidebar-footer">
          <div className="user-info" onClick={() => navigate('/profile')} style={{ cursor: 'pointer' }}>
            <div className="user-avatar"><User size={18} /></div>
            <div className="user-details">
              <span className="user-name">{user?.givenName || 'User'}</span>
              <span className="user-email">{user?.email}</span>
            </div>
          </div>
          <button className="btn-icon" onClick={handleLogout} title="Logout"><LogOut size={18} /></button>
        </div>
      </aside>

      <main className="main-content">
        <header className="header">
          <div className="header-left">
            <h1><Terminal size={24} style={{ marginRight: 12 }} />tickets.list()</h1>
            <span className="record-count">{filteredTickets.length} records{searchQuery && ` (filtered)`}</span>
          </div>
          <div className="header-actions">
            <button className="btn-icon" onClick={toggleTheme} title={theme === 'dark' ? 'Light Mode' : 'Dark Mode'}>
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="btn-icon" onClick={fetchTickets} title="Refresh">
              <RefreshCw size={18} className={loading ? 'spin' : ''} />
            </button>
            <button className="btn btn-primary" onClick={() => setShowCreateModal(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} />
              <span>NEW TICKET</span>
            </button>
          </div>
        </header>

        <div className="filters">
          <div className="search-wrapper">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="Search tickets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="search-clear" onClick={() => setSearchQuery('')}>
                <X size={16} />
              </button>
            )}
          </div>
          <div className="filter-group">
            <Filter size={16} />
            <select className="input-field select-field filter-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Status</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="WAITING">Waiting</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>
        </div>

        <div className="content">
          {error && <div className="error-banner"><AlertCircle size={18} />{error}</div>}
          {loading ? (
            <div className="loading-state"><div className="spinner" style={{ width: 40, height: 40 }}></div><p>Loading tickets...</p></div>
          ) : filteredTickets.length === 0 ? (
            <div className="empty-state">
              <WinningTeamLogo size={80} />
              <h3>{searchQuery ? 'No matching tickets' : 'No tickets found'}</h3>
              <p className="text-muted">{searchQuery ? 'Try a different search term' : 'Create your first ticket to get started'}</p>
              {!searchQuery && (
                <button className="btn btn-primary" onClick={() => setShowCreateModal(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginTop: '24px' }}>
                  <Plus size={18} />
                  <span>CREATE TICKET</span>
                </button>
              )}
            </div>
          ) : (
            <div className="tickets-grid">
              {filteredTickets.map(ticket => (
                <div 
                  key={ticket.ticketId} 
                  className="ticket-card schema-card fade-in"
                  onClick={() => navigate(`/tickets/${ticket.ticketId}`)}
                >
                  <div className="schema-card-header">
                    <Ticket size={16} className="icon" />
                    <span className="title">ticket.{ticket.ticketId.slice(0, 8)}</span>
                    <span className={`badge ${getPriorityClass(ticket.priority)}`}>{ticket.priority}</span>
                  </div>
                  <div className="schema-card-body">
                    <h4 className="ticket-title">{ticket.title}</h4>
                    <p className="ticket-description">{ticket.description}</p>
                    <div className="ticket-meta">
                      <div className="schema-field">
                        <span className="schema-field-name">status</span>
                        <span className={`badge ${getStatusClass(ticket.status)}`}>{getStatusIcon(ticket.status)}{ticket.status.replace('_', ' ')}</span>
                      </div>
                      <div className="schema-field">
                        <span className="schema-field-name">created</span>
                        <span className="schema-field-type">{formatDate(ticket.createdAt)}</span>
                      </div>
                      <div className="schema-field">
                        <span className="schema-field-name">category</span>
                        <span className="schema-field-type">{ticket.category}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {showCreateModal && <CreateTicketModal onClose={() => setShowCreateModal(false)} onCreated={() => { setShowCreateModal(false); fetchTickets() }} token={token} />}

      <style>{`
        .dashboard { display: flex; min-height: 100vh; }
        .sidebar { width: 280px; background: var(--bg-secondary); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; position: fixed; top: 0; left: 0; bottom: 0; }
        .sidebar-header { padding: 20px; border-bottom: 1px solid var(--border-color); }
        .logo { display: flex; align-items: center; gap: 12px; font-family: var(--font-mono); font-size: 0.9rem; font-weight: 700; color: var(--accent-primary); }
        .sidebar-nav { flex: 1; padding: 16px 12px; }
        .nav-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; color: var(--text-secondary); border-radius: 8px; margin-bottom: 4px; font-family: var(--font-mono); font-size: 0.9rem; }
        .nav-item:hover, .nav-item.active { background: var(--bg-panel); color: var(--accent-primary); }
        .sidebar-footer { padding: 16px; border-top: 1px solid var(--border-color); display: flex; align-items: center; gap: 12px; }
        .user-info { flex: 1; display: flex; align-items: center; gap: 12px; min-width: 0; padding: 8px; border-radius: 8px; transition: background 0.2s; }
        .user-info:hover { background: var(--bg-panel); }
        .user-avatar { width: 36px; height: 36px; flex-shrink: 0; background: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: var(--accent-primary); }
        .user-details { display: flex; flex-direction: column; min-width: 0; }
        .user-name { font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-primary); }
        .user-email { font-size: 0.7rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .main-content { flex: 1; margin-left: 280px; display: flex; flex-direction: column; }
        .header { display: flex; align-items: center; justify-content: space-between; padding: 20px 32px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); }
        .header-left { display: flex; align-items: center; gap: 16px; }
        .header-left h1 { display: flex; align-items: center; font-family: var(--font-mono); font-size: 1.25rem; color: var(--accent-primary); }
        .record-count { font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted); padding: 4px 12px; background: var(--bg-panel); border-radius: 4px; }
        .header-actions { display: flex; align-items: center; gap: 12px; }
        .btn-icon { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; background: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-secondary); cursor: pointer; }
        .btn-icon:hover { color: var(--accent-primary); border-color: var(--accent-primary); }
        .btn-with-icon { display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
        .spin { animation: spin 1s linear infinite; }
        .filters { padding: 16px 32px; border-bottom: 1px solid var(--border-color); display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
        .search-wrapper { position: relative; flex: 1; min-width: 200px; max-width: 400px; }
        .search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; }
        .search-input { width: 100%; padding: 10px 40px 10px 44px; font-family: var(--font-mono); font-size: 0.9rem; color: var(--text-primary); background: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 8px; }
        .search-input:focus { outline: none; border-color: var(--accent-primary); }
        .search-input::placeholder { color: var(--text-muted); }
        .search-clear { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; display: flex; }
        .search-clear:hover { color: var(--accent-primary); }
        .filter-group { display: flex; align-items: center; gap: 8px; color: var(--text-muted); }
        .filter-select { width: auto; padding: 8px 36px 8px 12px; font-size: 0.85rem; }
        .content { flex: 1; padding: 32px; overflow-y: auto; }
        .error-banner { display: flex; align-items: center; gap: 12px; padding: 16px; background: rgba(255, 107, 107, 0.1); border: 1px solid var(--priority-critical); border-radius: 8px; color: var(--priority-critical); margin-bottom: 24px; }
        .loading-state, .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 24px; color: var(--text-muted); text-align: center; }
        .empty-state svg { color: var(--accent-primary); opacity: 0.3; margin-bottom: 24px; }
        .empty-state h3 { margin-bottom: 8px; }
        .empty-state .btn { margin-top: 24px; }
        .tickets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; }
        .ticket-card { cursor: pointer; }
        .ticket-card:hover { transform: translateY(-2px); }
        .ticket-title { font-size: 1rem; margin-bottom: 8px; color: var(--text-primary); }
        .ticket-description { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .ticket-meta .schema-field { padding: 6px 0; }
        .ticket-meta .badge { display: inline-flex; align-items: center; gap: 4px; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
          .sidebar { display: none; }
          .main-content { margin-left: 0; }
          .header { padding: 16px; flex-wrap: wrap; gap: 12px; }
          .header-left { flex: 1 1 100%; }
          .header-left h1 { font-size: 1rem; }
          .header-actions { width: 100%; justify-content: space-between; }
          .filters { padding: 12px 16px; flex-direction: column; align-items: stretch; }
          .search-wrapper { max-width: none; }
          .content { padding: 16px; }
          .tickets-grid { grid-template-columns: 1fr; gap: 16px; }
          .record-count { display: none; }
        }
      `}</style>
    </div>
  )
}

function CreateTicketModal({ onClose, onCreated, token }) {
  const [formData, setFormData] = useState({ title: '', description: '', priority: 'MEDIUM', category: 'General' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await axios.post(`${API_CONFIG.baseUrl}/tickets`, formData, { headers: { Authorization: token, 'Content-Type': 'application/json' } })
      onCreated()
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create ticket')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal schema-card" onClick={e => e.stopPropagation()}>
        <div className="schema-card-header"><Plus size={16} className="icon" /><span className="title">ticket.create()</span></div>
        <div className="schema-card-body">
          <form onSubmit={handleSubmit}>
            {error && <div className="error-message"><AlertCircle size={16} />{error}</div>}
            <div className="input-group">
              <label className="input-label">TITLE</label>
              <input type="text" className="input-field" placeholder="Enter ticket title" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} required />
            </div>
            <div className="input-group">
              <label className="input-label">DESCRIPTION</label>
              <textarea className="input-field textarea" placeholder="Describe the issue..." rows={4} value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} required />
            </div>
            <div className="form-row">
              <div className="input-group">
                <label className="input-label">PRIORITY</label>
                <select className="input-field select-field" value={formData.priority} onChange={e => setFormData({...formData, priority: e.target.value})}>
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">CATEGORY</label>
                <select className="input-field select-field" value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})}>
                  <option value="General">General</option>
                  <option value="Bug">Bug</option>
                  <option value="Feature">Feature Request</option>
                  <option value="Support">Support</option>
                </select>
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={onClose}>CANCEL</button>
              <button type="submit" className="btn btn-primary btn-with-icon" disabled={loading}>
                {loading ? <><div className="spinner"></div><span>CREATING...</span></> : <><Plus size={18} /><span>CREATE TICKET</span></>}
              </button>
            </div>
          </form>
        </div>
      </div>
      <style>{`
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 24px; }
        .modal { width: 100%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .textarea { resize: vertical; min-height: 100px; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; padding-top: 24px; border-top: 1px solid var(--border-color); }
        .error-message { display: flex; align-items: center; gap: 8px; padding: 12px; background: rgba(255, 107, 107, 0.1); border: 1px solid var(--priority-critical); border-radius: 6px; color: var(--priority-critical); font-size: 0.85rem; margin-bottom: 20px; }
        .btn-with-icon { display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
      `}</style>
    </div>
  )
}

export default Dashboard
