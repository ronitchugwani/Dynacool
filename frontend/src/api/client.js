import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 15000,
})

export async function fetchDashboardData(filters = {}) {
  const params = {}
  if (filters.year && filters.year !== 'all') {
    params.year = filters.year
  }
  if (filters.customer && filters.customer !== 'all') {
    params.customer = filters.customer
  }

  const [kpisRes, monthlyRes, customersRes, gstRes] = await Promise.all([
    apiClient.get('/kpis', { params }),
    apiClient.get('/monthly-sales', { params }),
    apiClient.get('/top-customers', { params }),
    apiClient.get('/gst', { params }),
  ])

  return {
    kpis: kpisRes.data,
    monthlySales: monthlyRes.data,
    topCustomers: customersRes.data,
    gst: gstRes.data,
  }
}

export default apiClient
