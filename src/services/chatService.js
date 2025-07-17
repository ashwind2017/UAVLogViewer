import axios from 'axios'

class ChatService {
  constructor() {
    this.baseURL = 'http://localhost:8000/api'
  }

  async uploadFlightFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      const response = await axios.post(`${this.baseURL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data
    } catch (error) {
      console.error('Error uploading file:', error)
      throw error
    }
  }

  async sendChatMessage(message, flightId = null) {
    try {
      const response = await axios.post(`${this.baseURL}/chat`, {
        message,
        flight_id: flightId
      })
      return response.data
    } catch (error) {
      console.error('Error sending chat message:', error)
      throw error
    }
  }

  async getFlights() {
    try {
      const response = await axios.get(`${this.baseURL}/flights`)
      return response.data
    } catch (error) {
      console.error('Error fetching flights:', error)
      throw error
    }
  }

  async getFlightDetails(flightId) {
    try {
      const response = await axios.get(`${this.baseURL}/flights/${flightId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching flight details:', error)
      throw error
    }
  }
}

export default new ChatService()