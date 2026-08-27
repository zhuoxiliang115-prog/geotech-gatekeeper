const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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
