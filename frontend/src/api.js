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

export async function soilParameters(logFile) {
  const formData = new FormData()
  formData.append('file', logFile)

  const response = await fetch(`${API_BASE_URL}/soil-parameters`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Soil parameter derivation failed (${response.status})`)
  }

  return response.json()
}

export async function rockParameters(logFile) {
  const formData = new FormData()
  formData.append('file', logFile)

  const response = await fetch(`${API_BASE_URL}/rock-parameters`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Rock parameter derivation failed (${response.status})`)
  }

  return response.json()
}

/**
 * POST /report - formats whatever's already been fetched from
 * /review-log, /soil-parameters, and/or /rock-parameters (any/all
 * optional) into a downloadable PDF. `results` values are the raw parsed
 * JSON already held in the calling page's state, JSON-stringified here
 * since the endpoint takes them as multipart form fields, not a JSON
 * body (it needs `file` alongside them). No recomputation - the file
 * itself is only used for its filename.
 */
export async function downloadReport(logFile, { reviewLogResult, soilParametersResult, rockParametersResult } = {}) {
  const formData = new FormData()
  formData.append('file', logFile)
  if (reviewLogResult) formData.append('review_log_result', JSON.stringify(reviewLogResult))
  if (soilParametersResult) formData.append('soil_parameters_result', JSON.stringify(soilParametersResult))
  if (rockParametersResult) formData.append('rock_parameters_result', JSON.stringify(rockParametersResult))

  const response = await fetch(`${API_BASE_URL}/report`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Report generation failed (${response.status})`)
  }

  return response.blob()
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
