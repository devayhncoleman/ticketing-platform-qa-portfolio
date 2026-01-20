import { useState, useEffect, useContext, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, Tag, Clock, User, AlertCircle, CheckCircle, 
  MessageSquare, Send, Paperclip, Image, X, Loader,
  Shield, Calendar, Hash
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
      fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600,
      textTransform: 'uppercase'
    }}>
      <Icon size={12} />
      {status.replace('_', ' ')}
    </span>
  )
}

// Priority badge component
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
      padding: '4px 12px', borderRadius: '4px',
      border: `1px solid ${color}`, color,
      fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600,
      textTransform: 'uppercase'
    }}>
      {priority}
    </span>
  )
}

// Comment component
const Comment = ({ comment, isOwnComment }) => {
  const isInternal = comment.isInternal
  const roleColors = {
    'CUSTOMER': '#4ecdc4',
    'TECH': '#ffe66d',
    'ADMIN': '#ff6b6b'
  }
  const roleColor = roleColors[comment.authorRole] || '#4ecdc4'
  
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: isOwnComment ? 'flex-end' : 'flex-start',
      marginBottom: '16px'
    }}>
      <div style={{
        maxWidth: '80%',
        background: isInternal ? 'rgba(255, 107, 107, 0.1)' : (isOwnComment ? 'rgba(0, 255, 65, 0.1)' : 'var(--bg-panel)'),
        border: `1px solid ${isInternal ? 'rgba(255, 107, 107, 0.3)' : 'var(--border-color)'}`,
        borderRadius: '12px',
        borderTopLeftRadius: isOwnComment ? '12px' : '4px',
        borderTopRightRadius: isOwnComment ? '4px' : '12px',
        padding: '12px 16px'
      }}>
        {/* Author header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <span style={{ 
            fontFamily: 'var(--font-mono)', 
            fontSize: '0.8rem', 
            fontWeight: 600,
            color: roleColor 
          }}>
            {comment.authorName || comment.authorEmail}
          </span>
          <span style={{
            fontSize: '0.65rem',
            padding: '2px 6px',
            borderRadius: '4px',
            background: `${roleColor}22`,
            color: roleColor,
            fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase'
          }}>
            {comment.authorRole}
          </span>
          {isInternal && (
            <span style={{
              fontSize: '0.65rem',
              padding: '2px 6px',
              borderRadius: '4px',
              background: 'rgba(255, 107, 107, 0.2)',
              color: '#ff6b6b',
              fontFamily: 'var(--font-mono)'
            }}>
              INTERNAL
            </span>
          )}
        </div>
        
        {/* Content */}
        <p style={{ 
          color: 'var(--text-primary)', 
          fontSize: '0.9rem', 
          lineHeight: 1.5,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}>
          {comment.content}
        </p>
        
        {/* Attachments */}
        {comment.attachments && comment.attachments.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
            {comment.attachments.map((url, idx) => (
              <a 
                key={idx} 
                href={url} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{
                  display: 'block',
                  width: '100px',
                  height: '100px',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  border: '1px solid var(--border-color)'
                }}
              >
                <img 
                  src={url} 
                  alt={`Attachment ${idx + 1}`}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </a>
            ))}
          </div>
        )}
        
        {/* Timestamp */}
        <div style={{ 
          marginTop: '8px', 
          fontSize: '0.7rem', 
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)'
        }}>
          {new Date(comment.createdAt).toLocaleString()}
        </div>
      </div>
    </div>
  )
}

function TicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, token } = useContext(AuthContext)
  const messagesEndRef = useRef(null)
  
  // Ticket state
  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  
  // Comments state
  const [comments, setComments] = useState([])
  const [loadingComments, setLoadingComments] = useState(true)
  
  // New comment state
  const [newComment, setNewComment] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [sending, setSending] = useState(false)
  const [attachments, setAttachments] = useState([])
  const [uploading, setUploading] = useState(false)
  
  // User role (from token or API)
  const [userRole, setUserRole] = useState('CUSTOMER')

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    fetchTicket()
    fetchComments()
    // Get user role from stored user data
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}')
    setUserRole(storedUser.role || 'CUSTOMER')
  }, [id])

  useEffect(() => {
    scrollToBottom()
  }, [comments])

  const fetchTicket = async () => {
    try {
      const response = await axios.get(`${API_CONFIG.baseUrl}/tickets/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setTicket(response.data)
    } catch (err) {
      setError('Failed to load ticket')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchComments = async () => {
    try {
      const response = await axios.get(`${API_CONFIG.baseUrl}/tickets/${id}/comments`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setComments(response.data.comments || [])
    } catch (err) {
      console.error('Failed to load comments:', err)
    } finally {
      setLoadingComments(false)
    }
  }

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files)
    if (files.length === 0) return
    
    // Validate file types (images only)
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    const invalidFiles = files.filter(f => !validTypes.includes(f.type))
    if (invalidFiles.length > 0) {
      alert('Only image files are allowed (JPEG, PNG, GIF, WebP)')
      return
    }
    
    // Max 5 attachments
    if (attachments.length + files.length > 5) {
      alert('Maximum 5 attachments per comment')
      return
    }
    
    setUploading(true)
    
    try {
      for (const file of files) {
        // Get presigned URL
        const urlResponse = await axios.post(
          `${API_CONFIG.baseUrl}/attachments/upload-url`,
          {
            fileName: file.name,
            contentType: file.type,
            ticketId: id
          },
          { headers: { Authorization: `Bearer ${token}` } }
        )
        
        const { uploadUrl, fileUrl } = urlResponse.data
        
        // Upload to S3
        await fetch(uploadUrl, {
          method: 'PUT',
          body: file,
          headers: { 'Content-Type': file.type }
        })
        
        setAttachments(prev => [...prev, { url: fileUrl, name: file.name }])
      }
    } catch (err) {
      console.error('Upload failed:', err)
      alert('Failed to upload attachment')
    } finally {
      setUploading(false)
    }
  }

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }

  const handleSendComment = async () => {
    if (!newComment.trim() && attachments.length === 0) return
    
    setSending(true)
    
    try {
      const response = await axios.post(
        `${API_CONFIG.baseUrl}/tickets/${id}/comments`,
        {
          content: newComment.trim(),
          attachments: attachments.map(a => a.url),
          isInternal
        },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      setComments(prev => [...prev, response.data])
      setNewComment('')
      setAttachments([])
      setIsInternal(false)
    } catch (err) {
      console.error('Failed to send comment:', err)
      alert('Failed to send comment')
    } finally {
      setSending(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendComment()
    }
  }

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'var(--bg-primary)'
      }}>
        <div className="spinner" style={{ width: 40, height: 40 }} />
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        color: '#ff6b6b'
      }}>
        {error || 'Ticket not found'}
      </div>
    )
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'var(--bg-primary)',
      display: 'flex',
      flexDirection: 'column'
    }}>
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
            fontSize: '1.1rem',
            color: 'var(--accent-primary)'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>&gt;_ </span>
            ticket.view("{ticket.ticketId.substring(0, 8)}...")
          </h1>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <StatusBadge status={ticket.status} />
          <PriorityBadge priority={ticket.priority} />
        </div>
      </header>

      {/* Main content */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 320px',
        flex: 1,
        overflow: 'hidden'
      }}>
        {/* Left: Ticket details and chat */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column',
          borderRight: '1px solid var(--border-color)',
          overflow: 'hidden'
        }}>
          {/* Ticket info */}
          <div style={{ 
            padding: '24px',
            borderBottom: '1px solid var(--border-color)',
            background: 'var(--bg-card)'
          }}>
            <h2 style={{ 
              fontFamily: 'var(--font-mono)',
              fontSize: '1.25rem',
              color: 'var(--text-primary)',
              marginBottom: '12px'
            }}>
              {ticket.title}
            </h2>
            <p style={{ 
              color: 'var(--text-secondary)',
              fontSize: '0.95rem',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap'
            }}>
              {ticket.description}
            </p>
          </div>

          {/* Comments/Chat section */}
          <div style={{ 
            flex: 1, 
            overflow: 'auto',
            padding: '24px',
            background: 'var(--bg-primary)'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              marginBottom: '20px',
              color: 'var(--accent-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.9rem'
            }}>
              <MessageSquare size={18} />
              ticket.comments
            </div>

            {loadingComments ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div className="spinner" />
              </div>
            ) : comments.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '40px',
                color: 'var(--text-muted)'
              }}>
                No comments yet. Start the conversation!
              </div>
            ) : (
              comments.map((comment) => (
                <Comment 
                  key={comment.commentId} 
                  comment={comment}
                  isOwnComment={comment.authorId === user?.sub}
                />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Comment input */}
          <div style={{
            padding: '16px 24px',
            background: 'var(--bg-secondary)',
            borderTop: '1px solid var(--border-color)'
          }}>
            {/* Attachments preview */}
            {attachments.length > 0 && (
              <div style={{ 
                display: 'flex', 
                gap: '8px', 
                marginBottom: '12px',
                flexWrap: 'wrap'
              }}>
                {attachments.map((att, idx) => (
                  <div key={idx} style={{
                    position: 'relative',
                    width: '60px',
                    height: '60px',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    border: '1px solid var(--border-color)'
                  }}>
                    <img 
                      src={att.url} 
                      alt={att.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                    <button
                      onClick={() => removeAttachment(idx)}
                      style={{
                        position: 'absolute',
                        top: '2px',
                        right: '2px',
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        background: '#ff6b6b',
                        border: 'none',
                        color: 'white',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: 0
                      }}
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Internal note toggle (tech/admin only) */}
            {userRole !== 'CUSTOMER' && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px',
                marginBottom: '12px'
              }}>
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8rem',
                  color: isInternal ? '#ff6b6b' : 'var(--text-muted)'
                }}>
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(e) => setIsInternal(e.target.checked)}
                    style={{ accentColor: '#ff6b6b' }}
                  />
                  <Shield size={14} />
                  Internal note (not visible to customer)
                </label>
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
                  rows={2}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.9rem',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                    resize: 'none'
                  }}
                />
              </div>
              
              {/* Attachment button */}
              <label style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '44px',
                height: '44px',
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                cursor: uploading ? 'wait' : 'pointer',
                color: 'var(--text-muted)'
              }}>
                {uploading ? <Loader size={18} className="spinner" /> : <Image size={18} />}
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleFileSelect}
                  disabled={uploading}
                  style={{ display: 'none' }}
                />
              </label>
              
              {/* Send button */}
              <button
                onClick={handleSendComment}
                disabled={sending || (!newComment.trim() && attachments.length === 0)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '12px 24px',
                  background: 'var(--accent-primary)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'var(--bg-primary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: sending ? 'wait' : 'pointer',
                  opacity: sending || (!newComment.trim() && attachments.length === 0) ? 0.5 : 1
                }}
              >
                {sending ? <Loader size={16} className="spinner" /> : <Send size={16} />}
                SEND
              </button>
            </div>
          </div>
        </div>

        {/* Right: Metadata sidebar */}
        <div style={{ 
          background: 'var(--bg-secondary)',
          padding: '24px',
          overflow: 'auto'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '24px',
            color: 'var(--accent-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.9rem'
          }}>
            <Tag size={18} />
            ticket.metadata
          </div>

          {/* Metadata fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                <AlertCircle size={12} />
                Status
              </label>
              <StatusBadge status={ticket.status} />
            </div>

            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                Priority
              </label>
              <PriorityBadge priority={ticket.priority} />
            </div>

            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                <Tag size={12} />
                Category
              </label>
              <span style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>
                {ticket.category}
              </span>
            </div>

            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                <User size={12} />
                Assigned To
              </label>
              <span style={{ 
                color: ticket.assignedTo ? 'var(--text-primary)' : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.9rem'
              }}>
                {ticket.assignedToName || ticket.assignedTo || 'Unassigned'}
              </span>
            </div>

            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                <Calendar size={12} />
                Created
              </label>
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                {new Date(ticket.createdAt).toLocaleString()}
              </span>
            </div>

            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                <Clock size={12} />
                Last Updated
              </label>
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                {new Date(ticket.updatedAt).toLocaleString()}
              </span>
            </div>

            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                <User size={12} />
                Created By
              </label>
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                {ticket.createdByName || ticket.createdByEmail}
              </span>
            </div>

            <div>
              <label style={{ 
                display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: 'var(--text-muted)', marginBottom: '8px',
                textTransform: 'uppercase'
              }}>
                <Hash size={12} />
                Ticket ID
              </label>
              <span style={{ 
                color: 'var(--accent-primary)', 
                fontFamily: 'var(--font-mono)', 
                fontSize: '0.75rem',
                wordBreak: 'break-all'
              }}>
                {ticket.ticketId}
              </span>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        textarea:focus {
          outline: none;
          border-color: var(--accent-primary) !important;
        }
        .spinner {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @media (max-width: 768px) {
          .ticket-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  )
}

export default TicketDetail
