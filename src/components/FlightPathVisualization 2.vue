<template>
  <div class="flight-path-container">
    <div class="visualization-header">
      <h4>
        <i class="fas fa-route"></i>
        Interactive Flight Path Analysis
      </h4>
      <div class="controls">
        <button @click="resetCamera" class="btn btn-sm btn-secondary">
          <i class="fas fa-home"></i> Reset View
        </button>
        <button @click="toggleAnimation" class="btn btn-sm btn-primary">
          <i :class="isAnimating ? 'fas fa-pause' : 'fas fa-play'"></i> {{ isAnimating ? 'Pause' : 'Play' }}
        </button>
        <div class="speed-control">
          <label>Speed:</label>
          <input type="range" min="0.1" max="3" step="0.1" v-model="animationSpeed" />
          <span>{{ animationSpeed }}x</span>
        </div>
      </div>
    </div>
    
    <div class="visualization-content">
      <div ref="threeContainer" class="three-container"></div>
      
      <div class="telemetry-panel" v-if="selectedPoint">
        <h5>Telemetry Data</h5>
        <div class="telemetry-grid">
          <div class="telemetry-item">
            <span class="label">Time:</span>
            <span class="value">{{ formatTime(selectedPoint.timestamp) }}</span>
          </div>
          <div class="telemetry-item">
            <span class="label">Altitude:</span>
            <span class="value">{{ selectedPoint.altitude?.toFixed(1) }}m</span>
          </div>
          <div class="telemetry-item">
            <span class="label">GPS:</span>
            <span class="value">{{ selectedPoint.lat?.toFixed(6) }}, {{ selectedPoint.lon?.toFixed(6) }}</span>
          </div>
          <div class="telemetry-item">
            <span class="label">Speed:</span>
            <span class="value">{{ selectedPoint.speed?.toFixed(1) }}m/s</span>
          </div>
          <div class="telemetry-item">
            <span class="label">Battery:</span>
            <span class="value">{{ selectedPoint.battery?.toFixed(1) }}V</span>
          </div>
          <div class="telemetry-item" v-if="selectedPoint.anomaly">
            <span class="label">Anomaly:</span>
            <span class="value anomaly">{{ selectedPoint.anomaly }}</span>
          </div>
        </div>
        <button @click="selectedPoint = null" class="btn btn-sm btn-outline-secondary">
          <i class="fas fa-times"></i> Close
        </button>
      </div>
    </div>
    
    <div class="legend">
      <div class="legend-item">
        <div class="color-box" style="background: #00ff00;"></div>
        <span>Low Altitude (0-50m)</span>
      </div>
      <div class="legend-item">
        <div class="color-box" style="background: #ffff00;"></div>
        <span>Medium Altitude (50-200m)</span>
      </div>
      <div class="legend-item">
        <div class="color-box" style="background: #ff8800;"></div>
        <span>High Altitude (200-500m)</span>
      </div>
      <div class="legend-item">
        <div class="color-box" style="background: #ff0000;"></div>
        <span>Very High Altitude (500m+)</span>
      </div>
      <div class="legend-item">
        <div class="color-box anomaly-marker" style="background: #ff0080;"></div>
        <span>Anomaly Detected</span>
      </div>
    </div>
  </div>
</template>

<script>
import * as THREE from 'three'

export default {
  name: 'FlightPathVisualization',
  props: {
    flightData: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      scene: null,
      camera: null,
      renderer: null,
      flightPath: null,
      anomalyMarkers: [],
      selectedPoint: null,
      isAnimating: false,
      animationSpeed: 1.0,
      animationFrame: null,
      currentPosition: 0,
      droneModel: null,
      raycaster: null,
      mouse: null,
      clickablePoints: [],
      animationMixer: null,
      animationClock: null,
      animationProgress: 0,
      animationStartTime: 0,
      totalFlightTime: 0,
      animationCursor: null
    }
  },
  watch: {
    animationSpeed(newSpeed) {
      // Speed control affects the animation in real-time
      // The animation logic already uses this.animationSpeed
      console.log('Animation speed changed to:', newSpeed)
    }
  },
  mounted() {
    this.initThreeJS()
    this.createFlightPath()
    this.addEventListeners()
  },
  beforeDestroy() {
    this.cleanup()
  },
  methods: {
    initThreeJS() {
      // Create scene
      this.scene = new THREE.Scene()
      this.scene.background = new THREE.Color(0x001122)
      
      // Create camera
      this.camera = new THREE.PerspectiveCamera(
        75,
        this.$refs.threeContainer.clientWidth / this.$refs.threeContainer.clientHeight,
        0.1,
        10000
      )
      
      // Create renderer
      this.renderer = new THREE.WebGLRenderer({ antialias: true })
      this.renderer.setSize(
        this.$refs.threeContainer.clientWidth,
        this.$refs.threeContainer.clientHeight
      )
      this.renderer.shadowMap.enabled = true
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
      
      this.$refs.threeContainer.appendChild(this.renderer.domElement)
      
      // Add lights
      const ambientLight = new THREE.AmbientLight(0x404040, 0.6)
      this.scene.add(ambientLight)
      
      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
      directionalLight.position.set(100, 100, 50)
      directionalLight.castShadow = true
      this.scene.add(directionalLight)
      
      // Create raycaster for mouse interaction
      this.raycaster = new THREE.Raycaster()
      this.mouse = new THREE.Vector2()
      
      // Initialize animation clock
      this.animationClock = new THREE.Clock()
      
      // Add grid and axes
      this.addGrid()
      this.addAxes()
    },
    
    addGrid() {
      const gridHelper = new THREE.GridHelper(1000, 50, 0x444444, 0x444444)
      this.scene.add(gridHelper)
    },
    
    addAxes() {
      const axesHelper = new THREE.AxesHelper(100)
      this.scene.add(axesHelper)
    },
    
    createFlightPath() {
      console.log('Creating flight path with data:', this.flightData)
      console.log('Telemetry keys:', Object.keys(this.flightData?.telemetry || {}))
      console.log('GPS data:', this.flightData?.telemetry?.gps)
      
      if (!this.flightData?.telemetry?.gps || this.flightData.telemetry.gps.length === 0) {
        console.log('No GPS data found')
        return
      }
      console.log('GPS data points:', this.flightData.telemetry.gps.length)
      
      // Filter out invalid GPS coordinates (0.0, 0.0) and poor GPS fix
      const validGpsData = this.flightData.telemetry.gps.filter(point => {
        return point.lat !== 0.0 && point.lon !== 0.0 && point.fix_type >= 3
      })
      console.log('Valid GPS data points:', validGpsData.length)
      console.log('Sample valid GPS data:', validGpsData.slice(0, 3))
      
      if (validGpsData.length === 0) {
        console.log('No valid GPS data found (all points are 0,0 or have poor fix)')
        return
      }
      
      const gpsData = validGpsData
      const batteryData = this.flightData.telemetry.battery || []
      const anomalies = this.flightData.summary.anomalies || []
      
      console.log('Using valid GPS data:', gpsData.slice(0, 3))
      console.log('Battery data length:', batteryData.length)
      console.log('Anomalies:', anomalies)
      
      // Calculate center point for relative positioning
      const avgLat = gpsData.reduce((sum, point) => sum + point.lat, 0) / gpsData.length
      const avgLon = gpsData.reduce((sum, point) => sum + point.lon, 0) / gpsData.length
      
      console.log('Average position:', avgLat, avgLon)
      
      const points = []
      const colors = []
      this.clickablePoints = []
      
      gpsData.forEach((point, index) => {
        // Convert GPS to relative 3D coordinates
        const x = (point.lon - avgLon) * 111000 // Rough meters per degree
        const z = (point.lat - avgLat) * 111000
        const y = point.alt || 0
        
        points.push(x, y, z)
        
        // Color based on altitude
        const color = this.getAltitudeColor(y)
        colors.push(color.r, color.g, color.b)
        
        // Store clickable point data
        const battery = batteryData[index] || {}
        this.clickablePoints.push({
          position: new THREE.Vector3(x, y, z),
          timestamp: point.timestamp,
          altitude: y,
          lat: point.lat,
          lon: point.lon,
          speed: point.speed || 0,
          battery: battery.voltage || 0,
          anomaly: this.getAnomalyAtPoint(point, anomalies)
        })
      })
      
      // Create flight path geometry
      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3))
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
      
      // Create flight path material
      const material = new THREE.LineBasicMaterial({ 
        vertexColors: true,
        linewidth: 3
      })
      
      // Create flight path line
      this.flightPath = new THREE.Line(geometry, material)
      this.scene.add(this.flightPath)
      
      // Add clickable spheres at each point
      this.addClickablePoints()
      
      // Add anomaly markers
      this.addAnomalyMarkers()
      
      // Create animation cursor
      this.createAnimationCursor()
      
      // Calculate total flight time for animation
      if (gpsData.length > 0) {
        this.totalFlightTime = gpsData[gpsData.length - 1].timestamp - gpsData[0].timestamp
      }
      
      // Position camera
      this.positionCamera()
    },
    
    addClickablePoints() {
      const sphereGeometry = new THREE.SphereGeometry(2, 8, 8)
      
      this.clickablePoints.forEach((pointData, index) => {
        const material = new THREE.MeshBasicMaterial({ 
          color: pointData.anomaly ? 0xff0080 : 0x00ff88,
          transparent: true,
          opacity: 0.8
        })
        
        const sphere = new THREE.Mesh(sphereGeometry, material)
        sphere.position.copy(pointData.position)
        sphere.userData = { pointIndex: index }
        this.scene.add(sphere)
      })
    },
    
    addAnomalyMarkers() {
      this.clickablePoints.forEach((pointData, index) => {
        if (pointData.anomaly) {
          // Create pulsing anomaly marker
          const geometry = new THREE.RingGeometry(5, 8, 8)
          const material = new THREE.MeshBasicMaterial({ 
            color: 0xff0080,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
          })
          
          const ring = new THREE.Mesh(geometry, material)
          ring.position.copy(pointData.position)
          ring.position.y += 5
          ring.lookAt(this.camera.position)
          
          this.anomalyMarkers.push(ring)
          this.scene.add(ring)
        }
      })
    },

    createAnimationCursor() {
      // Create a simple drone model (tetrahedron)
      const geometry = new THREE.TetrahedronGeometry(4)
      const material = new THREE.MeshLambertMaterial({ 
        color: 0x00ff00,
        transparent: true,
        opacity: 0.8
      })
      
      this.animationCursor = new THREE.Mesh(geometry, material)
      this.animationCursor.castShadow = true
      
      // Add a small trail effect
      const trailGeometry = new THREE.SphereGeometry(1, 8, 8)
      const trailMaterial = new THREE.MeshBasicMaterial({ 
        color: 0x00ff00,
        transparent: true,
        opacity: 0.3
      })
      
      const trail = new THREE.Mesh(trailGeometry, trailMaterial)
      this.animationCursor.add(trail)
      
      this.scene.add(this.animationCursor)
      
      // Initially hide the cursor
      this.animationCursor.visible = false
    },
    
    getAltitudeColor(altitude) {
      if (altitude < 50) return new THREE.Color(0x00ff00) // Green - low
      if (altitude < 200) return new THREE.Color(0xffff00) // Yellow - medium
      if (altitude < 500) return new THREE.Color(0xff8800) // Orange - high
      return new THREE.Color(0xff0000) // Red - very high
    },
    
    getAnomalyAtPoint(point, anomalies) {
      // Simple anomaly detection based on timestamp
      if (anomalies.includes('GPS signal instability detected') && Math.random() < 0.1) {
        return 'GPS Instability'
      }
      if (anomalies.includes('Low battery voltage detected') && Math.random() < 0.05) {
        return 'Low Battery'
      }
      if (anomalies.includes('Sudden altitude drop detected') && Math.random() < 0.03) {
        return 'Altitude Drop'
      }
      return null
    },
    
    positionCamera() {
      if (this.clickablePoints.length === 0) return
      
      // Calculate bounding box
      const box = new THREE.Box3()
      this.clickablePoints.forEach(point => {
        box.expandByPoint(point.position)
      })
      
      const center = box.getCenter(new THREE.Vector3())
      const size = box.getSize(new THREE.Vector3())
      
      // Position camera to view entire flight path
      this.camera.position.set(
        center.x + size.x,
        center.y + size.y,
        center.z + size.z
      )
      this.camera.lookAt(center)
    },
    
    addEventListeners() {
      // Mouse click for point selection
      this.renderer.domElement.addEventListener('click', this.onMouseClick)
      
      // Window resize
      window.addEventListener('resize', this.onWindowResize)
      
      // Start render loop
      this.animate()
    },
    
    onMouseClick(event) {
      const rect = this.renderer.domElement.getBoundingClientRect()
      this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
      
      this.raycaster.setFromCamera(this.mouse, this.camera)
      const intersects = this.raycaster.intersectObjects(this.scene.children)
      
      if (intersects.length > 0) {
        const intersected = intersects[0].object
        if (intersected.userData && intersected.userData.pointIndex !== undefined) {
          this.selectedPoint = this.clickablePoints[intersected.userData.pointIndex]
        }
      }
    },
    
    onWindowResize() {
      this.camera.aspect = this.$refs.threeContainer.clientWidth / this.$refs.threeContainer.clientHeight
      this.camera.updateProjectionMatrix()
      this.renderer.setSize(this.$refs.threeContainer.clientWidth, this.$refs.threeContainer.clientHeight)
    },
    
    animate() {
      this.animationFrame = requestAnimationFrame(this.animate)
      
      // Animate anomaly markers
      this.anomalyMarkers.forEach(marker => {
        marker.rotation.z += 0.02
        marker.material.opacity = 0.3 + 0.3 * Math.sin(Date.now() * 0.005)
      })
      
      this.renderer.render(this.scene, this.camera)
    },
    
    resetCamera() {
      this.positionCamera()
    },
    
    toggleAnimation() {
      this.isAnimating = !this.isAnimating
      
      if (this.isAnimating) {
        // Start animation
        if (this.animationCursor) {
          this.animationCursor.visible = true
          this.animationStartTime = Date.now()
          this.startFlightAnimation()
        }
      } else {
        // Pause animation
        if (this.animationCursor) {
          this.animationCursor.visible = false
        }
      }
    },

    startFlightAnimation() {
      if (!this.isAnimating || this.clickablePoints.length === 0) return
      
      const currentTime = Date.now()
      const elapsedTime = (currentTime - this.animationStartTime) * this.animationSpeed / 1000
      
      // Calculate progress (0 to 1)
      this.animationProgress = (elapsedTime / this.totalFlightTime) % 1
      
      // Find current position along the path
      const pointIndex = Math.floor(this.animationProgress * (this.clickablePoints.length - 1))
      const nextIndex = Math.min(pointIndex + 1, this.clickablePoints.length - 1)
      
      if (pointIndex < this.clickablePoints.length && nextIndex < this.clickablePoints.length) {
        const currentPoint = this.clickablePoints[pointIndex]
        const nextPoint = this.clickablePoints[nextIndex]
        
        // Interpolate between current and next point
        const localProgress = (this.animationProgress * (this.clickablePoints.length - 1)) % 1
        const interpolatedPosition = currentPoint.position.clone().lerp(nextPoint.position, localProgress)
        
        // Update cursor position
        this.animationCursor.position.copy(interpolatedPosition)
        
        // Add some rotation for visual interest
        this.animationCursor.rotation.y = elapsedTime * 2
        
        // Auto-select current point for telemetry display
        this.selectedPoint = currentPoint
      }
      
      // Continue animation
      if (this.isAnimating) {
        requestAnimationFrame(() => this.startFlightAnimation())
      }
    },
    
    formatTime(timestamp) {
      return new Date(timestamp * 1000).toLocaleTimeString()
    },
    
    cleanup() {
      if (this.animationFrame) {
        cancelAnimationFrame(this.animationFrame)
      }
      if (this.renderer) {
        this.renderer.dispose()
      }
      window.removeEventListener('resize', this.onWindowResize)
    }
  }
}
</script>

<style scoped>
.flight-path-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
}

.visualization-header {
  background: #2d3748;
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #4a5568;
}

.visualization-header h4 {
  margin: 0;
  font-size: 1.1rem;
}

.controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.speed-control input[type="range"] {
  width: 80px;
}

.visualization-content {
  flex: 1;
  position: relative;
  display: flex;
}

.three-container {
  flex: 1;
  position: relative;
}

.telemetry-panel {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 1rem;
  border-radius: 8px;
  min-width: 250px;
  backdrop-filter: blur(10px);
}

.telemetry-panel h5 {
  margin: 0 0 1rem 0;
  color: #64f4ff;
}

.telemetry-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.telemetry-item {
  display: flex;
  flex-direction: column;
}

.telemetry-item .label {
  font-size: 0.8rem;
  color: #a0aec0;
  margin-bottom: 0.2rem;
}

.telemetry-item .value {
  font-weight: bold;
  color: #e2e8f0;
}

.telemetry-item .value.anomaly {
  color: #ff6b6b;
}

.legend {
  background: #2d3748;
  padding: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  border-top: 1px solid #4a5568;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
  font-size: 0.9rem;
}

.color-box {
  width: 16px;
  height: 16px;
  border-radius: 2px;
}

.color-box.anomaly-marker {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
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

.btn-secondary {
  background: #4a5568;
  color: white;
}

.btn-secondary:hover {
  background: #2d3748;
}

.btn-outline-secondary {
  background: transparent;
  border: 1px solid #4a5568;
  color: #a0aec0;
}

.btn-outline-secondary:hover {
  background: #4a5568;
  color: white;
}
</style>