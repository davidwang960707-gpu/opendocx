/** 认证状态管理 */
import { create } from 'zustand'
import { authApi } from '../services/api'

interface User {
  id: string
  email: string
  name: string
  role: string
}

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  loading: true,

  login: async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    const { access_token } = res.data.data
    localStorage.setItem('token', access_token)
    set({ token: access_token })

    const userRes = await authApi.getMe()
    set({ user: userRes.data.data, loading: false })
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null })
  },

  checkAuth: async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      set({ loading: false })
      return
    }
    try {
      const res = await authApi.getMe()
      set({ user: res.data.data, loading: false })
    } catch {
      localStorage.removeItem('token')
      set({ user: null, token: null, loading: false })
    }
  },
}))
