// No existing download/Blob precedent anywhere in this frontend before
// the PDF report export feature - every prior response is consumed as
// JSON. This is the standard object-URL-plus-temporary-anchor pattern for
// saving a Blob the browser fetched via XHR/fetch rather than navigated
// to directly.
export function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
