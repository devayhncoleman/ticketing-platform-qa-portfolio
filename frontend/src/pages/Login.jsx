import { useState, useContext } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Mail, Lock, AlertCircle, LogIn, Eye, EyeOff } from 'lucide-react'
import { AuthContext, API_CONFIG } from '../App'
import axios from 'axios'

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
        role: userRole  // THIS WILL BE SET FROM /users/me OR DEFAULT
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
        maxWidth: '400px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '40px 24px'
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '1.5rem',
            color: 'var(--accent-primary)',
            marginBottom: '8px'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>&gt;_ </span>
            login()
          </h1>
          <p style={{
            color: 'var(--text-muted)',
            fontSize: '0.85rem'
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
      `}</style>
    </div>
  )
}
