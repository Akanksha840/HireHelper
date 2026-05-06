export function getStoredToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  return localStorage.getItem('token') || sessionStorage.getItem('token')
}

export function getStoredUser(): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  return localStorage.getItem('user') || sessionStorage.getItem('user')
}
