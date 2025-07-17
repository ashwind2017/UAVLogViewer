<template>
  <div class="analysis-dashboard">
    <div class="dashboard-header">
      <h4>
        <i class="fas fa-tachometer-alt"></i>
        Real-Time Flight Analysis Dashboard
      </h4>
      <div class="dashboard-controls">
        <button @click="refreshAnalysis" class="btn btn-sm btn-primary">
          <i class="fas fa-sync"></i> Refresh
        </button>
        <button @click="exportReport" class="btn btn-sm btn-success" :disabled="isExportingReport">
          <i v-if="!isExportingReport" class="fas fa-file-export"></i>
          <i v-else class="fas fa-spinner fa-spin"></i>
          {{ isExportingReport ? 'Generating PDF...' : 'Export Report' }}
        </button>
      </div>
    </div>
    
    <div class="dashboard-content">
      <!-- Flight Safety Score -->
      <div class="metric-card safety-score">
        <div class="metric-header">
          <h5>
            <i class="fas fa-shield-alt"></i>
            Flight Safety Score
          </h5>
          <div class="score-badge" :class="safetyScoreClass">
            {{ safetyScore }}/100
          </div>
        </div>
        <div class="score-bar">
          <div class="score-fill" :style="{ width: safetyScore + '%' }" :class="safetyScoreClass"></div>
        </div>
        <div class="score-breakdown">
          <div class="breakdown-item">
            <span>GPS Stability:</span>
            <span :class="getScoreColor(gpsScore)">{{ gpsScore }}/25</span>
          </div>
          <div class="breakdown-item">
            <span>Battery Health:</span>
            <span :class="getScoreColor(batteryScore)">{{ batteryScore }}/25</span>
          </div>
          <div class="breakdown-item">
            <span>Flight Stability:</span>
            <span :class="getScoreColor(stabilityScore)">{{ stabilityScore }}/25</span>
          </div>
          <div class="breakdown-item">
            <span>System Health:</span>
            <span :class="getScoreColor(systemScore)">{{ systemScore }}/25</span>
          </div>
        </div>
      </div>
      
      <!-- Anomaly Alerts -->
      <div class="metric-card anomaly-alerts">
        <div class="metric-header">
          <h5>
            <i class="fas fa-exclamation-triangle"></i>
            Anomaly Alerts
          </h5>
          <div class="alert-count" :class="alertSeverityClass">
            {{ anomalies.length }}
          </div>
        </div>
        <div class="alerts-list">
          <div v-for="anomaly in anomalies" :key="anomaly.id" class="alert-item" :class="anomaly.severity">
            <div class="alert-icon">
              <i :class="getAnomalyIcon(anomaly.type)"></i>
            </div>
            <div class="alert-content">
              <div class="alert-title">{{ anomaly.title }}</div>
              <div class="alert-details">{{ anomaly.description }}</div>
              <div class="alert-timestamp">{{ formatTime(anomaly.timestamp) }}</div>
            </div>
            <div class="alert-severity">{{ anomaly.severity.toUpperCase() }}</div>
          </div>
        </div>
      </div>
      
      <!-- Flight Metrics -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-header">
            <h6><i class="fas fa-clock"></i> Flight Duration</h6>
          </div>
          <div class="metric-value">{{ formatDuration(flightDuration) }}</div>
          <div class="metric-trend" :class="getDurationTrend()">
            <i :class="getDurationTrendIcon()"></i>
            {{ getDurationTrendText() }}
          </div>
        </div>
        
        <div class="metric-card">
          <div class="metric-header">
            <h6><i class="fas fa-arrow-up"></i> Max Altitude</h6>
          </div>
          <div class="metric-value">{{ maxAltitude.toFixed(1) }}m</div>
          <div class="metric-trend" :class="getAltitudeTrend()">
            <i :class="getAltitudeTrendIcon()"></i>
            {{ getAltitudeTrendText() }}
          </div>
        </div>
        
        <div class="metric-card">
          <div class="metric-header">
            <h6><i class="fas fa-tachometer-alt"></i> Max Speed</h6>
          </div>
          <div class="metric-value">{{ maxSpeed.toFixed(1) }}m/s</div>
          <div class="metric-trend" :class="getSpeedTrend()">
            <i :class="getSpeedTrendIcon()"></i>
            {{ getSpeedTrendText() }}
          </div>
        </div>
        
        <div class="metric-card">
          <div class="metric-header">
            <h6><i class="fas fa-battery-half"></i> Battery Usage</h6>
          </div>
          <div class="metric-value">{{ batteryUsage.toFixed(1) }}%</div>
          <div class="metric-trend" :class="getBatteryTrend()">
            <i :class="getBatteryTrendIcon()"></i>
            {{ getBatteryTrendText() }}
          </div>
        </div>
      </div>
      
      <!-- Real-time Recommendations -->
      <div class="metric-card recommendations">
        <div class="metric-header">
          <h5>
            <i class="fas fa-lightbulb"></i>
            AI Recommendations
          </h5>
        </div>
        <div class="recommendations-list">
          <div v-for="recommendation in recommendations" :key="recommendation.id" class="recommendation-item">
            <div class="recommendation-icon">
              <i :class="getRecommendationIcon(recommendation.type)"></i>
            </div>
            <div class="recommendation-content">
              <div class="recommendation-title">{{ recommendation.title }}</div>
              <div class="recommendation-description">{{ recommendation.description }}</div>
            </div>
            <div class="recommendation-priority" :class="recommendation.priority">
              {{ recommendation.priority.toUpperCase() }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AnalysisDashboard',
  props: {
    flightData: {
      type: Object,
      required: true
    },
    historicalData: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      anomalies: [],
      recommendations: [],
      safetyScore: 0,
      gpsScore: 0,
      batteryScore: 0,
      stabilityScore: 0,
      systemScore: 0,
      flightDuration: 0,
      maxAltitude: 0,
      maxSpeed: 0,
      batteryUsage: 0,
      isExportingReport: false
    }
  },
  computed: {
    safetyScoreClass() {
      if (this.safetyScore >= 80) return 'excellent'
      if (this.safetyScore >= 60) return 'good'
      if (this.safetyScore >= 40) return 'warning'
      return 'critical'
    },
    alertSeverityClass() {
      const criticalCount = this.anomalies.filter(a => a.severity === 'critical').length
      const warningCount = this.anomalies.filter(a => a.severity === 'warning').length
      
      if (criticalCount > 0) return 'critical'
      if (warningCount > 0) return 'warning'
      return 'info'
    }
  },
  watch: {
    flightData: {
      handler: 'analyzeFlightData',
      immediate: true,
      deep: true
    }
  },
  methods: {
    analyzeFlightData() {
      if (!this.flightData?.summary) return
      
      // Extract basic metrics
      this.flightDuration = this.flightData.summary.duration || 0
      this.maxAltitude = this.flightData.summary.max_altitude || 0
      this.maxSpeed = this.flightData.summary.max_speed || 0
      this.batteryUsage = this.flightData.summary.battery_usage || 0
      
      // Calculate safety scores
      this.calculateSafetyScores()
      
      // Generate anomalies
      this.generateAnomalies()
      
      // Generate recommendations
      this.generateRecommendations()
    },
    
    calculateSafetyScores() {
      const anomalies = this.flightData.summary.anomalies || []
      
      // GPS Score (25 points)
      this.gpsScore = 25
      if (anomalies.some(a => a.includes('GPS'))) {
        this.gpsScore -= 10
      }
      if (this.flightData.telemetry?.gps) {
        const gpsData = this.flightData.telemetry.gps
        const poorFixCount = gpsData.filter(g => g.fix_type < 3).length
        const poorFixRatio = poorFixCount / gpsData.length
        this.gpsScore -= Math.floor(poorFixRatio * 15)
      }
      
      // Battery Score (25 points)
      this.batteryScore = 25
      if (anomalies.some(a => a.includes('battery'))) {
        this.batteryScore -= 10
      }
      if (this.batteryUsage > 80) {
        this.batteryScore -= 10
      }
      
      // Stability Score (25 points)
      this.stabilityScore = 25
      if (anomalies.some(a => a.includes('altitude'))) {
        this.stabilityScore -= 8
      }
      if (anomalies.some(a => a.includes('vibration'))) {
        this.stabilityScore -= 7
      }
      
      // System Score (25 points)
      this.systemScore = 25
      if (anomalies.length > 3) {
        this.systemScore -= 10
      }
      if (anomalies.some(a => a.includes('critical'))) {
        this.systemScore -= 15
      }
      
      // Calculate total safety score
      this.safetyScore = Math.max(0, this.gpsScore + this.batteryScore + this.stabilityScore + this.systemScore)
    },
    
    generateAnomalies() {
      this.anomalies = []
      const flightAnomalies = this.flightData.summary.anomalies || []
      
      flightAnomalies.forEach((anomaly, index) => {
        let severity = 'info'
        let type = 'general'
        
        if (anomaly.includes('GPS')) {
          severity = 'warning'
          type = 'gps'
        } else if (anomaly.includes('battery')) {
          severity = 'critical'
          type = 'battery'
        } else if (anomaly.includes('altitude')) {
          severity = 'warning'
          type = 'altitude'
        } else if (anomaly.includes('vibration')) {
          severity = 'info'
          type = 'vibration'
        }
        
        this.anomalies.push({
          id: index,
          title: this.getAnomalyTitle(anomaly),
          description: anomaly,
          severity,
          type,
          timestamp: Date.now() - (index * 10000) // Mock timestamps
        })
      })
    },
    
    generateRecommendations() {
      this.recommendations = []
      
      if (this.safetyScore < 60) {
        this.recommendations.push({
          id: 1,
          title: 'Flight Safety Review Required',
          description: 'Multiple anomalies detected. Recommend thorough pre-flight inspection.',
          type: 'safety',
          priority: 'high'
        })
      }
      
      if (this.batteryUsage > 80) {
        this.recommendations.push({
          id: 2,
          title: 'Battery Optimization',
          description: 'Consider shorter flight plans or battery replacement.',
          type: 'battery',
          priority: 'medium'
        })
      }
      
      if (this.gpsScore < 20) {
        this.recommendations.push({
          id: 3,
          title: 'GPS Signal Improvement',
          description: 'Check GPS antenna placement and avoid GPS-denied environments.',
          type: 'gps',
          priority: 'high'
        })
      }
      
      // Compare with historical data
      if (this.historicalData.length > 0) {
        const avgHistoricalScore = this.historicalData.reduce((sum, flight) => sum + (flight.safetyScore || 0), 0) / this.historicalData.length
        
        if (this.safetyScore < avgHistoricalScore * 0.8) {
          this.recommendations.push({
            id: 4,
            title: 'Performance Degradation',
            description: 'Flight performance below historical average. Consider maintenance.',
            type: 'maintenance',
            priority: 'medium'
          })
        }
      }
    },
    
    getAnomalyTitle(anomaly) {
      if (anomaly.includes('GPS')) return 'GPS Signal Issues'
      if (anomaly.includes('battery')) return 'Battery Problems'
      if (anomaly.includes('altitude')) return 'Flight Stability Issues'
      if (anomaly.includes('vibration')) return 'Vibration Detected'
      return 'System Alert'
    },
    
    getAnomalyIcon(type) {
      const icons = {
        gps: 'fas fa-satellite-dish',
        battery: 'fas fa-battery-empty',
        altitude: 'fas fa-arrow-down',
        vibration: 'fas fa-wave-square',
        general: 'fas fa-exclamation-circle'
      }
      return icons[type] || icons.general
    },
    
    getRecommendationIcon(type) {
      const icons = {
        safety: 'fas fa-shield-alt',
        battery: 'fas fa-battery-half',
        gps: 'fas fa-satellite-dish',
        maintenance: 'fas fa-wrench'
      }
      return icons[type] || 'fas fa-lightbulb'
    },
    
    getScoreColor(score) {
      if (score >= 20) return 'excellent'
      if (score >= 15) return 'good'
      if (score >= 10) return 'warning'
      return 'critical'
    },
    
    getDurationTrend() {
      if (this.historicalData.length === 0) return 'neutral'
      const avgDuration = this.historicalData.reduce((sum, f) => sum + (f.duration || 0), 0) / this.historicalData.length
      return this.flightDuration > avgDuration ? 'positive' : 'negative'
    },
    
    getDurationTrendIcon() {
      const trend = this.getDurationTrend()
      return trend === 'positive' ? 'fas fa-arrow-up' : trend === 'negative' ? 'fas fa-arrow-down' : 'fas fa-minus'
    },
    
    getDurationTrendText() {
      const trend = this.getDurationTrend()
      return trend === 'positive' ? 'Above average' : trend === 'negative' ? 'Below average' : 'No trend'
    },
    
    getAltitudeTrend() {
      if (this.historicalData.length === 0) return 'neutral'
      const avgAltitude = this.historicalData.reduce((sum, f) => sum + (f.max_altitude || 0), 0) / this.historicalData.length
      return this.maxAltitude > avgAltitude ? 'positive' : 'negative'
    },
    
    getAltitudeTrendIcon() {
      const trend = this.getAltitudeTrend()
      return trend === 'positive' ? 'fas fa-arrow-up' : trend === 'negative' ? 'fas fa-arrow-down' : 'fas fa-minus'
    },
    
    getAltitudeTrendText() {
      const trend = this.getAltitudeTrend()
      return trend === 'positive' ? 'Higher than avg' : trend === 'negative' ? 'Lower than avg' : 'No trend'
    },
    
    getSpeedTrend() {
      if (this.historicalData.length === 0) return 'neutral'
      const avgSpeed = this.historicalData.reduce((sum, f) => sum + (f.max_speed || 0), 0) / this.historicalData.length
      return this.maxSpeed > avgSpeed ? 'positive' : 'negative'
    },
    
    getSpeedTrendIcon() {
      const trend = this.getSpeedTrend()
      return trend === 'positive' ? 'fas fa-arrow-up' : trend === 'negative' ? 'fas fa-arrow-down' : 'fas fa-minus'
    },
    
    getSpeedTrendText() {
      const trend = this.getSpeedTrend()
      return trend === 'positive' ? 'Faster than avg' : trend === 'negative' ? 'Slower than avg' : 'No trend'
    },
    
    getBatteryTrend() {
      if (this.historicalData.length === 0) return 'neutral'
      const avgBattery = this.historicalData.reduce((sum, f) => sum + (f.battery_usage || 0), 0) / this.historicalData.length
      return this.batteryUsage < avgBattery ? 'positive' : 'negative'
    },
    
    getBatteryTrendIcon() {
      const trend = this.getBatteryTrend()
      return trend === 'positive' ? 'fas fa-arrow-up' : trend === 'negative' ? 'fas fa-arrow-down' : 'fas fa-minus'
    },
    
    getBatteryTrendText() {
      const trend = this.getBatteryTrend()
      return trend === 'positive' ? 'More efficient' : trend === 'negative' ? 'Less efficient' : 'No trend'
    },
    
    formatTime(timestamp) {
      return new Date(timestamp).toLocaleTimeString()
    },
    
    formatDuration(seconds) {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = Math.floor(seconds % 60)
      return `${minutes}m ${remainingSeconds}s`
    },
    
    refreshAnalysis() {
      this.analyzeFlightData()
    },
    
    async exportReport() {
      try {
        // Show loading indicator
        this.isExportingReport = true
        
        // Import the report service
        const reportService = await import('../services/reportService')
        
        // Prepare analysis data
        const analysisData = {
          safetyScore: this.safetyScore,
          gpsScore: this.gpsScore,
          batteryScore: this.batteryScore,
          stabilityScore: this.stabilityScore,
          systemScore: this.systemScore,
          anomalies: this.anomalies,
          recommendations: this.recommendations
        }
        
        // Generate PDF report
        const doc = await reportService.default.generateFlightReport(
          this.flightData,
          analysisData,
          null // TODO: Add visualization element if needed
        )
        
        // Download the PDF
        const filename = `flight-analysis-report-${new Date().toISOString().split('T')[0]}.pdf`
        await reportService.default.downloadReport(filename)
        
        // Show success message
        this.$emit('report-generated', { success: true, filename })
        
      } catch (error) {
        console.error('Error generating report:', error)
        this.$emit('report-generated', { success: false, error: error.message })
      } finally {
        this.isExportingReport = false
      }
    }
  }
}
</script>

<style scoped>
.analysis-dashboard {
  background: #1a1a1a;
  color: white;
  border-radius: 8px;
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dashboard-header {
  background: #2d3748;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #4a5568;
}

.dashboard-header h4 {
  margin: 0;
  font-size: 1.1rem;
}

.dashboard-controls {
  display: flex;
  gap: 0.5rem;
}

.dashboard-content {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
}

.metric-card {
  background: #2d3748;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid #4a5568;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.metric-header h5, .metric-header h6 {
  margin: 0;
  color: #e2e8f0;
}

.safety-score {
  background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
}

.score-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: bold;
  font-size: 1.1rem;
}

.score-badge.excellent { background: #48bb78; }
.score-badge.good { background: #ed8936; }
.score-badge.warning { background: #ecc94b; }
.score-badge.critical { background: #f56565; }

.score-bar {
  height: 8px;
  background: #4a5568;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.score-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.score-fill.excellent { background: #48bb78; }
.score-fill.good { background: #ed8936; }
.score-fill.warning { background: #ecc94b; }
.score-fill.critical { background: #f56565; }

.score-breakdown {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.breakdown-item span.excellent { color: #48bb78; }
.breakdown-item span.good { color: #ed8936; }
.breakdown-item span.warning { color: #ecc94b; }
.breakdown-item span.critical { color: #f56565; }

.alert-count {
  padding: 0.5rem 1rem;
  border-radius: 15px;
  font-weight: bold;
  font-size: 0.9rem;
}

.alert-count.critical { background: #f56565; }
.alert-count.warning { background: #ecc94b; color: #000; }
.alert-count.info { background: #4299e1; }

.alerts-list {
  max-height: 200px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border-radius: 6px;
  border-left: 4px solid;
}

.alert-item.critical {
  background: rgba(245, 101, 101, 0.1);
  border-left-color: #f56565;
}

.alert-item.warning {
  background: rgba(236, 201, 75, 0.1);
  border-left-color: #ecc94b;
}

.alert-item.info {
  background: rgba(66, 153, 225, 0.1);
  border-left-color: #4299e1;
}

.alert-icon {
  margin-right: 1rem;
  font-size: 1.2rem;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-weight: bold;
  margin-bottom: 0.25rem;
}

.alert-details {
  font-size: 0.9rem;
  color: #a0aec0;
  margin-bottom: 0.25rem;
}

.alert-timestamp {
  font-size: 0.8rem;
  color: #718096;
}

.alert-severity {
  font-size: 0.8rem;
  font-weight: bold;
  color: #e2e8f0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.metric-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #64f4ff;
  margin-bottom: 0.5rem;
}

.metric-trend {
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.metric-trend.positive { color: #48bb78; }
.metric-trend.negative { color: #f56565; }
.metric-trend.neutral { color: #a0aec0; }

.recommendations-list {
  max-height: 300px;
  overflow-y: auto;
}

.recommendation-item {
  display: flex;
  align-items: center;
  padding: 1rem;
  margin-bottom: 0.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  border-left: 4px solid #4299e1;
}

.recommendation-icon {
  margin-right: 1rem;
  font-size: 1.2rem;
  color: #4299e1;
}

.recommendation-content {
  flex: 1;
}

.recommendation-title {
  font-weight: bold;
  margin-bottom: 0.25rem;
}

.recommendation-description {
  font-size: 0.9rem;
  color: #a0aec0;
}

.recommendation-priority {
  font-size: 0.8rem;
  font-weight: bold;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.recommendation-priority.high {
  background: #f56565;
  color: white;
}

.recommendation-priority.medium {
  background: #ecc94b;
  color: black;
}

.recommendation-priority.low {
  background: #4299e1;
  color: white;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.btn-primary {
  background: #3182ce;
  color: white;
}

.btn-primary:hover {
  background: #2c5282;
}

.btn-success {
  background: #38a169;
  color: white;
}

.btn-success:hover {
  background: #2f855a;
}
</style>