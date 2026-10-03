import axios from 'axios'

export async function submitVisualScan(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await axios.post('/api/visual_scan', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })

  return response.data
}
