/** Auth utility functions */

const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000 // 5 minutes

export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

export function shouldRefreshToken(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const expiresAt = payload.exp * 1000
    return expiresAt - Date.now() < TOKEN_REFRESH_THRESHOLD
  } catch {
    return true
  }
}

export function getTokenExpireTime(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000
  } catch {
    return null
  }
}
