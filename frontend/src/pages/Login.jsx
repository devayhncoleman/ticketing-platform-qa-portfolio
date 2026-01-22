import { useState, useContext } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Mail, Lock, AlertCircle, LogIn, Eye, EyeOff } from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'
import axios from 'axios'

// Trophy with Arrow Logo Component
const WinningTeamLogo = ({ size = 64 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    {/* Outer glow effect */}
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    
    {/* Trophy Cup */}
    <path 
      d="M20 12H44V14C44 14 46 14 48 16C50 18 50 22 48 24C46 26 44 26 44 26V28C44 32 40 36 36 38V42H40C40 42 42 42 42 44V46H22V44C22 42 24 42 24 42H28V38C24 36 20 32 20 28V26C20 26 18 26 16 24C14 22 14 18 16 16C18 14 20 14 20 14V12Z" 
      stroke="#00ff41" 
      strokeWidth="2" 
      fill="rgba(0, 255, 65, 0.1)"
      filter="url(#glow)"
    />
    
    {/* Trophy handles */}
    <path 
      d="M20 16C18 16 16 18 16 20C16 22 18 24 20 24" 
      stroke="#00ff41" 
      strokeWidth="2" 
      fill="none"
    />
    <path 
      d="M44 16C46 16 48 18 48 20C48 22 46 24 44 24" 
      stroke="#00ff41" 
      strokeWidth="2" 
      fill="none"
    />
    
    {/* Trophy base */}
    <rect x="26" y="46" width="12" height="4" stroke="#00ff41" strokeWidth="2" fill="rgba(0, 255, 65, 0.1)"/>
    <rect x="22" y="50" width="20" height="3" stroke="#00ff41" strokeWidth="2" fill="rgba(0, 255, 65, 0.1)"/>
    
    {/* Arrow going through trophy - tilted for dynamic effect */}
    <g transform="rotate(-15, 32, 24)">
      {/* Arrow shaft */}
      <line x1="8" y1="24" x2="56" y2="24" stroke="#00ff41" strokeWidth="2.5" filter="url(#glow)"/>
      {/* Arrow head */}
      <path d="M52 24L46 20V28L52 24Z" fill="#00ff41" filter="url(#glow)"/>
      {/* Arrow fletching */}
      <path d="M12 24L16 20M12 24L16 28" stroke="#00ff41" strokeWidth="2"/>
    </g>
    
    {/* Bullseye/target circle in trophy center */}
    <circle cx="32" cy="22" r="6" stroke="#00ff41" strokeWidth="1.5" fill="none" opacity="0.7"/>
    <circle cx="32" cy="22" r="3" stroke="#00ff41" strokeWidth="1.5" fill="none" opacity="0.7"/>
    <circle cx="32" cy="22" r="1" fill="#00ff41"/>
  </svg>
)

export default function Login() {
  const navigate = useNavigate()
  const { login: contextLogin } = useContext(AuthContext)
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      console.log('=== LOGIN START ===')
      console.log('Email:', email)
      
      // Step 1: Authenticate with Cognito
      console.log('[Step 1] Calling Cognito...')
      
      const authResponse = await axios.post(
        `https://cognito-idp.${API_CONFIG.region}.amazonaws.com/`,
        {
          ClientId: API_CONFIG.clientId,
          AuthFlow: 'USER_PASSWORD_AUTH',
          AuthParameters: {
            USERNAME: email,
            PASSWORD: password
          }
        },
        {
          headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
          }
        }
      )

      console.log('[Step 1] ✓ Cognito auth successful')
      
      const idToken = authResponse.data.AuthenticationResult.IdToken
      console.log('[Step 1] ID Token received')

      // Step 2: Decode token
      console.log('[Step 2] Decoding JWT token...')
      
      const tokenParts = idToken.split('.')
      if (tokenParts.length !== 3) {
        throw new Error('Invalid token format')
      }
      
      const decodedToken = JSON.parse(atob(tokenParts[1]))
      console.log('[Step 2] ✓ Token decoded')
      console.log('[Step 2] Token claims:', {
        email: decodedToken.email,
        given_name: decodedToken.given_name,
        family_name: decodedToken.family_name,
        sub: decodedToken.sub
      })

      // Step 3: FETCH ROLE FROM /users/me (CRITICAL)
      console.log('[Step 3] Fetching role from /users/me...')
      
      let userRole = 'CUSTOMER'
      let roleSource = 'default'
      
      try {
        const roleResponse = await axios.get(
          `${API_CONFIG.baseUrl}/users/me`,
          {
            headers: {
              Authorization: `Bearer ${idToken}`,
              'Content-Type': 'application/json'
            }
          }
        )
        
        console.log('[Step 3] Response status:', roleResponse.status)
        console.log('[Step 3] Response data:', roleResponse.data)
        
        if (roleResponse.data && roleResponse.data.role) {
          userRole = roleResponse.data.role
          roleSource = 'database'
          console.log('[Step 3] ✓ Role from database:', userRole)
        } else {
          console.warn('[Step 3] ⚠ No role in response, using default')
        }
      } catch (roleError) {
        console.error('[Step 3] ✗ Error fetching role:', roleError.message)
        console.error('[Step 3] Status:', roleError.response?.status)
        console.error('[Step 3] Data:', roleError.response?.data)
        console.warn('[Step 3] Using default CUSTOMER role')
        roleSource = 'default'
      }

      // Step 4: Create user object with GUARANTEED role
      console.log('[Step 4] Creating user object...')
      
      const userData = {
        email: decodedToken.email || email,
        firstName: decodedToken.given_name || decodedToken.name || 'User',
        lastName: decodedToken.family_name || '',
        sub: decodedToken.sub,
        role: userRole
      }

      console.log('[Step 4] ✓ User object created:')
      console.log('  Email:', userData.email)
      console.log('  Name:', `${userData.firstName} ${userData.lastName}`)
      console.log('  Role:', userData.role)
      console.log('  Role Source:', roleSource)
      console.log('  Sub:', userData.sub)

      // Step 5: Store in context (saves to localStorage)
      console.log('[Step 5] Storing user in context...')
      
      contextLogin(userData, idToken)
      
      console.log('[Step 5] ✓ User stored')
      console.log('[Step 5] localStorage.user:', localStorage.getItem('user'))

      // Step 6: Navigate based on role
      console.log('[Step 6] Navigating based on role:', userData.role)
      
      if (userData.role === 'ADMIN') {
        console.log('[Step 6] → Redirecting to /admin')
        navigate('/admin', { replace: true })
      } else if (userData.role === 'TECH') {
        console.log('[Step 6] → Redirecting to /tech')
        navigate('/tech', { replace: true })
      } else {
        console.log('[Step 6] → Redirecting to /dashboard')
        navigate('/dashboard', { replace: true })
      }
      
      console.log('=== LOGIN SUCCESS ===')

    } catch (err) {
      console.error('=== LOGIN ERROR ===')
      console.error('Error:', err)
      console.error('Message:', err.message)
      
      let errorMessage = 'Login failed. Check your credentials.'
      
      if (err.response?.data?.message) {
        errorMessage = err.response.data.message
      } else if (err.response?.data?.__type === 'NotAuthorizedException') {
        errorMessage = 'Invalid email or password'
      } else if (err.response?.data?.__type === 'UserNotConfirmedException') {
        errorMessage = 'Please verify your email before logging in'
      } else if (err.response?.status === 400) {
        errorMessage = 'Invalid email or password'
      } else if (err.message) {
        errorMessage = err.message
      }
      
      console.error('Final error message:', errorMessage)
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '420px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '40px 32px'
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '8px' }}>
          <WinningTeamLogo size={72} />
        </div>

        {/* Brand Name */}
        <div style={{ textAlign: 'center', marginBottom: '4px' }}>
          <h1 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.4rem',
            color: 'var(--accent-primary)',
            letterSpacing: '2px',
            margin: 0
          }}>
            THE_WINNING_TEAM
          </h1>
        </div>

        {/* Tagline */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <p style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            margin: 0
          }}>
            <span style={{ color: 'var(--accent-primary)' }}>&gt;_ </span>
            <span style={{ 
              color: 'var(--accent-primary)', 
              background: 'rgba(0, 255, 65, 0.15)',
              padding: '2px 6px',
              borderRadius: '3px'
            }}>Precision</span>
            {' '}Support Portal
          </p>
        </div>

        {/* Login Header */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.1rem',
            color: 'var(--text-primary)',
            marginBottom: '4px'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>&gt;_ </span>
            login()
          </h2>
          <p style={{
            color: 'var(--text-muted)',
            fontSize: '0.8rem',
            margin: 0
          }}>
            Sign in to your account
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div style={{
            background: 'rgba(255, 107, 107, 0.1)',
            border: '1px solid #ff6b6b',
            borderRadius: '6px',
            padding: '12px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#ff6b6b',
            fontSize: '0.85rem'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Email */}
          <div>
            <label style={{
              display: 'block',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              marginBottom: '6px',
              textTransform: 'uppercase'
            }}>
              Email Address
            </label>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              paddingLeft: '12px'
            }}>
              <Mail size={16} style={{ color: 'var(--text-muted)' }} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                disabled={loading}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  padding: '12px 12px',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: loading ? 'not-allowed' : 'auto'
                }}
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label style={{
              display: 'block',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              marginBottom: '6px',
              textTransform: 'uppercase'
            }}>
              Password
            </label>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              paddingLeft: '12px'
            }}>
              <Lock size={16} style={{ color: 'var(--text-muted)' }} />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={loading}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  padding: '12px 12px',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: loading ? 'not-allowed' : 'auto'
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                disabled={loading}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  padding: '8px 12px',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Sign In Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              background: 'var(--accent-primary)',
              color: 'var(--bg-primary)',
              border: 'none',
              borderRadius: '6px',
              padding: '12px 16px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              marginTop: '8px',
              transition: 'all 0.3s ease'
            }}
          >
            <LogIn size={16} />
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {/* Links */}
        <div style={{
          marginTop: '24px',
          paddingTop: '20px',
          borderTop: '1px solid var(--border-color)',
          textAlign: 'center'
        }}>
          <p style={{
            color: 'var(--text-muted)',
            fontSize: '0.85rem',
            marginBottom: '12px'
          }}>
            Don't have an account?{' '}
            <Link
              to="/signup"
              style={{
                color: 'var(--accent-primary)',
                textDecoration: 'none',
                fontWeight: 600
              }}
            >
              Sign up
            </Link>
          </p>
          <Link
            to="/forgot-password"
            style={{
              color: 'var(--text-muted)',
              textDecoration: 'none',
              fontSize: '0.8rem'
            }}
          >
            Forgot password?
          </Link>
        </div>
      </div>

      <style>{`
        input:focus {
          outline: none;
        }
        button:hover:not(:disabled) {
          box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
        }
      `}</style>
    </div>
  )
}
