/** Resolve the backend origin from the shared root environment configuration. */
export function getBackendUrl(): string {
  return (
    process.env.KIRA_API_URL?.replace(/\/$/, '') ||
    `http://127.0.0.1:${process.env.BACKEND_PORT || '8006'}`
  )
}
