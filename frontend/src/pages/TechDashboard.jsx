import { useState, useEffect, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Ticket, Clock, CheckCircle, AlertCircle, ArrowLeft,
  Search, Filter, RefreshCw, MessageSquare, User, Calendar, Moon, Sun
} from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'
import axios from 'axios'

// Status badge component
const StatusBadge = ({ status }) => {
  const config = {
    'OPEN': { color: '#00ff41', bg: 'rgba(0, 255, 65, 0.15)', icon: AlertCircle },
    'IN_PROGRESS': { color: '#4ecdc4', bg: 'rgba(78, 205, 196, 0.15)', icon: Clock },
    'WAITING': { color: '#ffe66d', bg: 'rgba(255, 230, 109, 0.15)', icon: Clock },
    'RESOLVED': { color: '#39ff14', bg: 'rgba(57, 255, 20, 0.15)', icon: CheckCircle },
    'CLOSED': { color: '#6c757d', bg: 'rgba(108, 117, 125, 0.15)', icon: CheckCircle }
  }
  const { color, bg, icon: Icon } = config[status] || config['OPEN']
  
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '6px',
      padding: '4px 12px', borderRadius: '4px',
      background: bg, border: `1px solid ${color}`, color,
      fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 600,
      textTransform: 'uppercase'
    }}>
      <Icon size={12} />
      {status.replace('_', ' ')}
    </span>
  )
}

// Priority badge
const PriorityBadge = ({ priority }) => {
  const colors = {
    'LOW': '#6c757d',
    'MEDIUM': '#4ecdc4',
    'HIGH': '#ffe66d',
    'CRITICAL': '#ff6b6b'
  }
  const color = colors[priority] || colors['MEDIUM']
  
  return (
    <span style={{
      padding: '2px 8px', borderRadius: '4px',
      border: `1px solid ${color}`, color,
      fontFamily: 'var(--font-mono)', fontSize: '0.65rem', fontWeight: 600,
      textTransform: 'uppercase'
    }}>
      {priority}
    </span>
  )
}

function TechDashboard() {
  const navigate = useNavigate()
  const { token, user, theme, toggleTheme } = useContext(AuthContext)
  
  // State
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [viewMode, setViewMode] = useState('assigned') // 'assigned' or 'all'

  useEffect(() => {
    fetchTickets()
  }, [])

  const fetchTickets = async () => {
    setLoading(true)
    try {
      const response = await axios.get(`${API_CONFIG.baseUrl}/tickets`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setTickets(response.data.tickets || response.data || [])
    } catch (err) {
      console.error('Failed to fetch tickets:', err)
    } finally {
      setLoading(false)
    }
  }

  // Filter tickets
  const filteredTickets = tickets.filter(ticket => {
    // Search filter
    const matchesSearch = !searchQuery || 
      ticket.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.ticketId?.includes(searchQuery)
    
    // Status filter
    const matchesStatus = !statusFilter || ticket.status === statusFilter
    
    // View mode filter (assigned to me vs all)
    const matchesView = viewMode === 'all' || ticket.assignedTo === user?.sub
    
    return matchesSearch && matchesStatus && matchesView
  })

  // Stats
  const myTickets = tickets.filter(t => t.assignedTo === user?.sub)
  const openCount = myTickets.filter(t => t.status === 'OPEN').length
  const inProgressCount = myTickets.filter(t => t.status === 'IN_PROGRESS').length
  const resolvedCount = myTickets.filter(t => t.status === 'RESOLVED').length

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 24px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* FIXED: Back button now goes to /tech instead of /dashboard for consistency */}
          <button 
            onClick={() => navigate('/dashboard')}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
              borderRadius: '6px', padding: '8px 16px', color: 'var(--text-primary)',
              cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.85rem'
            }}
          >
            <ArrowLeft size={16} />
            Back
          </button>
          
          <h1 style={{ 
            fontFamily: 'var(--font-mono)', 
            fontSize: '1.2rem',
            color: 'var(--accent-primary)'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>&gt;_ </span>
            tech.dashboard()
          </h1>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button 
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'lime' : 'dark'} theme`}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: '40px', height: '40px',
              background: 'var(--bg-panel)', 
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--accent-primary)',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            padding: '6px 14px', borderRadius: '4px',
            background: 'rgba(255, 230, 109, 0.15)', 
            border: '1px solid #ffe66d', 
            color: '#ffe66d',
            fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600,
            textTransform: 'uppercase'
          }}>
            <User size={12} />
            Technician
          </span>
        </div>
      </header>

      {/* Stats cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        padding: '24px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)'
      }}>
        {/* FIXED: My Tickets card is now YELLOW to match Technician color scheme */}
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid #ffe66d',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            color: '#ffe66d',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            marginBottom: '8px'
          }}>
            <Ticket size={16} />
            My Tickets
          </div>
          <div style={{ 
            fontSize: '2rem', 
            fontWeight: 700, 
            color: '#ffe66d',
            fontFamily: 'var(--font-mono)'
          }}>
            {myTickets.length}
          </div>
        </div>
        
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            color: '#00ff41',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            marginBottom: '8px'
          }}>
            <AlertCircle size={16} />
            Open
          </div>
          <div style={{ 
            fontSize: '2rem', 
            fontWeight: 700, 
            color: '#00ff41',
            fontFamily: 'var(--font-mono)'
          }}>
            {openCount}
          </div>
        </div>
        
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            color: '#4ecdc4',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            marginBottom: '8px'
          }}>
            <Clock size={16} />
            In Progress
          </div>
          <div style={{ 
            fontSize: '2rem', 
            fontWeight: 700, 
            color: '#4ecdc4',
            fontFamily: 'var(--font-mono)'
          }}>
            {inProgressCount}
          </div>
        </div>
        
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            color: '#39ff14',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            marginBottom: '8px'
          }}>
            <CheckCircle size={16} />
            Resolved
          </div>
          <div style={{ 
            fontSize: '2rem', 
            fontWeight: 700, 
            color: '#39ff14',
            fontFamily: 'var(--font-mono)'
          }}>
            {resolvedCount}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '16px 24px',
        flexWrap: 'wrap'
      }}>
        {/* View toggle - FIXED: My Tickets button is now yellow when active */}
        <div style={{
          display: 'flex',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid var(--border-color)'
        }}>
          <button
            onClick={() => setViewMode('assigned')}
            style={{
              padding: '8px 16px',
              background: viewMode === 'assigned' ? '#ffe66d' : 'transparent',
              border: 'none',
              color: viewMode === 'assigned' ? 'var(--bg-primary)' : 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              cursor: 'pointer',
              fontWeight: viewMode === 'assigned' ? 600 : 400
            }}
          >
            My Tickets
          </button>
          <button
            onClick={() => setViewMode('all')}
            style={{
              padding: '8px 16px',
              background: viewMode === 'all' ? 'var(--accent-primary)' : 'transparent',
              border: 'none',
              color: viewMode === 'all' ? 'var(--bg-primary)' : 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              cursor: 'pointer',
              fontWeight: viewMode === 'all' ? 600 : 400
            }}
          >
            All Tickets
          </button>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', flex: '1', minWidth: '200px', maxWidth: '400px' }}>
          <Search size={18} style={{ 
            position: 'absolute', left: '12px', top: '50%', 
            transform: 'translateY(-50%)', color: 'var(--text-muted)' 
          }} />
          <input
            type="text"
            placeholder="Search tickets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 16px 10px 44px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.9rem',
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              color: 'var(--text-primary)'
            }}
          />
        </div>

        {/* Status filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Filter size={16} style={{ color: 'var(--text-muted)' }} />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: '10px 16px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.9rem',
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              cursor: 'pointer'
            }}
          >
            <option value="">All Status</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="WAITING">Waiting</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>

        {/* Refresh */}
        <button
          onClick={fetchTickets}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 16px',
            background: 'var(--bg-panel)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            color: 'var(--text-secondary)',
            cursor: 'pointer'
          }}
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Tickets list */}
      <div style={{ padding: '0 24px 24px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto' }} />
          </div>
        ) : filteredTickets.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '60px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px'
          }}>
            <Ticket size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
            <h3 style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              No tickets found
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              {viewMode === 'assigned' 
                ? 'No tickets are currently assigned to you.'
                : 'No tickets match your filters.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filteredTickets.map(ticket => (
              <div
                key={ticket.ticketId}
                onClick={() => navigate(`/tickets/${ticket.ticketId}`)}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '20px',
                  cursor: 'pointer',
                  transition: 'border-color 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
              >
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'flex-start',
                  marginBottom: '12px'
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <span style={{ 
                        fontFamily: 'var(--font-mono)', 
                        fontSize: '0.75rem',
                        color: 'var(--accent-primary)'
                      }}>
                        {ticket.ticketId.substring(0, 8)}...
                      </span>
                      <PriorityBadge priority={ticket.priority} />
                    </div>
                    <h3 style={{ 
                      fontFamily: 'var(--font-mono)', 
                      fontSize: '1rem',
                      color: 'var(--text-primary)',
                      marginBottom: '8px'
                    }}>
                      {ticket.title}
                    </h3>
                    <p style={{ 
                      color: 'var(--text-muted)', 
                      fontSize: '0.85rem',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden'
                    }}>
                      {ticket.description}
                    </p>
                  </div>
                  <StatusBadge status={ticket.status} />
                </div>
                
                <div style={{ 
                  display: 'flex', 
                  gap: '20px',
                  color: 'var(--text-muted)',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <User size={12} />
                    {ticket.createdByEmail?.split('@')[0] || 'Unknown'}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Calendar size={12} />
                    {new Date(ticket.createdAt).toLocaleDateString()}
                  </span>
                  {ticket.lastCommentAt && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-primary)' }}>
                      <MessageSquare size={12} />
                      New activity
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        input:focus, select:focus {
          outline: none;
          border-color: var(--accent-primary) !important;
        }
        .spinner {
          border: 3px solid var(--border-color);
          border-top-color: var(--accent-primary);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default TechDashboard
