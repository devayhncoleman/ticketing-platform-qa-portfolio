import { useState, useEffect, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Users, Shield, ArrowLeft, Search, UserPlus, Edit2, 
  Ticket, CheckCircle, Clock, AlertCircle, RefreshCw,
  ChevronDown, X, User, Mail, Moon, Sun
} from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'
import axios from 'axios'

// Role badge component
const RoleBadge = ({ role }) => {
  const config = {
    'CUSTOMER': { color: '#4ecdc4', label: 'Customer' },
    'TECH': { color: '#ffe66d', label: 'Technician' },
    'ADMIN': { color: '#ff6b6b', label: 'Admin' }
  }
  const { color, label } = config[role] || config['CUSTOMER']
  
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      padding: '4px 10px', borderRadius: '4px',
      background: `${color}22`, border: `1px solid ${color}`, color,
      fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 600,
      textTransform: 'uppercase'
    }}>
      <Shield size={10} />
      {label}
    </span>
  )
}

// Status badge for tickets
const StatusBadge = ({ status }) => {
  const config = {
    'OPEN': { color: '#00ff41', icon: AlertCircle },
    'IN_PROGRESS': { color: '#4ecdc4', icon: Clock },
    'RESOLVED': { color: '#39ff14', icon: CheckCircle },
    'CLOSED': { color: '#6c757d', icon: CheckCircle }
  }
  const { color, icon: Icon } = config[status] || config['OPEN']
  
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      padding: '2px 8px', borderRadius: '4px',
      background: `${color}22`, color,
      fontFamily: 'var(--font-mono)', fontSize: '0.65rem', fontWeight: 600,
      textTransform: 'uppercase'
    }}>
      <Icon size={10} />
      {status.replace('_', ' ')}
    </span>
  )
}

function AdminConsole() {
  const navigate = useNavigate()
  const { token, user, theme, toggleTheme } = useContext(AuthContext)
  
  // Tab state
  const [activeTab, setActiveTab] = useState('users')
  
  // Users state
  const [users, setUsers] = useState([])
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [userSearch, setUserSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  
  // Tickets state (for assignment)
  const [tickets, setTickets] = useState([])
  const [loadingTickets, setLoadingTickets] = useState(true)
  const [ticketSearch, setTicketSearch] = useState('')
  
  // Technicians (for assignment dropdown)
  const [technicians, setTechnicians] = useState([])
  
  // Modal state
  const [editingUser, setEditingUser] = useState(null)
  const [assigningTicket, setAssigningTicket] = useState(null)
  const [selectedTech, setSelectedTech] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchUsers()
    fetchTickets()
    fetchTechnicians()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API_CONFIG.baseUrl}/users`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(response.data.users || [])
    } catch (err) {
      console.error('Failed to fetch users:', err)
    } finally {
      setLoadingUsers(false)
    }
  }

  const fetchTickets = async () => {
    try {
      const response = await axios.get(`${API_CONFIG.baseUrl}/tickets`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setTickets(response.data.tickets || response.data || [])
    } catch (err) {
      console.error('Failed to fetch tickets:', err)
    } finally {
      setLoadingTickets(false)
    }
  }

  const fetchTechnicians = async () => {
    try {
      const response = await axios.get(`${API_CONFIG.baseUrl}/technicians`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setTechnicians(response.data.technicians || [])
    } catch (err) {
      console.error('Failed to fetch technicians:', err)
    }
  }

  const handleUpdateRole = async (userId, newRole) => {
    setSaving(true)
    try {
      await axios.patch(
        `${API_CONFIG.baseUrl}/users/${userId}/role`,
        { role: newRole },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setUsers(prev => prev.map(u => 
        u.userId === userId ? { ...u, role: newRole } : u
      ))
      setEditingUser(null)
    } catch (err) {
      console.error('Failed to update role:', err)
      alert('Failed to update user role')
    } finally {
      setSaving(false)
    }
  }

  const handleAssignTicket = async () => {
    if (!selectedTech || !assigningTicket) return
    
    setSaving(true)
    try {
      await axios.post(
        `${API_CONFIG.baseUrl}/tickets/${assigningTicket.ticketId}/assign`,
        { technicianId: selectedTech },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      // Refresh tickets
      await fetchTickets()
      setAssigningTicket(null)
      setSelectedTech('')
    } catch (err) {
      console.error('Failed to assign ticket:', err)
      alert('Failed to assign ticket')
    } finally {
      setSaving(false)
    }
  }

  // Filter users
  const filteredUsers = users.filter(u => {
    const matchesSearch = !userSearch || 
      u.email?.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.firstName?.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.lastName?.toLowerCase().includes(userSearch.toLowerCase())
    const matchesRole = !roleFilter || u.role === roleFilter
    return matchesSearch && matchesRole
  })

  // Filter tickets (unassigned or all)
  const filteredTickets = tickets.filter(t => {
    const matchesSearch = !ticketSearch ||
      t.title?.toLowerCase().includes(ticketSearch.toLowerCase()) ||
      t.ticketId?.includes(ticketSearch)
    return matchesSearch
  })

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
            admin.console()
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
          
          <RoleBadge role="ADMIN" />
        </div>
      </header>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '0',
        padding: '0 24px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <button
          onClick={() => setActiveTab('users')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '16px 24px',
            background: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'users' ? '2px solid var(--accent-primary)' : '2px solid transparent',
            color: activeTab === 'users' ? 'var(--accent-primary)' : 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.9rem',
            cursor: 'pointer'
          }}
        >
          <Users size={18} />
          User Management
        </button>
        <button
          onClick={() => setActiveTab('tickets')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '16px 24px',
            background: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'tickets' ? '2px solid var(--accent-primary)' : '2px solid transparent',
            color: activeTab === 'tickets' ? 'var(--accent-primary)' : 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.9rem',
            cursor: 'pointer'
          }}
        >
          <Ticket size={18} />
          Ticket Assignment
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: '24px' }}>
        {activeTab === 'users' ? (
          <>
            {/* Users tab */}
            <div style={{ 
              display: 'flex', 
              gap: '16px', 
              marginBottom: '24px',
              flexWrap: 'wrap'
            }}>
              {/* Search */}
              <div style={{ position: 'relative', flex: '1', minWidth: '200px', maxWidth: '400px' }}>
                <Search size={18} style={{ 
                  position: 'absolute', left: '12px', top: '50%', 
                  transform: 'translateY(-50%)', color: 'var(--text-muted)' 
                }} />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
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
              
              {/* Role filter */}
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
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
                <option value="">All Roles</option>
                <option value="CUSTOMER">Customers</option>
                <option value="TECH">Technicians</option>
                <option value="ADMIN">Admins</option>
              </select>
              
              {/* Refresh */}
              <button
                onClick={fetchUsers}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '10px 16px',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                <RefreshCw size={16} />
              </button>
            </div>

            {/* Users list */}
            {loadingUsers ? (
              <div style={{ textAlign: 'center', padding: '60px' }}>
                <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto' }} />
              </div>
            ) : (
              <div style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                overflow: 'hidden'
              }}>
                {/* Table header */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 150px 120px',
                  gap: '16px',
                  padding: '12px 20px',
                  background: 'var(--bg-panel)',
                  borderBottom: '1px solid var(--border-color)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase'
                }}>
                  <span>User</span>
                  <span>Email</span>
                  <span>Role</span>
                  <span>Actions</span>
                </div>
                
                {/* Table body */}
                {filteredUsers.length === 0 ? (
                  <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No users found
                  </div>
                ) : (
                  filteredUsers.map(u => (
                    <div
                      key={u.userId}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr 150px 120px',
                        gap: '16px',
                        padding: '16px 20px',
                        borderBottom: '1px solid var(--border-color)',
                        alignItems: 'center'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{
                          width: '36px', height: '36px',
                          borderRadius: '50%',
                          background: 'var(--bg-panel)',
                          border: '1px solid var(--accent-primary)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: 'var(--accent-primary)'
                        }}>
                          <User size={18} />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem' }}>
                          {u.firstName} {u.lastName}
                        </span>
                      </div>
                      <span style={{ 
                        fontFamily: 'var(--font-mono)', 
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)'
                      }}>
                        {u.email}
                      </span>
                      <RoleBadge role={u.role} />
                      <button
                        onClick={() => setEditingUser(u)}
                        disabled={u.userId === user?.sub}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '6px',
                          padding: '6px 12px',
                          background: 'transparent',
                          border: '1px solid var(--border-color)',
                          borderRadius: '4px',
                          color: u.userId === user?.sub ? 'var(--text-muted)' : 'var(--text-secondary)',
                          cursor: u.userId === user?.sub ? 'not-allowed' : 'pointer',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.75rem'
                        }}
                      >
                        <Edit2 size={12} />
                        Edit
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        ) : (
          <>
            {/* Tickets tab */}
            <div style={{ 
              display: 'flex', 
              gap: '16px', 
              marginBottom: '24px',
              flexWrap: 'wrap'
            }}>
              {/* Search */}
              <div style={{ position: 'relative', flex: '1', minWidth: '200px', maxWidth: '400px' }}>
                <Search size={18} style={{ 
                  position: 'absolute', left: '12px', top: '50%', 
                  transform: 'translateY(-50%)', color: 'var(--text-muted)' 
                }} />
                <input
                  type="text"
                  placeholder="Search tickets..."
                  value={ticketSearch}
                  onChange={(e) => setTicketSearch(e.target.value)}
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
              
              <button
                onClick={fetchTickets}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '10px 16px',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                <RefreshCw size={16} />
              </button>
            </div>

            {/* Tickets list */}
            {loadingTickets ? (
              <div style={{ textAlign: 'center', padding: '60px' }}>
                <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto' }} />
              </div>
            ) : (
              <div style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                overflow: 'hidden'
              }}>
                {/* Table header */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '2fr 1fr 1fr 150px 120px',
                  gap: '16px',
                  padding: '12px 20px',
                  background: 'var(--bg-panel)',
                  borderBottom: '1px solid var(--border-color)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase'
                }}>
                  <span>Ticket</span>
                  <span>Status</span>
                  <span>Created By</span>
                  <span>Assigned To</span>
                  <span>Actions</span>
                </div>
                
                {filteredTickets.length === 0 ? (
                  <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No tickets found
                  </div>
                ) : (
                  filteredTickets.map(t => (
                    <div
                      key={t.ticketId}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '2fr 1fr 1fr 150px 120px',
                        gap: '16px',
                        padding: '16px 20px',
                        borderBottom: '1px solid var(--border-color)',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ 
                          fontFamily: 'var(--font-mono)', 
                          fontSize: '0.85rem',
                          marginBottom: '4px',
                          cursor: 'pointer',
                          color: 'var(--accent-primary)'
                        }}
                          onClick={() => navigate(`/tickets/${t.ticketId}`)}
                        >
                          {t.title}
                        </div>
                        <div style={{ 
                          fontFamily: 'var(--font-mono)', 
                          fontSize: '0.7rem',
                          color: 'var(--text-muted)'
                        }}>
                          {t.ticketId.substring(0, 8)}...
                        </div>
                      </div>
                      <StatusBadge status={t.status} />
                      <span style={{ 
                        fontFamily: 'var(--font-mono)', 
                        fontSize: '0.8rem',
                        color: 'var(--text-secondary)'
                      }}>
                        {t.createdByEmail?.split('@')[0] || 'Unknown'}
                      </span>
                      <span style={{ 
                        fontFamily: 'var(--font-mono)', 
                        fontSize: '0.8rem',
                        color: t.assignedTo ? 'var(--text-primary)' : 'var(--text-muted)'
                      }}>
                        {t.assignedToName || 'Unassigned'}
                      </span>
                      <button
                        onClick={() => setAssigningTicket(t)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '6px',
                          padding: '6px 12px',
                          background: 'transparent',
                          border: '1px solid var(--accent-primary)',
                          borderRadius: '4px',
                          color: 'var(--accent-primary)',
                          cursor: 'pointer',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.75rem'
                        }}
                      >
                        <UserPlus size={12} />
                        Assign
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Edit User Modal */}
      {editingUser && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            padding: '24px',
            width: '400px',
            maxWidth: '90%'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '24px'
            }}>
              <h3 style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)' }}>
                Edit User Role
              </h3>
              <button
                onClick={() => setEditingUser(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>
            
            <div style={{ marginBottom: '20px' }}>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>
                {editingUser.firstName} {editingUser.lastName}
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {editingUser.email}
              </p>
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={{ 
                display: 'block',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8rem',
                color: 'var(--text-muted)',
                marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                Select Role
              </label>
              <div style={{ display: 'flex', gap: '12px' }}>
                {['CUSTOMER', 'TECH', 'ADMIN'].map(role => (
                  <button
                    key={role}
                    onClick={() => handleUpdateRole(editingUser.userId, role)}
                    disabled={saving || editingUser.role === role}
                    style={{
                      flex: 1,
                      padding: '12px',
                      background: editingUser.role === role ? 'var(--accent-primary)' : 'var(--bg-panel)',
                      border: `1px solid ${editingUser.role === role ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                      borderRadius: '6px',
                      color: editingUser.role === role ? 'var(--bg-primary)' : 'var(--text-secondary)',
                      cursor: saving ? 'wait' : 'pointer',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.8rem'
                    }}
                  >
                    {role}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Assign Ticket Modal */}
      {assigningTicket && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            padding: '24px',
            width: '450px',
            maxWidth: '90%'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '24px'
            }}>
              <h3 style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)' }}>
                Assign Ticket
              </h3>
              <button
                onClick={() => { setAssigningTicket(null); setSelectedTech(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>
            
            <div style={{ marginBottom: '20px' }}>
              <p style={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: '8px' }}>
                {assigningTicket.title}
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                ID: {assigningTicket.ticketId.substring(0, 8)}...
              </p>
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={{ 
                display: 'block',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8rem',
                color: 'var(--text-muted)',
                marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                Select Technician
              </label>
              <select
                value={selectedTech}
                onChange={(e) => setSelectedTech(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.9rem',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  color: 'var(--text-primary)',
                  cursor: 'pointer'
                }}
              >
                <option value="">-- Select a technician --</option>
                {technicians.map(tech => (
                  <option key={tech.userId} value={tech.userId}>
                    {tech.name} ({tech.role})
                  </option>
                ))}
              </select>
            </div>
            
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => { setAssigningTicket(null); setSelectedTech(''); }}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleAssignTicket}
                disabled={!selectedTech || saving}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: selectedTech ? 'var(--accent-primary)' : 'var(--bg-panel)',
                  border: 'none',
                  borderRadius: '6px',
                  color: selectedTech ? 'var(--bg-primary)' : 'var(--text-muted)',
                  cursor: !selectedTech || saving ? 'not-allowed' : 'pointer',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600
                }}
              >
                {saving ? 'Assigning...' : 'Assign'}
              </button>
            </div>
          </div>
        </div>
      )}

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

export default AdminConsole
