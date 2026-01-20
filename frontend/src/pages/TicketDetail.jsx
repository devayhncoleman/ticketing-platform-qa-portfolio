import { useState, useEffect, useContext } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { 
  Terminal, ArrowLeft, Ticket, Clock, AlertCircle, CheckCircle, 
  User, Calendar, Tag, Edit3, Save, X, Trash2, MessageSquare
} from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'
import axios from 'axios'

// The Winning Team Logo
const WinningTeamLogo = ({ size = 24 }) => (
  <svg viewBox="0 0 120 120" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
    <circle cx="60" cy="60" r="52" fill="#1a1a2e" stroke="currentColor" strokeWidth="2"/>
    <circle cx="60" cy="60" r="42" fill="#0d0d1a" stroke="currentColor" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="32" fill="#1a1a2e" stroke="currentColor" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="6" fill="currentColor" opacity="0.5"/>
    <g transform="translate(60, 62) rotate(12)">
      <path d="M-14,-22 L-11,-6 Q-11,7 0,11 Q11,7 11,-6 L14,-22 Z" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
      <polygon points="0,-14 1.5,-9 7,-9 2.5,-5 4,1 0,-2 -4,1 -2.5,-5 -7,-9 -1.5,-9" fill="currentColor" opacity="0.9"/>
    </g>
    <g transform="translate(60, 60)">
      <line x1="0" y1="0" x2="32" y2="32" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
      <g transform="translate(32, 32) rotate(45)">
        <path d="M0,0 L0,-18 L6,-12 L0,-6 L-6,-12 Z" fill="currentColor" opacity="0.9"/>
      </g>
    </g>
  </svg>
)

function TicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, token, logout } = useContext(AuthContext)
  
  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    status: '',
    priority: '',
    category: ''
  })

  useEffect(() => {
    fetchTicket()
  }, [id])

  const fetchTicket = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.get(`${API_CONFIG.baseUrl}/tickets/${id}`, {
        headers: { Authorization: token }
      })
      setTicket(response.data)
      setEditForm({
        title: response.data.title,
        description: response.data.description,
        status: response.data.status,
        priority: response.data.priority,
        category: response.data.category
      })
    } catch (err) {
      if (err.response?.status === 401) {
        logout()
        navigate('/login')
      } else if (err.response?.status === 404) {
        setError('Ticket not found')
      } else {
        setError('Failed to load ticket')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      const response = await axios.patch(
        `${API_CONFIG.baseUrl}/tickets/${id}`,
        editForm,
        { headers: { Authorization: token, 'Content-Type': 'application/json' } }
      )
      setTicket(response.data)
      setIsEditing(false)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update ticket')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await axios.delete(`${API_CONFIG.baseUrl}/tickets/${id}`, {
        headers: { Authorization: token }
      })
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete ticket')
      setDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'OPEN': return <AlertCircle size={16} />
      case 'IN_PROGRESS': return <Clock size={16} />
      case 'RESOLVED': case 'CLOSED': return <CheckCircle size={16} />
      default: return <Ticket size={16} />
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="ticket-detail-page">
        <div className="loading-container">
          <div className="spinner" style={{ width: 48, height: 48 }}></div>
          <p>Loading ticket...</p>
        </div>
        <style>{styles}</style>
      </div>
    )
  }

  if (error && !ticket) {
    return (
      <div className="ticket-detail-page">
        <div className="error-container">
          <AlertCircle size={48} />
          <h2>{error}</h2>
          <Link to="/dashboard" className="btn btn-primary btn-with-icon">
            <ArrowLeft size={18} /><span>Back to Dashboard</span>
          </Link>
        </div>
        <style>{styles}</style>
      </div>
    )
  }

  return (
    <div className="ticket-detail-page">
      {/* Header */}
      <header className="detail-header">
        <div className="header-left">
          <Link to="/dashboard" className="back-link">
            <ArrowLeft size={20} />
            <span>Back</span>
          </Link>
          <div className="header-title">
            <h1>
              <Terminal size={24} />
              ticket.view("{id.slice(0, 8)}...")
            </h1>
          </div>
        </div>
        <div className="header-actions">
          {!isEditing ? (
            <>
              <button className="btn btn-ghost btn-with-icon" onClick={() => setIsEditing(true)}>
                <Edit3 size={18} /><span>Edit</span>
              </button>
              <button className="btn btn-danger btn-with-icon" onClick={() => setShowDeleteConfirm(true)}>
                <Trash2 size={18} /><span>Delete</span>
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost btn-with-icon" onClick={() => { setIsEditing(false); setEditForm({ title: ticket.title, description: ticket.description, status: ticket.status, priority: ticket.priority, category: ticket.category }) }}>
                <X size={18} /><span>Cancel</span>
              </button>
              <button className="btn btn-primary btn-with-icon" onClick={handleSave} disabled={saving}>
                {saving ? <><div className="spinner"></div><span>Saving...</span></> : <><Save size={18} /><span>Save Changes</span></>}
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="detail-content">
        {error && <div className="error-banner"><AlertCircle size={18} />{error}</div>}

        <div className="content-grid">
          {/* Left Column - Main Info */}
          <div className="main-column">
            <div className="schema-card">
              <div className="schema-card-header">
                <Ticket size={16} className="icon" />
                <span className="title">ticket.details</span>
                <span className={`badge ${getPriorityClass(ticket.priority)}`}>{ticket.priority}</span>
              </div>
              <div className="schema-card-body">
                {isEditing ? (
                  <>
                    <div className="input-group">
                      <label className="input-label">TITLE</label>
                      <input
                        type="text"
                        className="input-field"
                        value={editForm.title}
                        onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                      />
                    </div>
                    <div className="input-group">
                      <label className="input-label">DESCRIPTION</label>
                      <textarea
                        className="input-field textarea"
                        rows={6}
                        value={editForm.description}
                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <h2 className="ticket-title">{ticket.title}</h2>
                    <p className="ticket-description">{ticket.description}</p>
                  </>
                )}
              </div>
            </div>

            {/* Comments Section Placeholder */}
            <div className="schema-card">
              <div className="schema-card-header">
                <MessageSquare size={16} className="icon" />
                <span className="title">ticket.comments</span>
              </div>
              <div className="schema-card-body">
                <div className="comments-placeholder">
                  <MessageSquare size={32} />
                  <p>Comments feature coming soon</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Metadata */}
          <div className="sidebar-column">
            <div className="schema-card">
              <div className="schema-card-header">
                <Tag size={16} className="icon" />
                <span className="title">ticket.metadata</span>
              </div>
              <div className="schema-card-body">
                {/* Status */}
                <div className="meta-field">
                  <span className="meta-label">Status</span>
                  {isEditing ? (
                    <select
                      className="input-field select-field"
                      value={editForm.status}
                      onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                    >
                      <option value="OPEN">Open</option>
                      <option value="IN_PROGRESS">In Progress</option>
                      <option value="WAITING">Waiting</option>
                      <option value="RESOLVED">Resolved</option>
                      <option value="CLOSED">Closed</option>
                    </select>
                  ) : (
                    <span className={`badge ${getStatusClass(ticket.status)}`}>
                      {getStatusIcon(ticket.status)}
                      {ticket.status.replace('_', ' ')}
                    </span>
                  )}
                </div>

                {/* Priority */}
                <div className="meta-field">
                  <span className="meta-label">Priority</span>
                  {isEditing ? (
                    <select
                      className="input-field select-field"
                      value={editForm.priority}
                      onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
                    >
                      <option value="LOW">Low</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HIGH">High</option>
                      <option value="CRITICAL">Critical</option>
                    </select>
                  ) : (
                    <span className={`badge ${getPriorityClass(ticket.priority)}`}>{ticket.priority}</span>
                  )}
                </div>

                {/* Category */}
                <div className="meta-field">
                  <span className="meta-label">Category</span>
                  {isEditing ? (
                    <select
                      className="input-field select-field"
                      value={editForm.category}
                      onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                    >
                      <option value="General">General</option>
                      <option value="Bug">Bug</option>
                      <option value="Feature">Feature Request</option>
                      <option value="Support">Support</option>
                    </select>
                  ) : (
                    <span className="meta-value">{ticket.category}</span>
                  )}
                </div>

                <div className="meta-divider"></div>

                {/* Created */}
                <div className="meta-field">
                  <span className="meta-label"><Calendar size={14} /> Created</span>
                  <span className="meta-value meta-date">{formatDate(ticket.createdAt)}</span>
                </div>

                {/* Updated */}
                <div className="meta-field">
                  <span className="meta-label"><Clock size={14} /> Updated</span>
                  <span className="meta-value meta-date">{formatDate(ticket.updatedAt)}</span>
                </div>

                {/* Created By */}
                <div className="meta-field">
                  <span className="meta-label"><User size={14} /> Created By</span>
                  <span className="meta-value">{ticket.createdBy || 'Unknown'}</span>
                </div>

                {/* Ticket ID */}
                <div className="meta-field">
                  <span className="meta-label">Ticket ID</span>
                  <code className="meta-code">{ticket.ticketId}</code>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="modal-overlay" onClick={() => setShowDeleteConfirm(false)}>
          <div className="modal schema-card" onClick={(e) => e.stopPropagation()}>
            <div className="schema-card-header">
              <Trash2 size={16} className="icon" style={{ color: 'var(--priority-critical)' }} />
              <span className="title">ticket.delete()</span>
            </div>
            <div className="schema-card-body" style={{ textAlign: 'center', padding: '32px 24px' }}>
              <AlertCircle size={48} style={{ color: 'var(--priority-critical)', marginBottom: 16 }} />
              <h3 style={{ marginBottom: 8 }}>Delete this ticket?</h3>
              <p className="text-muted" style={{ marginBottom: 24 }}>This action cannot be undone.</p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                <button className="btn btn-ghost" onClick={() => setShowDeleteConfirm(false)}>Cancel</button>
                <button className="btn btn-danger btn-with-icon" onClick={handleDelete} disabled={deleting}>
                  {deleting ? <><div className="spinner"></div><span>Deleting...</span></> : <><Trash2 size={18} /><span>Delete Ticket</span></>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{styles}</style>
    </div>
  )
}

const styles = `
  .ticket-detail-page {
    min-height: 100vh;
    background: var(--bg-primary);
  }

  .loading-container, .error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    color: var(--text-muted);
    gap: 16px;
  }

  .error-container svg {
    color: var(--priority-critical);
  }

  .detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 32px;
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-secondary);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .back-link {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.9rem;
    padding: 8px 16px;
    background: var(--bg-panel);
    border-radius: 8px;
    transition: all 0.2s;
  }

  .back-link:hover {
    color: var(--accent-primary);
    background: var(--bg-card);
  }

  .header-title h1 {
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: var(--font-mono);
    font-size: 1.25rem;
    color: var(--accent-primary);
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }

  .btn-with-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .btn-danger {
    background: rgba(255, 107, 107, 0.1);
    border: 1px solid var(--priority-critical);
    color: var(--priority-critical);
  }

  .btn-danger:hover {
    background: rgba(255, 107, 107, 0.2);
  }

  .detail-content {
    padding: 32px;
    max-width: 1400px;
    margin: 0 auto;
  }

  .error-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: rgba(255, 107, 107, 0.1);
    border: 1px solid var(--priority-critical);
    border-radius: 8px;
    color: var(--priority-critical);
    margin-bottom: 24px;
    font-family: var(--font-mono);
  }

  .content-grid {
    display: grid;
    grid-template-columns: 1fr 350px;
    gap: 24px;
  }

  @media (max-width: 1024px) {
    .content-grid {
      grid-template-columns: 1fr;
    }
  }

  .main-column {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .ticket-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
  }

  .ticket-description {
    color: var(--text-secondary);
    line-height: 1.7;
    white-space: pre-wrap;
  }

  .textarea {
    resize: vertical;
    min-height: 150px;
  }

  .comments-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px;
    color: var(--text-muted);
    opacity: 0.5;
  }

  .comments-placeholder svg {
    margin-bottom: 12px;
  }

  .sidebar-column .schema-card-body {
    padding: 16px;
  }

  .meta-field {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border-color);
  }

  .meta-field:last-child {
    border-bottom: none;
  }

  .meta-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
  }

  .meta-value {
    font-family: var(--font-mono);
    font-size: 0.9rem;
    color: var(--text-primary);
  }

  .meta-date {
    font-size: 0.8rem;
    color: var(--text-secondary);
  }

  .meta-code {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--accent-primary);
    background: var(--bg-panel);
    padding: 4px 8px;
    border-radius: 4px;
    word-break: break-all;
  }

  .meta-divider {
    height: 1px;
    background: var(--border-color);
    margin: 8px 0;
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 24px;
  }

  .modal {
    width: 100%;
    max-width: 400px;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
`

export default TicketDetail
