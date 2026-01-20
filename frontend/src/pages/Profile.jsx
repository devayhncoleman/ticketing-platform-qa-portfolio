import { useState, useContext } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  Terminal, ArrowLeft, User, Mail, Shield, Key, LogOut, 
  Save, AlertCircle, CheckCircle, Eye, EyeOff
} from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'

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

function Profile() {
  const { user, token, logout } = useContext(AuthContext)
  const navigate = useNavigate()
  
  // Password change state
  const [showPasswordChange, setShowPasswordChange] = useState(false)
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [showPasswords, setShowPasswords] = useState(false)
  const [changingPassword, setChangingPassword] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState(false)

  const validatePassword = (password) => ({
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
  })

  const passwordChecks = validatePassword(passwordForm.newPassword)
  const allPasswordChecksPass = Object.values(passwordChecks).every(Boolean)

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess(false)

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('New passwords do not match')
      return
    }

    if (!allPasswordChecksPass) {
      setPasswordError('New password does not meet requirements')
      return
    }

    setChangingPassword(true)

    try {
      const response = await fetch(
        `https://cognito-idp.${API_CONFIG.region}.amazonaws.com/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.ChangePassword'
          },
          body: JSON.stringify({
            AccessToken: token,
            PreviousPassword: passwordForm.currentPassword,
            ProposedPassword: passwordForm.newPassword
          })
        }
      )

      const data = await response.json()

      if (data.__type) {
        if (data.__type.includes('NotAuthorizedException')) {
          setPasswordError('Current password is incorrect')
        } else if (data.__type.includes('InvalidPasswordException')) {
          setPasswordError('New password does not meet requirements')
        } else if (data.__type.includes('LimitExceededException')) {
          setPasswordError('Too many attempts. Please try again later.')
        } else {
          setPasswordError(data.message || 'Failed to change password')
        }
      } else {
        setPasswordSuccess(true)
        setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
        setTimeout(() => {
          setShowPasswordChange(false)
          setPasswordSuccess(false)
        }, 2000)
      }
    } catch (err) {
      setPasswordError('Connection error. Please try again.')
    } finally {
      setChangingPassword(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="profile-page">
      {/* Header */}
      <header className="profile-header">
        <div className="header-left">
          <Link to="/dashboard" className="back-link">
            <ArrowLeft size={20} />
            <span>Back to Dashboard</span>
          </Link>
        </div>
        <div className="header-title">
          <h1>
            <Terminal size={24} />
            user.profile()
          </h1>
        </div>
        <div className="header-right">
          <button className="btn btn-ghost btn-with-icon" onClick={handleLogout}>
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="profile-content">
        <div className="profile-grid">
          {/* User Info Card */}
          <div className="schema-card">
            <div className="schema-card-header">
              <User size={16} className="icon" />
              <span className="title">user.info</span>
            </div>
            <div className="schema-card-body">
              <div className="user-avatar-large">
                <User size={48} />
              </div>
              <div className="user-info-grid">
                <div className="info-field">
                  <span className="info-label">Full Name</span>
                  <span className="info-value">{user?.givenName} {user?.familyName}</span>
                </div>
                <div className="info-field">
                  <span className="info-label"><Mail size={14} /> Email</span>
                  <span className="info-value">{user?.email}</span>
                </div>
                <div className="info-field">
                  <span className="info-label"><Shield size={14} /> User ID</span>
                  <code className="info-code">{user?.sub}</code>
                </div>
                <div className="info-field">
                  <span className="info-label">Account Status</span>
                  <span className="badge badge-resolved">
                    <CheckCircle size={14} /> Verified
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Security Card */}
          <div className="schema-card">
            <div className="schema-card-header">
              <Key size={16} className="icon" />
              <span className="title">user.security</span>
            </div>
            <div className="schema-card-body">
              {!showPasswordChange ? (
                <div className="security-options">
                  <div className="security-item">
                    <div className="security-info">
                      <h4>Password</h4>
                      <p className="text-muted">Change your account password</p>
                    </div>
                    <button 
                      className="btn btn-ghost btn-with-icon"
                      onClick={() => setShowPasswordChange(true)}
                    >
                      <Key size={18} />
                      <span>Change</span>
                    </button>
                  </div>
                  <div className="security-item">
                    <div className="security-info">
                      <h4>Two-Factor Authentication</h4>
                      <p className="text-muted">Add an extra layer of security</p>
                    </div>
                    <span className="badge badge-waiting">Coming Soon</span>
                  </div>
                </div>
              ) : (
                <form onSubmit={handlePasswordChange} className="password-form">
                  {passwordError && (
                    <div className="error-message">
                      <AlertCircle size={16} />
                      <span>{passwordError}</span>
                    </div>
                  )}
                  {passwordSuccess && (
                    <div className="success-message">
                      <CheckCircle size={16} />
                      <span>Password changed successfully!</span>
                    </div>
                  )}

                  <div className="input-group">
                    <label className="input-label">CURRENT PASSWORD</label>
                    <div className="input-with-icon password-field">
                      <input
                        type={showPasswords ? 'text' : 'password'}
                        className="input-field"
                        placeholder="••••••••"
                        value={passwordForm.currentPassword}
                        onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                        required
                      />
                      <button
                        type="button"
                        className="password-toggle"
                        onClick={() => setShowPasswords(!showPasswords)}
                      >
                        {showPasswords ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  <div className="input-group">
                    <label className="input-label">NEW PASSWORD</label>
                    <input
                      type={showPasswords ? 'text' : 'password'}
                      className="input-field"
                      placeholder="••••••••"
                      value={passwordForm.newPassword}
                      onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                      required
                    />
                    <div className="password-requirements">
                      <div className={`requirement ${passwordChecks.length ? 'met' : ''}`}>
                        {passwordChecks.length ? '✓' : '○'} 8+ characters
                      </div>
                      <div className={`requirement ${passwordChecks.uppercase ? 'met' : ''}`}>
                        {passwordChecks.uppercase ? '✓' : '○'} Uppercase
                      </div>
                      <div className={`requirement ${passwordChecks.lowercase ? 'met' : ''}`}>
                        {passwordChecks.lowercase ? '✓' : '○'} Lowercase
                      </div>
                      <div className={`requirement ${passwordChecks.number ? 'met' : ''}`}>
                        {passwordChecks.number ? '✓' : '○'} Number
                      </div>
                      <div className={`requirement ${passwordChecks.special ? 'met' : ''}`}>
                        {passwordChecks.special ? '✓' : '○'} Special char
                      </div>
                    </div>
                  </div>

                  <div className="input-group">
                    <label className="input-label">CONFIRM NEW PASSWORD</label>
                    <input
                      type={showPasswords ? 'text' : 'password'}
                      className="input-field"
                      placeholder="••••••••"
                      value={passwordForm.confirmPassword}
                      onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                      required
                    />
                    {passwordForm.confirmPassword && (
                      <div className={`match-indicator ${passwordForm.newPassword === passwordForm.confirmPassword ? 'match' : 'no-match'}`}>
                        {passwordForm.newPassword === passwordForm.confirmPassword ? '✓ Passwords match' : '✗ Passwords do not match'}
                      </div>
                    )}
                  </div>

                  <div className="form-actions">
                    <button 
                      type="button" 
                      className="btn btn-ghost"
                      onClick={() => {
                        setShowPasswordChange(false)
                        setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
                        setPasswordError('')
                      }}
                    >
                      Cancel
                    </button>
                    <button 
                      type="submit" 
                      className="btn btn-primary btn-with-icon"
                      disabled={changingPassword || !allPasswordChecksPass}
                    >
                      {changingPassword ? (
                        <><div className="spinner"></div><span>Changing...</span></>
                      ) : (
                        <><Save size={18} /><span>Update Password</span></>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          {/* Danger Zone */}
          <div className="schema-card danger-card">
            <div className="schema-card-header">
              <AlertCircle size={16} className="icon" style={{ color: 'var(--priority-critical)' }} />
              <span className="title" style={{ color: 'var(--priority-critical)' }}>danger.zone</span>
            </div>
            <div className="schema-card-body">
              <div className="danger-item">
                <div className="danger-info">
                  <h4>Delete Account</h4>
                  <p className="text-muted">Permanently delete your account and all data</p>
                </div>
                <button className="btn btn-danger btn-with-icon" disabled>
                  <AlertCircle size={18} />
                  <span>Delete Account</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      <style>{`
        .profile-page {
          min-height: 100vh;
          background: var(--bg-primary);
        }

        .profile-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 32px;
          border-bottom: 1px solid var(--border-color);
          background: var(--bg-secondary);
        }

        .header-left, .header-right {
          flex: 1;
        }

        .header-right {
          display: flex;
          justify-content: flex-end;
        }

        .back-link {
          display: inline-flex;
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
          justify-content: center;
          gap: 12px;
          font-family: var(--font-mono);
          font-size: 1.25rem;
          color: var(--accent-primary);
        }

        .profile-content {
          padding: 32px;
          max-width: 800px;
          margin: 0 auto;
        }

        .profile-grid {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .user-avatar-large {
          width: 80px;
          height: 80px;
          background: var(--bg-panel);
          border: 2px solid var(--accent-primary);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--accent-primary);
          margin: 0 auto 24px;
        }

        .user-info-grid {
          display: grid;
          gap: 16px;
        }

        .info-field {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 12px;
          background: var(--bg-panel);
          border-radius: 8px;
        }

        .info-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--text-muted);
          text-transform: uppercase;
        }

        .info-value {
          font-family: var(--font-mono);
          font-size: 1rem;
          color: var(--text-primary);
        }

        .info-code {
          font-family: var(--font-mono);
          font-size: 0.8rem;
          color: var(--accent-primary);
          word-break: break-all;
        }

        .security-options {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .security-item, .danger-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px;
          background: var(--bg-panel);
          border-radius: 8px;
        }

        .security-info h4, .danger-info h4 {
          font-size: 1rem;
          margin-bottom: 4px;
        }

        .password-form {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          background: rgba(255, 107, 107, 0.1);
          border: 1px solid var(--priority-critical);
          border-radius: 6px;
          color: var(--priority-critical);
          font-family: var(--font-mono);
          font-size: 0.85rem;
        }

        .success-message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          background: rgba(0, 255, 65, 0.1);
          border: 1px solid var(--accent-primary);
          border-radius: 6px;
          color: var(--accent-primary);
          font-family: var(--font-mono);
          font-size: 0.85rem;
        }

        .input-with-icon {
          position: relative;
        }

        .password-field .input-field {
          padding-right: 48px;
        }

        .password-toggle {
          position: absolute;
          right: 12px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 4px;
        }

        .password-toggle:hover {
          color: var(--accent-primary);
        }

        .password-requirements {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 10px;
        }

        .requirement {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--text-muted);
          padding: 2px 8px;
          background: var(--bg-panel);
          border-radius: 4px;
        }

        .requirement.met {
          color: var(--accent-primary);
          background: rgba(0, 255, 65, 0.1);
        }

        .match-indicator {
          font-family: var(--font-mono);
          font-size: 0.75rem;
          margin-top: 8px;
        }

        .match-indicator.match {
          color: var(--accent-primary);
        }

        .match-indicator.no-match {
          color: var(--priority-critical);
        }

        .form-actions {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          margin-top: 8px;
        }

        .danger-card {
          border-color: rgba(255, 107, 107, 0.3);
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

        .btn-danger:hover:not(:disabled) {
          background: rgba(255, 107, 107, 0.2);
        }

        .btn-danger:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
      `}</style>
    </div>
  )
}

export default Profile
