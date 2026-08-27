// 127.0.0.1, not localhost: on some Windows setups "localhost" resolves to
// the IPv6 loopback (::1) first, which nothing is listening on since
// uvicorn's default bind is IPv4-only (127.0.0.1) - the connection then
// hangs or fails outright ("Failed to fetch") even though the backend is
// up and reachable. 127.0.0.1 skips that resolution step entirely.
// VITE_API_BASE_URL still overrides this for any deployment that needs to.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export async function uploadReport(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Upload failed (${response.status})`)
  }

  return response.json()
}

export async function reviewLog(logFile, labFiles = []) {
  const formData = new FormData()
  formData.append('file', logFile)
  for (const labFile of labFiles) {
    formData.append('lab_reports', labFile)
  }

  const response = await fetch(`${API_BASE_URL}/review-log`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Review failed (${response.status})`)
  }

  return response.json()
}
