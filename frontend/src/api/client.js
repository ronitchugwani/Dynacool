import axios from 'axios'

const API = import.meta.env.VITE_API_URL

const apiClient = axios.create({
  baseURL: API,
  timeout: 15000,
})

function buildParams(filters = {}) {
  const params = {}

  if (filters.year && filters.year !== 'all') {
    params.year = filters.year
  }
  if (filters.customer && filters.customer !== 'all') {
    params.customer = filters.customer
  }
  if (filters.product && filters.product !== 'all') {
    params.product = filters.product
  }

  return params
}

export async function fetchDashboardData(filters = {}) {
  const params = buildParams(filters)

  const [kpisRes, monthlyRes, customersRes, gstRes, productsRes, categoriesRes] = await Promise.all([
    apiClient.get('/kpis', { params }),
    apiClient.get('/monthly-sales', { params }),
    apiClient.get('/top-customers', { params }),
    apiClient.get('/gst', { params }),
    apiClient.get('/top-products', { params }),
    apiClient.get('/category-sales', { params }),
  ])

  return {
    kpis: kpisRes.data,
    monthlySales: monthlyRes.data,
    topCustomers: customersRes.data,
    gst: gstRes.data,
    topProducts: productsRes.data,
    categorySales: categoriesRes.data,
  }
}

export async function fetchFilterOptions(filters = {}) {
  const params = buildParams(filters)
  const response = await apiClient.get('/filters', { params })
  return response.data
}

export default apiClient
