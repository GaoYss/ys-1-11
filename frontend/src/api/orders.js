import { http } from './http'

export const ordersApi = {
  list(params = {}) {
    return http.get('/orders', { params })
  },
  create(payload) {
    return http.post('/orders', payload)
  },
  updateStatus(id, status) {
    return http.put(`/orders/${id}/status`, { status })
  },
  getAvgPrice(ingredientId) {
    return http.get(`/orders/avg-price/${ingredientId}`)
  }
}
