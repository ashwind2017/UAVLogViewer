<template>
  <div class="chat-interface">
    <div class="chat-content">
        <div class="chat-header">
          <h4>
            <i class="fas fa-robot"></i>
            UAV Flight Assistant
          </h4>
          <div v-if="currentFlight" class="flight-info">
            <small>
              <i class="fas fa-plane"></i>
              Flight: {{ currentFlight.flight_id.slice(0, 8) }}...
              | Duration: {{ currentFlight.summary.duration.toFixed(1) }}s
              | Max Alt: {{ currentFlight.summary.max_altitude.toFixed(0) }}m
            </small>
          </div>
        </div>
        
        <div class="tab-navigation" v-if="currentFlight">
          <div class="tab-buttons">
            <button 
              class="tab-btn" 
              :class="{ active: activeTab === 'chat' }"
              @click="activeTab = 'chat'"
            >
              <i class="fas fa-comments"></i>
              Chat
            </button>
            <button 
              class="tab-btn" 
              :class="{ active: activeTab === 'dashboard' }"
              @click="activeTab = 'dashboard'"
            >
              <i class="fas fa-tachometer-alt"></i>
              Dashboard
            </button>
          </div>
        </div>

        <div class="file-upload-section" v-if="!currentFlight">
          <div class="upload-area" @drop="handleDrop" @dragover.prevent @dragenter.prevent>
            <input 
              type="file" 
              ref="fileInput" 
              @change="handleFileSelect" 
              accept=".bin"
              class="file-input"
            >
            <div class="upload-content">
              <i class="fas fa-upload"></i>
              <p>Drop a .bin flight log file here or click to select</p>
              <button class="btn btn-primary" @click="$refs.fileInput.click()">
                Choose File
              </button>
            </div>
          </div>
          <div v-if="uploadProgress" class="upload-progress">
            <div class="progress">
              <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
            </div>
            <small>Uploading and parsing flight data...</small>
          </div>
        </div>

        <!-- Chat Tab Content -->
        <div class="tab-content" v-if="activeTab === 'chat' || !currentFlight">
          <div class="proactive-suggestions" v-if="proactiveSuggestions.length > 0">
            <h5>💡 Suggested Topics</h5>
            <div v-for="suggestion in proactiveSuggestions" :key="suggestion" class="suggestion-item">
              <button @click="askSuggestion(suggestion)" class="suggestion-btn">
                {{ suggestion }}
              </button>
            </div>
          </div>

          <div class="comparison-insights" v-if="comparisonInsights">
            <h5>📊 Flight Comparison</h5>
            <p>{{ comparisonInsights }}</p>
          </div>

          <div class="chat-messages" ref="chatMessages">
            <div v-for="message in messages" :key="message.id" class="message" :class="message.type">
              <div class="message-content">
                <div class="message-text">{{ message.text }}</div>
                <div class="message-time">{{ formatTime(message.timestamp) }}</div>
              </div>
            </div>
            <div v-if="isTyping" class="message assistant">
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <div class="chat-input">
            <div class="input-group">
              <input 
                type="text" 
                v-model="currentMessage" 
                @keypress.enter="sendMessage"
                placeholder="Ask about flight data..."
                class="form-control"
                :disabled="!currentFlight || isTyping"
              >
              <div class="input-group-append">
                <button 
                  class="btn btn-primary" 
                  @click="sendMessage"
                  :disabled="!currentMessage.trim() || !currentFlight || isTyping"
                >
                  <i class="fas fa-paper-plane"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Dashboard Tab Content -->
        <div class="tab-content" v-if="activeTab === 'dashboard'">
          <AnalysisDashboard 
            :flight-data="currentFlight"
            :historical-data="historicalFlights"
          />
        </div>
      </div>
      
      <!-- Bottom Visualization (Always Visible) -->
      <div class="visualization-section" v-if="currentFlight">
        <FlightPathVisualization :flight-data="currentFlight"/>
      </div>
    </div>
  </div>
</template>

<script>
import chatService from '../services/chatService'
import FlightPathVisualization from './FlightPathVisualization.vue'
import AnalysisDashboard from './AnalysisDashboard.vue'

export default {
  name: 'ChatInterface',
  components: {
    FlightPathVisualization,
    AnalysisDashboard
  },
  data() {
    return {
      messages: [],
      currentMessage: '',
      currentFlight: null,
      isTyping: false,
      uploadProgress: 0,
      nextMessageId: 1,
      proactiveSuggestions: [],
      comparisonInsights: '',
      activeTab: 'chat',
      historicalFlights: []
    }
  },
  mounted() {
    this.addMessage('assistant', 'Hello! Upload a .bin flight log file to start analyzing your drone flight data.')
  },
  methods: {
    async handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        await this.uploadFile(file)
      }
    },
    
    async handleDrop(event) {
      event.preventDefault()
      const file = event.dataTransfer.files[0]
      if (file && file.name.endsWith('.bin')) {
        await this.uploadFile(file)
      }
    },

    async uploadFile(file) {
      this.uploadProgress = 10
      this.addMessage('user', `Uploading ${file.name}...`)
      
      try {
        this.uploadProgress = 50
        const response = await chatService.uploadFlightFile(file)
        this.uploadProgress = 100
        
        console.log('Upload response:', response)
        console.log('Response telemetry structure:', response.telemetry)
        console.log('GPS data array:', response.telemetry?.gps)
        console.log('GPS data length:', response.telemetry?.gps?.length)
        console.log('Sample GPS points:', response.telemetry?.gps?.slice(0, 3))
        this.currentFlight = response
        this.addMessage('assistant', `Flight data uploaded successfully! I can now analyze your flight data. Duration: ${response.summary.duration.toFixed(1)}s, Max altitude: ${response.summary.max_altitude.toFixed(0)}m.`)
        
        if (response.summary.anomalies && response.summary.anomalies.length > 0) {
          this.addMessage('assistant', `⚠️ I detected some anomalies: ${response.summary.anomalies.join(', ')}. Feel free to ask me about them!`)
        }
        
        setTimeout(() => {
          this.uploadProgress = 0
        }, 1000)
      } catch (error) {
        this.uploadProgress = 0
        this.addMessage('assistant', `Error uploading file: ${error.message}`)
      }
    },

    async sendMessage() {
      if (!this.currentMessage.trim() || !this.currentFlight) return

      const userMessage = this.currentMessage.trim()
      this.addMessage('user', userMessage)
      this.currentMessage = ''
      this.isTyping = true

      try {
        const response = await chatService.sendChatMessage(userMessage, this.currentFlight.flight_id)
        this.addMessage('assistant', response.response)
        
        // Update proactive suggestions
        this.proactiveSuggestions = response.proactive_suggestions || []
        
        // Update comparison insights
        this.comparisonInsights = response.comparison_insights || ''
        
      } catch (error) {
        this.addMessage('assistant', `Sorry, I encountered an error: ${error.message}`)
      } finally {
        this.isTyping = false
      }
    },

    addMessage(type, text) {
      this.messages.push({
        id: this.nextMessageId++,
        type,
        text,
        timestamp: new Date()
      })
      this.$nextTick(() => {
        this.scrollToBottom()
      })
    },

    scrollToBottom() {
      const chatMessages = this.$refs.chatMessages
      if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight
      }
    },

    formatTime(timestamp) {
      return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },

    askSuggestion(suggestion) {
      this.currentMessage = suggestion
      this.sendMessage()
    }
  }
}
</script>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
  min-height: 600px;
}

.chat-layout {
  display: flex;
  height: 100%;
  gap: 8px;
  min-height: 500px;
  flex: 1;
}

.chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 400px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.visualization-section {
  flex: 1;
  min-width: 400px;
  background: #1a1a1a;
  border-radius: 8px;
  border: 1px solid #333;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.viz-placeholder {
  text-align: center;
  padding: 2rem;
}

.viz-placeholder h3 {
  color: #64f4ff;
  margin-bottom: 1rem;
}

.viz-placeholder p {
  margin: 0.5rem 0;
  color: #e2e8f0;
}

.chat-header {
  background: #007bff;
  color: white;
  padding: 1rem;
  border-bottom: 1px solid #dee2e6;
}

.chat-header h4 {
  margin: 0;
  font-size: 1.1rem;
}

.flight-info {
  margin-top: 0.5rem;
  opacity: 0.9;
}

.file-upload-section {
  padding: 1rem;
}

.upload-area {
  border: 2px dashed #007bff;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  background: #f8f9fa;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-area:hover {
  background: #e9ecef;
  border-color: #0056b3;
}

.file-input {
  display: none;
}

.upload-content i {
  font-size: 2rem;
  color: #007bff;
  margin-bottom: 1rem;
}

.upload-progress {
  margin-top: 1rem;
}

.progress {
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #007bff;
  transition: width 0.3s ease;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  max-height: 400px;
}

.message {
  margin-bottom: 1rem;
}

.message.user {
  display: flex;
  justify-content: flex-end;
}

.message.assistant {
  display: flex;
  justify-content: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  position: relative;
}

.user .message-content {
  background: #007bff;
  color: white;
  border-bottom-right-radius: 0.25rem;
}

.assistant .message-content {
  background: white;
  color: #333;
  border: 1px solid #dee2e6;
  border-bottom-left-radius: 0.25rem;
}

.message-text {
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

.message-time {
  font-size: 0.75rem;
  opacity: 0.7;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #666;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  30% {
    transform: scale(1);
    opacity: 1;
  }
}

.chat-input {
  padding: 1rem;
  border-top: 1px solid #dee2e6;
  background: white;
}

.input-group {
  display: flex;
}

.form-control {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 0.375rem 0 0 0.375rem;
  font-size: 0.9rem;
}

.form-control:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.input-group-append .btn {
  border-radius: 0 0.375rem 0.375rem 0;
  padding: 0.75rem 1rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.proactive-suggestions {
  margin: 1rem;
  padding: 1rem;
  background: #e8f4ff;
  border-radius: 8px;
  border: 1px solid #bee5eb;
}

.proactive-suggestions h5 {
  margin: 0 0 0.5rem 0;
  color: #0c5460;
  font-size: 1rem;
}

.suggestion-item {
  margin-bottom: 0.5rem;
}

.suggestion-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  display: block;
  width: 100%;
  text-align: left;
}

.suggestion-btn:hover {
  background: #0056b3;
  transform: translateY(-1px);
}

.comparison-insights {
  margin: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #28a745;
}

.comparison-insights h5 {
  margin: 0 0 0.5rem 0;
  color: #155724;
  font-size: 1rem;
}

.comparison-insights p {
  margin: 0;
  color: #495057;
  font-size: 0.9rem;
}

/* Tab Navigation */
.tab-navigation {
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  padding: 0;
}

.tab-buttons {
  display: flex;
  margin: 0;
  padding: 0;
}

.tab-btn {
  background: none;
  border: none;
  padding: 1rem 1.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: #6c757d;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tab-btn:hover {
  color: #007bff;
  background: rgba(0, 123, 255, 0.1);
}

.tab-btn.active {
  color: #007bff;
  border-bottom-color: #007bff;
  background: white;
}

.tab-btn i {
  font-size: 1rem;
}

/* Tab Content */
.tab-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tab-content .chat-messages {
  flex: 1;
  overflow-y: auto;
}

.tab-content .chat-input {
  flex-shrink: 0;
}
</style>