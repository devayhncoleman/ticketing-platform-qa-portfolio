import { useState, useContext } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Terminal, Lock, Mail, Eye, EyeOff, Zap, KeyRound, ArrowLeft } from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'

// The Winning Team Logo Component - Dart from Southeast (we see back/fins)
const WinningTeamLogo = ({ size = 80 }) => (
  <svg viewBox="0 0 120 120" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
    {/* Dartboard rings */}
    <circle cx="60" cy="60" r="52" fill="#1a1a2e" stroke="#00ff41" strokeWidth="2"/>
    <circle cx="60" cy="60" r="42" fill="#0d0d1a" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="32" fill="#1a1a2e" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="22" fill="#0d0d1a" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.4"/>
    <circle cx="60" cy="60" r="12" fill="#1a1a2e" stroke="#00ff41" strokeWidth="1" strokeOpacity="0.5"/>
    
    {/* Bullseye glow */}
    <circle cx="60" cy="60" r="6" fill="#00ff41" opacity="0.5"/>
    <circle cx="60" cy="60" r="3" fill="#00ff41" opacity="0.8"/>
    
    {/* Trophy (tilted 12 degrees clockwise) */}
    <g transform="translate(60, 62) rotate(12)">
      <path d="M-14,-22 L-11,-6 Q-11,7 0,11 Q11,7 11,-6 L14,-22 Z" fill="none" stroke="#00ff41" strokeWidth="2.5" strokeLinecap="round"/>
      <path d="M-14,-17 Q-21,-17 -21,-9 Q-21,-1 -14,-1" fill="none" stroke="#00ff41" strokeWidth="2" strokeLinecap="round"/>
      <path d="M14,-17 Q21,-17 21,-9 Q21,-1 14,-1" fill="none" stroke="#00ff41" strokeWidth="2" strokeLinecap="round"/>
      <line x1="0" y1="11" x2="0" y2="19" stroke="#00ff41" strokeWidth="2.5"/>
      <path d="M-9,19 L9,19 L11,24 L-11,24 Z" fill="none" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <polygon points="0,-14 1.5,-9 7,-9 2.5,-5 4,1 0,-2 -4,1 -2.5,-5 -7,-9 -1.5,-9" fill="#00ff41" opacity="0.9"/>
    </g>
    
    {/* DART - From SOUTHEAST, entering board (we see shaft + fins) */}
    <g transform="translate(60, 60)">
      {/* Dart shaft going into bullseye */}
      <line x1="0" y1="0" x2="32" y2="32" stroke="#00ff41" strokeWidth="4" strokeLinecap="round"/>
      {/* Dart grip/barrel */}
      <line x1="18" y1="18" x2="26" y2="26" stroke="#00ff41" strokeWidth="6" strokeLinecap="round"/>
      {/* Dart flights/fins at the back */}
      <g transform="translate(32, 32) rotate(45)">
        <path d="M0,0 L0,-18 L6,-12 L0,-6 L-6,-12 Z" fill="#00ff41" opacity="0.9"/>
        <path d="M0,0 L-18,0 L-12,-6 L-6,0 L-12,6 Z" fill="#00ff41" opacity="0.7"/>
        <path d="M0,0 L18,0 L12,-6 L6,0 L12,6 Z" fill="#00ff41" opacity="0.7"/>
      </g>
    </g>
    
    {/* Impact burst at bullseye */}
    <g transform="translate(60, 60)">
      <line x1="-5" y1="-5" x2="-12" y2="-12" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" opacity="0.8"/>
      <line x1="0" y1="-7" x2="0" y2="-14" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" opacity="0.7"/>
      <line x1="-7" y1="0" x2="-14" y2="0" stroke="#00ff41" strokeWidth="2" strokeLinecap="round" opacity="0.7"/>
    </g>
  </svg>
)

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [needsVerification, setNeedsVerification] = useState(false)
  const [verificationCode, setVerificationCode] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [resending, setResending] = useState(false)
  
  const { login } = useContext(AuthContext)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
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
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
          },
          body: JSON.stringify({
            AuthFlow: 'USER_PASSWORD_AUTH',
            ClientId: API_CONFIG.clientId,
            AuthParameters: { USERNAME: email, PASSWORD: password }
          })
        }
      )

      const data = await response.json()

      if (data.AuthenticationResult) {
        const { IdToken } = data.AuthenticationResult
        const payload = JSON.parse(atob(IdToken.split('.')[1]))
        login({ email: payload.email, sub: payload.sub, givenName: payload.given_name, familyName: payload.family_name }, IdToken)
        navigate('/dashboard')
      } else if (data.__type) {
        if (data.__type.includes('NotAuthorizedException')) setError('Invalid email or password')
        else if (data.__type.includes('UserNotFoundException')) setError('No account found with this email')
        else if (data.__type.includes('UserNotConfirmedException')) { setNeedsVerification(true); setError('') }
        else setError(data.message || 'Login failed. Please try again.')
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyCode = async (e) => {
    e.preventDefault()
    setError('')
    setVerifying(true)

    try {
      const response = await fetch(
        `https://cognito-idp.${API_CONFIG.region}.amazonaws.com/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-amz-json-1.1', 'X-Amz-Target': 'AWSCognitoIdentityProviderService.ConfirmSignUp' },
          body: JSON.stringify({ ClientId: API_CONFIG.clientId, Username: email, ConfirmationCode: verificationCode })
        }
      )
      const data = await response.json()
      if (data.__type) {
        if (data.__type.includes('CodeMismatchException')) setError('Invalid verification code.')
        else if (data.__type.includes('ExpiredCodeException')) setError('Code expired. Please request a new one.')
        else setError(data.message || 'Verification failed.')
      } else {
        setNeedsVerification(false)
        setVerificationCode('')
        handleSubmit(e)
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setVerifying(false)
    }
  }

  const handleResendCode = async () => {
    setError('')
    setResending(true)
    try {
      const response = await fetch(
        `https://cognito-idp.${API_CONFIG.region}.amazonaws.com/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-amz-json-1.1', 'X-Amz-Target': 'AWSCognitoIdentityProviderService.ResendConfirmationCode' },
          body: JSON.stringify({ ClientId: API_CONFIG.clientId, Username: email })
        }
      )
      const data = await response.json()
      if (data.__type) setError(data.message || 'Failed to resend code.')
      else alert('A new verification code has been sent to your email!')
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setResending(false)
    }
  }

  if (needsVerification) {
    return (
      <div className="login-container">
        <div className="grid-background"></div>
        <div className="login-wrapper">
          <div className="login-brand">
            <div className="brand-icon"><WinningTeamLogo size={80} /></div>
            <h1 className="brand-title"><span className="text-accent">THE_WINNING</span>_TEAM</h1>
            <p className="brand-subtitle"><Terminal size={14} style={{ display: 'inline', marginRight: 8 }} />Email Verification Required</p>
          </div>
          <div className="login-card schema-card">
            <div className="schema-card-header"><KeyRound size={16} className="icon" /><span className="title">auth.verify()</span></div>
            <div className="schema-card-body">
              <div className="verification-info">
                <p>We sent a verification code to:</p>
                <p className="email-highlight">{email}</p>
                <p className="text-muted text-sm">Enter the 6-digit code below.</p>
              </div>
              <form onSubmit={handleVerifyCode}>
                {error && <div className="error-message fade-in"><Zap size={16} /><span>{error}</span></div>}
                <div className="input-group">
                  <label className="input-label"><KeyRound size={12} style={{ display: 'inline', marginRight: 6 }} />VERIFICATION CODE</label>
                  <input type="text" className="input-field verification-input" placeholder="000000" value={verificationCode} onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))} maxLength={6} required autoFocus />
                </div>
                <button type="submit" className="btn btn-primary btn-full" disabled={verifying || verificationCode.length !== 6}>
                  {verifying ? <><div className="spinner"></div><span>VERIFYING...</span></> : <><KeyRound size={18} /><span>VERIFY ACCOUNT</span></>}
                </button>
              </form>
              <div className="verification-actions">
                <button type="button" className="btn-link" onClick={handleResendCode} disabled={resending}>{resending ? 'Sending...' : "Didn't receive code? Resend"}</button>
                <button type="button" className="btn-link" onClick={() => { setNeedsVerification(false); setVerificationCode(''); setError('') }}><ArrowLeft size={14} />Back to Login</button>
              </div>
            </div>
          </div>
        </div>
        <style>{`
          .login-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; position: relative; overflow: hidden; }
          .grid-background { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px); background-size: 50px 50px; pointer-events: none; }
          .login-wrapper { width: 100%; max-width: 420px; z-index: 1; }
          .login-brand { text-align: center; margin-bottom: 32px; }
          .brand-icon { display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px; }
          .brand-title { font-family: var(--font-mono); font-size: 1.75rem; font-weight: 700; margin-bottom: 8px; }
          .brand-subtitle { font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted); }
          .verification-info { text-align: center; margin-bottom: 24px; font-family: var(--font-mono); }
          .verification-info p { margin-bottom: 8px; }
          .email-highlight { color: var(--accent-primary); font-weight: 600; font-size: 1rem; }
          .text-sm { font-size: 0.8rem; }
          .verification-input { text-align: center; font-size: 1.5rem !important; letter-spacing: 0.5rem; font-weight: 600; }
          .verification-actions { display: flex; flex-direction: column; align-items: center; gap: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border-color); }
          .btn-link { background: none; border: none; color: var(--accent-primary); font-family: var(--font-mono); font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 6px; }
          .btn-link:hover { opacity: 0.8; }
          .btn-link:disabled { opacity: 0.5; cursor: not-allowed; }
          .error-message { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: rgba(255, 107, 107, 0.1); border: 1px solid var(--priority-critical); border-radius: 6px; color: var(--priority-critical); font-family: var(--font-mono); font-size: 0.85rem; margin-bottom: 20px; }
          .btn-full { width: 100%; padding: 14px 24px; margin-top: 8px; }
          .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }
        `}</style>
      </div>
    )
  }

  return (
    <div className="login-container">
      <div className="grid-background"></div>
      <div className="login-wrapper">
        <div className="login-brand">
          <div className="brand-icon"><WinningTeamLogo size={80} /></div>
          <h1 className="brand-title"><span className="text-accent">THE_WINNING</span>_TEAM</h1>
          <p className="brand-subtitle"><Terminal size={14} style={{ display: 'inline', marginRight: 8 }} />Precision Support Portal</p>
        </div>
        <div className="login-card schema-card">
          <div className="schema-card-header"><Lock size={16} className="icon" /><span className="title">auth.login()</span></div>
          <div className="schema-card-body">
            <form onSubmit={handleSubmit}>
              {error && <div className="error-message fade-in"><Zap size={16} /><span>{error}</span></div>}
              <div className="input-group">
                <label className="input-label"><Mail size={12} style={{ display: 'inline', marginRight: 6 }} />EMAIL</label>
                <input type="email" className="input-field" placeholder="user@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
              </div>
              <div className="input-group">
                <label className="input-label"><Lock size={12} style={{ display: 'inline', marginRight: 6 }} />PASSWORD</label>
                <div className="input-with-icon password-field">
                  <input type={showPassword ? 'text' : 'password'} className="input-field" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
                  <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button>
                </div>
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                {loading ? <><div className="spinner"></div><span>AUTHENTICATING...</span></> : <><Terminal size={18} /><span>INITIALIZE SESSION</span></>}
              </button>
            </form>
            <div className="login-footer"><span className="text-muted">No account?</span><Link to="/signup" className="signup-link">CREATE_USER →</Link></div>
          </div>
        </div>
        <div className="schema-preview">
          <code className="text-muted text-xs">// Authentication Schema<br /><span className="text-accent">user</span> {'{'}email: <span className="text-accent">VARCHAR</span>, role: <span className="text-accent">ENUM</span>{'}'}</code>
        </div>
      </div>
      <style>{`
        .login-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; position: relative; overflow: hidden; }
        .grid-background { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px); background-size: 50px 50px; pointer-events: none; }
        .login-wrapper { width: 100%; max-width: 420px; z-index: 1; }
        .login-brand { text-align: center; margin-bottom: 32px; }
        .brand-icon { display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px; }
        .brand-title { font-family: var(--font-mono); font-size: 1.75rem; font-weight: 700; margin-bottom: 8px; }
        .brand-subtitle { font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted); }
        .login-card { margin-bottom: 24px; }
        .error-message { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: rgba(255, 107, 107, 0.1); border: 1px solid var(--priority-critical); border-radius: 6px; color: var(--priority-critical); font-family: var(--font-mono); font-size: 0.85rem; margin-bottom: 20px; }
        .input-with-icon { position: relative; }
        .password-field .input-field { padding-right: 48px; }
        .password-toggle { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; }
        .password-toggle:hover { color: var(--accent-primary); }
        .btn-full { width: 100%; padding: 14px 24px; margin-top: 8px; }
        .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }
        .login-footer { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 24px; padding-top: 24px; border-top: 1px solid var(--border-color); font-family: var(--font-mono); font-size: 0.85rem; }
        .signup-link { color: var(--accent-primary); font-weight: 600; }
        .signup-link:hover { text-decoration: underline; }
        .schema-preview { text-align: center; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; }
        .schema-preview code { display: block; text-align: left; line-height: 1.8; }
      `}</style>
    </div>
  )
}

export default Login
