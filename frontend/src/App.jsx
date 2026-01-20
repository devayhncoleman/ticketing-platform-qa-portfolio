import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, createContext } from 'react'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import TicketDetail from './pages/TicketDetail'
import './index.css'

// Auth Context
export const AuthContext = createContext(null)

// API Configuration
export const API_CONFIG = {
  baseUrl: 'https://xs8nrtxpf8.execute-api.us-east-1.amazonaws.com/dev',
  region: 'us-east-1',
  userPoolId: 'us-east-1_aOPphSFcM',
  clientId: '2rm459s3kdlhrr33pvbndmuc1n'
}

function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark')

  // Check for existing token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    
    if (storedToken && storedUser) {
      setToken(storedToken)
      setUser(JSON.parse(storedUser))
    }
    setLoading(false)
  }, [])

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const login = (userData, authToken) => {
    setUser(userData)
    setToken(authToken)
    localStorage.setItem('token', authToken)
    localStorage.setItem('user', JSON.stringify(userData))
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

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '100vh' }}>
        <div className="spinner" style={{ width: 40, height: 40 }}></div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, theme, toggleTheme }}>
      <Router>
        <Routes>
          <Route 
            path="/login" 
            element={token ? <Navigate to="/dashboard" /> : <Login />} 
          />
          <Route 
            path="/signup" 
            element={token ? <Navigate to="/dashboard" /> : <Signup />} 
          />
          <Route 
            path="/dashboard" 
            element={token ? <Dashboard /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/tickets/:id" 
            element={token ? <TicketDetail /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/" 
            element={<Navigate to={token ? "/dashboard" : "/login"} />} 
          />
        </Routes>
      </Router>
    </AuthContext.Provider>
  )
}

export default App
