import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Terminal, Mail, Key, ArrowLeft, Zap, CheckCircle, Copy, Check, Eye, EyeOff } from 'lucide-react'
import { API_CONFIG } from '../App'

// The Winning Team Logo
const WinningTeamLogo = ({ size = 80 }) => (
  <svg viewBox="0 0 120 120" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
    <circle cx="60" cy="60" r="52" fill="#1a1a2e" stroke="#00ff41" strokeWidth="2"/>
    <circle cx="60" cy="60" r="42" fill="#0d0d1a" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="32" fill="#1a1a2e" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="22" fill="#0d0d1a" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="12" fill="#1a1a2e" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.5"/>
    <circle cx="60" cy="60" r="6" fill="#00ff41" opacity="0.5"/>
    <circle cx="60" cy="60" r="3" fill="#00ff41" opacity="0.8"/>
    <g transform="translate(60, 62) rotate(12)">
      <path d="M-14,-22 L-11,-6 Q-11,7 0,11 Q11,7 11,-6 L14,-22 Z" fill="none" stroke="#00ff41" strokeWidth="2.5" strokeLinecap="round"/>
      <path d="M-14,-17 Q-21,-17 -21,-9 Q-21,-1 -14,-1" fill="none" stroke="#00ff41" strokeWidth="2" strokeLinecap="round"/>
      <path d="M14,-17 Q21,-17 21,-9 Q21,-1 14,-1" fill="none" stroke="#00ff41" strokeWidth="2" strokeLinecap="round"/>
      <line x1="0" y1="11" x2="0" y2="19" stroke="#00ff41" strokeWidth="2.5"/>
      <path d="M-9,19 L9,19 L11,24 L-11,24 Z" fill="none" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <polygon points="0,-14 1.5,-9 7,-9 2.5,-5 4,1 0,-2 -4,1 -2.5,-5 -7,-9 -1.5,-9" fill="#00ff41" opacity="0.9"/>
    </g>
    <g transform="translate(60, 60)">
      <line x1="0" y1="0" x2="32" y2="32" stroke="#00ff41" strokeWidth="4" strokeLinecap="round"/>
      <line x1="18" y1="18" x2="26" y2="26" stroke="#00ff41" strokeWidth="6" strokeLinecap="round"/>
      <g transform="translate(32, 32) rotate(45)">
        <path d="M0,0 L0,-18 L6,-12 L0,-6 L-6,-12 Z" fill="#00ff41" opacity="0.9"/>
        <path d="M0,0 L-18,0 L-12,-6 L-6,0 L-12,6 Z" fill="#00ff41" opacity="0.7"/>
        <path d="M0,0 L18,0 L12,-6 L6,0 L12,6 Z" fill="#00ff41" opacity="0.7"/>
      </g>
    </g>
    <g transform="translate(60, 60)">
      <line x1="-5" y1="-5" x2="-12" y2="-12" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" opacity="0.8"/>
      <line x1="0" y1="-7" x2="0" y2="-14" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" opacity="0.7"/>
      <line x1="-7" y1="0" x2="-14" y2="0" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" opacity="0.7"/>
    </g>
  </svg>
)

function ForgotPassword() {
  const navigate = useNavigate()
  
  // Step 1: Request code
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Step 2: Enter code and new password
  const [codeSent, setCodeSent] = useState(false)
  const [verificationCode, setVerificationCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [copied, setCopied] = useState(false)
  
  // Step 3: Success
  const [resetComplete, setResetComplete] = useState(false)

  const validatePassword = (password) => ({
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
  })

  const passwordChecks = validatePassword(newPassword)
  const allPasswordChecksPass = Object.values(passwordChecks).every(Boolean)

  // Step 1: Request password reset code
  const handleRequestCode = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch(
        `https://cognito-idp.${API_CONFIG.region}.amazonaws.com/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.ForgotPassword'
          },
          body: JSON.stringify({
            ClientId: API_CONFIG.clientId,
            Username: email
          })
        }
      )

      const data = await response.json()

      if (data.__type) {
        if (data.__type.includes('UserNotFoundException')) {
          setError('No account found with this email')
        } else if (data.__type.includes('LimitExceededException')) {
          setError('Too many attempts. Please try again later.')
        } else {
          setError(data.message || 'Failed to send reset code')
        }
      } else {
        setCodeSent(true)
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Step 2: Reset password with code
  const handleResetPassword = async (e) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (!allPasswordChecksPass) {
      setError('Password does not meet requirements')
      return
    }

    setResetting(true)

    try {
      const response = await fetch(
        `https://cognito-idp.${API_CONFIG.region}.amazonaws.com/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.ConfirmForgotPassword'
          },
          body: JSON.stringify({
            ClientId: API_CONFIG.clientId,
            Username: email,
            ConfirmationCode: verificationCode,
            Password: newPassword
          })
        }
      )

      const data = await response.json()

      if (data.__type) {
        if (data.__type.includes('CodeMismatchException')) {
          setError('Invalid verification code')
        } else if (data.__type.includes('ExpiredCodeException')) {
          setError('Code has expired. Please request a new one.')
        } else if (data.__type.includes('InvalidPasswordException')) {
          setError('Password does not meet requirements')
        } else {
          setError(data.message || 'Failed to reset password')
        }
      } else {
        setResetComplete(true)
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setResetting(false)
    }
  }

  // Handle paste for verification code
  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText()
      const code = text.replace(/\D/g, '').slice(0, 6)
      if (code.length === 6) {
        setVerificationCode(code)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    } catch (err) {
      console.log('Clipboard access denied')
    }
  }

  // Resend code
  const handleResendCode = async () => {
    setError('')
    setLoading(true)
    try {
      await fetch(
        `https://cognito-idp.${API_CONFIG.region}.amazonaws.com/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.ForgotPassword'
          },
          body: JSON.stringify({
            ClientId: API_CONFIG.clientId,
            Username: email
          })
        }
      )
      alert('New reset code sent to your email!')
    } catch (err) {
      setError('Failed to resend code')
    } finally {
      setLoading(false)
    }
  }

  // Success Screen
  if (resetComplete) {
    return (
      <div className="forgot-container">
        <div className="grid-background"></div>
        <div className="forgot-wrapper">
          <div className="success-card schema-card">
            <div className="schema-card-header">
              <CheckCircle size={16} className="icon" />
              <span className="title">password.reset()</span>
            </div>
            <div className="schema-card-body" style={{ textAlign: 'center', padding: '40px 24px' }}>
              <div className="success-icon"><CheckCircle size={64} /></div>
              <h2 style={{ marginTop: 24, marginBottom: 12 }}>Password Reset Complete!</h2>
              <p className="text-muted" style={{ marginBottom: 24 }}>Your password has been successfully changed.</p>
              <Link to="/login" className="btn btn-primary btn-with-icon">
                <Terminal size={18} /><span>PROCEED TO LOGIN</span>
              </Link>
            </div>
          </div>
        </div>
        <style>{styles}</style>
      </div>
    )
  }

  // Step 2: Enter code and new password
  if (codeSent) {
    return (
      <div className="forgot-container">
        <div className="grid-background"></div>
        <div className="forgot-wrapper">
          <div className="forgot-brand">
            <div className="brand-icon"><WinningTeamLogo size={80} /></div>
            <h1 className="brand-title"><span className="text-accent">THE_WINNING</span>_TEAM</h1>
            <p className="brand-subtitle"><Terminal size={14} style={{ display: 'inline', marginRight: 8 }} />Reset Your Password</p>
          </div>
          
          <div className="forgot-card schema-card">
            <div className="schema-card-header">
              <Key size={16} className="icon" />
              <span className="title">auth.resetPassword()</span>
            </div>
            <div className="schema-card-body">
              <div className="info-text">
                <p>We sent a reset code to:</p>
                <p className="email-highlight">{email}</p>
              </div>

              <form onSubmit={handleResetPassword}>
                {error && <div className="error-message fade-in"><Zap size={16} /><span>{error}</span></div>}

                <div className="input-group">
                  <label className="input-label"><Key size={12} style={{ display: 'inline', marginRight: 6 }} />RESET CODE</label>
                  <div className="code-input-wrapper">
                    <input
                      type="text"
                      className="input-field verification-input"
                      placeholder="000000"
                      value={verificationCode}
                      onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      maxLength={6}
                      required
                    />
                    <button type="button" className="paste-btn" onClick={handlePaste} title="Paste from clipboard">
                      {copied ? <Check size={18} /> : <Copy size={18} />}
                    </button>
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">NEW PASSWORD</label>
                  <div className="input-with-icon password-field">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className="input-field"
                      placeholder="••••••••"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                    />
                    <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  <div className="password-requirements">
                    <div className={`requirement ${passwordChecks.length ? 'met' : ''}`}>{passwordChecks.length ? '✓' : '○'} 8+ chars</div>
                    <div className={`requirement ${passwordChecks.uppercase ? 'met' : ''}`}>{passwordChecks.uppercase ? '✓' : '○'} Uppercase</div>
                    <div className={`requirement ${passwordChecks.lowercase ? 'met' : ''}`}>{passwordChecks.lowercase ? '✓' : '○'} Lowercase</div>
                    <div className={`requirement ${passwordChecks.number ? 'met' : ''}`}>{passwordChecks.number ? '✓' : '○'} Number</div>
                    <div className={`requirement ${passwordChecks.special ? 'met' : ''}`}>{passwordChecks.special ? '✓' : '○'} Special</div>
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">CONFIRM PASSWORD</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="input-field"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                  {confirmPassword && (
                    <div className={`match-indicator ${newPassword === confirmPassword ? 'match' : 'no-match'}`}>
                      {newPassword === confirmPassword ? '✓ Passwords match' : '✗ Passwords do not match'}
                    </div>
                  )}
                </div>

                <button type="submit" className="btn btn-primary btn-full" disabled={resetting || !allPasswordChecksPass || verificationCode.length !== 6}>
                  {resetting ? <><div className="spinner"></div><span>RESETTING...</span></> : <><Key size={18} /><span>RESET PASSWORD</span></>}
                </button>
              </form>

              <div className="forgot-actions">
                <button type="button" className="btn-link" onClick={handleResendCode} disabled={loading}>
                  {loading ? 'Sending...' : "Didn't receive code? Resend"}
                </button>
                <button type="button" className="btn-link" onClick={() => { setCodeSent(false); setError('') }}>
                  <ArrowLeft size={14} />Change Email
                </button>
              </div>
            </div>
          </div>
        </div>
        <style>{styles}</style>
      </div>
    )
  }

  // Step 1: Enter email
  return (
    <div className="forgot-container">
      <div className="grid-background"></div>
      <div className="forgot-wrapper">
        <div className="forgot-brand">
          <div className="brand-icon"><WinningTeamLogo size={80} /></div>
          <h1 className="brand-title"><span className="text-accent">THE_WINNING</span>_TEAM</h1>
          <p className="brand-subtitle"><Terminal size={14} style={{ display: 'inline', marginRight: 8 }} />Password Recovery</p>
        </div>
        
        <div className="forgot-card schema-card">
          <div className="schema-card-header">
            <Mail size={16} className="icon" />
            <span className="title">auth.forgotPassword()</span>
          </div>
          <div className="schema-card-body">
            <p className="info-text">Enter your email address and we'll send you a code to reset your password.</p>

            <form onSubmit={handleRequestCode}>
              {error && <div className="error-message fade-in"><Zap size={16} /><span>{error}</span></div>}

              <div className="input-group">
                <label className="input-label"><Mail size={12} style={{ display: 'inline', marginRight: 6 }} />EMAIL</label>
                <input
                  type="email"
                  className="input-field"
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                {loading ? <><div className="spinner"></div><span>SENDING CODE...</span></> : <><Mail size={18} /><span>SEND RESET CODE</span></>}
              </button>
            </form>

            <div className="forgot-footer">
              <Link to="/login" className="btn-link">
                <ArrowLeft size={14} />Back to Login
              </Link>
            </div>
          </div>
        </div>
      </div>
      <style>{styles}</style>
    </div>
  )
}

const styles = `
  .forgot-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    position: relative;
    overflow: hidden;
  }

  .grid-background {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: 
      linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none;
  }

  .forgot-wrapper {
    width: 100%;
    max-width: 420px;
    z-index: 1;
  }

  .forgot-brand {
    text-align: center;
    margin-bottom: 32px;
  }

  .brand-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }

  .brand-title {
    font-family: var(--font-mono);
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .brand-subtitle {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .info-text {
    text-align: center;
    margin-bottom: 24px;
    font-family: var(--font-mono);
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  .email-highlight {
    color: var(--accent-primary);
    font-weight: 600;
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
    margin-bottom: 20px;
  }

  .code-input-wrapper {
    position: relative;
    display: flex;
    gap: 8px;
  }

  .verification-input {
    flex: 1;
    text-align: center;
    font-size: 1.5rem !important;
    letter-spacing: 0.5rem;
    font-weight: 600;
  }

  .paste-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;
  }

  .paste-btn:hover {
    color: var(--accent-primary);
    border-color: var(--accent-primary);
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
    gap: 6px;
    margin-top: 10px;
  }

  .requirement {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-muted);
    padding: 2px 6px;
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

  .btn-full {
    width: 100%;
    padding: 14px 24px;
    margin-top: 8px;
  }

  .btn-primary:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .forgot-footer, .forgot-actions {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid var(--border-color);
  }

  .btn-link {
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    color: var(--accent-primary);
    font-family: var(--font-mono);
    font-size: 0.85rem;
    cursor: pointer;
  }

  .btn-link:hover {
    opacity: 0.8;
  }

  .btn-link:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .success-icon {
    color: var(--accent-primary);
  }

  .btn-with-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
`

export default ForgotPassword
