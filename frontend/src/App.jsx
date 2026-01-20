import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, createContext } from 'react'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import TicketDetail from './pages/TicketDetail'
import Profile from './pages/Profile'
import ForgotPassword from './pages/ForgotPassword'
import AdminConsole from './pages/AdminConsole'
import TechDashboard from './pages/TechDashboard'
import './index.css'

// Auth Context
export const AuthContext = createContext(null)

// API Configuration - UPDATE THIS WITH YOUR NEW CLIENT ID FROM CDK OUTPUTS
export const API_CONFIG = {
  baseUrl: 'https://i3we9t67d7.execute-api.us-east-1.amazonaws.com/dev',
  region: 'us-east-1',
  userPoolId: 'us-east-1_GFpDaowfi',
  clientId: '592r9340r38hh9igdnc1bdokpr'  // 👈 REPLACE THIS with output from: cdk deploy
}

// Protected route - only allows specific roles
const ProtectedRoute = ({ children, requiredRoles, userRole, isLoggedIn }) => {
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />
  }
  
  if (!requiredRoles.includes(userRole)) {
    console.warn(`[ProtectedRoute] Access denied. User role: ${userRole}, Required: ${requiredRoles.join(', ')}`)
    return <Navigate to="/dashboard" replace />
  }
  
  return children
}

function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark')

  // Check for existing session
  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    
    if (storedToken && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser)
        setToken(storedToken)
        setUser(parsedUser)
      } catch (err) {
        console.error('Error parsing stored user:', err)
        localStorage.removeItem('user')
        localStorage.removeItem('token')
      }
    }
    
    setLoading(false)
  }, [])

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const login = (userData, authToken) => {
    const userDataWithRole = {
      email: userData.email || '',
      firstName: userData.firstName || 'User',
      lastName: userData.lastName || '',
      sub: userData.sub || '',
      role: userData.role || 'CUSTOMER'
    }
    
    setUser(userDataWithRole)
    setToken(authToken)
    localStorage.setItem('token', authToken)
    localStorage.setItem('user', JSON.stringify(userDataWithRole))
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'lime' : 'dark')
  }

  const userRole = user?.role || 'CUSTOMER'
  const isLoggedIn = !!token

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
        <div className="spinner"></div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, theme, toggleTheme, userRole }}>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route 
            path="/login" 
            element={
              isLoggedIn ? (
                userRole === 'ADMIN' ? <Navigate to="/admin" /> :
                userRole === 'TECH' ? <Navigate to="/tech" /> :
                <Navigate to="/dashboard" />
              ) : <Login />
            } 
          />
          <Route 
            path="/signup" 
            element={isLoggedIn ? <Navigate to="/dashboard" /> : <Signup />} 
          />
          <Route 
            path="/forgot-password" 
            element={isLoggedIn ? <Navigate to="/dashboard" /> : <ForgotPassword />} 
          />

          {/* Customer Routes */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute requiredRoles={['CUSTOMER', 'TECH', 'ADMIN']} userRole={userRole} isLoggedIn={isLoggedIn}>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/tickets/:id" 
            element={
              <ProtectedRoute requiredRoles={['CUSTOMER', 'TECH', 'ADMIN']} userRole={userRole} isLoggedIn={isLoggedIn}>
                <TicketDetail />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/profile" 
            element={
              <ProtectedRoute requiredRoles={['CUSTOMER', 'TECH', 'ADMIN']} userRole={userRole} isLoggedIn={isLoggedIn}>
                <Profile />
              </ProtectedRoute>
            } 
          />

          {/* ADMIN Only */}
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute requiredRoles={['ADMIN']} userRole={userRole} isLoggedIn={isLoggedIn}>
                <AdminConsole />
              </ProtectedRoute>
            } 
          />

          {/* TECH + ADMIN */}
          <Route 
            path="/tech" 
            element={
              <ProtectedRoute requiredRoles={['TECH', 'ADMIN']} userRole={userRole} isLoggedIn={isLoggedIn}>
                <TechDashboard />
              </ProtectedRoute>
            } 
          />

          {/* Default redirect */}
          <Route 
            path="/" 
            element={
              <Navigate to={
                isLoggedIn ? (
                  userRole === 'ADMIN' ? '/admin' :
                  userRole === 'TECH' ? '/tech' :
                  '/dashboard'
                ) : '/login'
              } />
            } 
          />
          
          {/* 404 */}
          <Route 
            path="*" 
            element={
              <Navigate to={
                isLoggedIn ? (
                  userRole === 'ADMIN' ? '/admin' :
                  userRole === 'TECH' ? '/tech' :
                  '/dashboard'
                ) : '/login'
              } />
            } 
          />
        </Routes>
      </Router>
    </AuthContext.Provider>
  )
}

export default App
