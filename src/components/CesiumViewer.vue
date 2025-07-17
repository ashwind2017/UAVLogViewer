<template>
    <div id="cesiumContainer" style="width: 100%; height: 100%;"></div>
</template>

<script>
import {
    Viewer,
    Cartesian3,
    Color,
    PolylineCollection,
    PinBuilder,
    VerticalOrigin,
    HorizontalOrigin,
    HeightReference,
    LabelStyle,
    JulianDate,
    ClockRange,
    ClockStep,
    Math as CesiumMath,
    UrlTemplateImageryProvider,
    Rectangle,
    WebMercatorProjection,
    Cartographic,
    defined,
    Entity,
    CallbackProperty,
    SampledPositionProperty,
    TimeIntervalCollection,
    TimeInterval,
    Transforms,
    HeadingPitchRoll,
    Matrix4,
    Quaternion,
    Matrix3
} from 'cesium'

import { store } from '@/components/Globals.js'

export default {
    name: 'CesiumViewer',
    data() {
        return {
            viewer: null,
            state: store,
            polylines: null,
            trajectoryEntity: null,
            aircraftEntity: null,
            currentTime: 0,
            isPlaying: false,
            animationSpeed: 1,
            followAircraft: true
        }
    },
    mounted() {
        console.log('CesiumViewer: Component mounted')
        // Use nextTick to ensure DOM is fully rendered
        this.$nextTick(() => {
            this.initCesium()
            this.setupEventListeners()
        })
    },
    beforeDestroy() {
        this.cleanup()
    },
    methods: {
        initCesium() {
            console.log('CesiumViewer: Starting initialization...')
            const container = document.getElementById('cesiumContainer')
            console.log('CesiumViewer: Container found:', container)
            
            if (!container) {
                console.error('CesiumViewer: cesiumContainer element not found!')
                return
            }
            
            try {
                console.log('CesiumViewer: Creating Cesium viewer with OpenStreetMap...')
                // Simple working configuration with OpenStreetMap
                this.viewer = new Viewer('cesiumContainer', {
                    imageryProvider: new UrlTemplateImageryProvider({
                        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        credit: 'Map data © OpenStreetMap contributors'
                    }),
                    homeButton: false,
                    timeline: true,
                    animation: true,
                    selectionIndicator: false,
                    baseLayerPicker: false,
                    geocoder: false,
                    infoBox: false,
                    navigationHelpButton: false,
                    sceneModePicker: false,
                    vrButton: false,
                    fullscreenButton: false
                })

                console.log('CesiumViewer: Viewer created successfully:', this.viewer)

                // Set initial camera position
                console.log('CesiumViewer: Setting camera position...')
                this.viewer.camera.setView({
                    destination: Cartesian3.fromDegrees(-117.16, 32.71, 15000.0)
                })

                // Initialize polylines collection
                console.log('CesiumViewer: Initializing polylines...')
                this.polylines = new PolylineCollection()
                this.viewer.scene.primitives.add(this.polylines)

                // Add original viewer configuration
                console.log('CesiumViewer: Applying original viewer settings...')
                this.viewer.scene.debugShowFramesPerSecond = true
                this.viewer.scene.postProcessStages.ambientOcclusion.enabled = false
                this.viewer.scene.postProcessStages.bloom.enabled = false
                this.viewer.scene.globe.enableLighting = true
                this.viewer.scene.globe.depthTestAgainstTerrain = true
                this.viewer.shadowMap.maxmimumDistance = 10000.0
                this.viewer.shadowMap.softShadows = true
                this.viewer.shadowMap.size = 4096

                // Watch for trajectory data changes
                console.log('CesiumViewer: Setting up watchers...')
                this.$watch('state.currentTrajectory', this.updateTrajectory, { immediate: true })
                this.$watch('state.flightModeChanges', this.updateFlightModes, { immediate: true })

                console.log('CesiumViewer initialized successfully')
            } catch (error) {
                console.error('Failed to initialize CesiumViewer:', error)
            }
        },

        setupEventListeners() {
            // Listen for time changes from the timeline
            this.viewer.clock.onTick.addEventListener(this.onClockTick)
            
            // Listen for external time changes
            this.$eventHub.$on('cesium-time-changed', this.onTimeChanged)
            this.$eventHub.$on('cesium-follow-aircraft', this.onFollowAircraft)
            this.$eventHub.$on('cesium-animation-speed', this.onAnimationSpeedChanged)
        },

        updateTrajectory() {
            if (!this.viewer || !this.state.currentTrajectory || this.state.currentTrajectory.length === 0) {
                return
            }

            try {
                // Clear existing trajectory
                this.viewer.entities.removeAll()
                this.polylines.removeAll()

                const trajectory = this.state.currentTrajectory
                const timeTrajectory = this.state.timeTrajectory

                // Create trajectory path
                const positions = []
                const times = []
                
                for (let i = 0; i < trajectory.length; i++) {
                    const point = trajectory[i]
                    if (point.lat !== undefined && point.lon !== undefined && point.alt !== undefined) {
                        positions.push(Cartesian3.fromDegrees(point.lon, point.lat, point.alt))
                        if (timeTrajectory && timeTrajectory[i]) {
                            times.push(JulianDate.fromDate(new Date(timeTrajectory[i])))
                        }
                    }
                }

                if (positions.length === 0) {
                    console.warn('No valid trajectory positions found')
                    return
                }

                // Create polyline for trajectory path
                const polyline = this.polylines.add({
                    positions: positions,
                    width: 3,
                    material: Color.CYAN,
                    clampToGround: false
                })

                // Create aircraft entity with time-based position
                if (times.length > 0) {
                    const positionProperty = new SampledPositionProperty()
                    for (let i = 0; i < positions.length && i < times.length; i++) {
                        positionProperty.addSample(times[i], positions[i])
                    }

                    this.aircraftEntity = this.viewer.entities.add({
                        name: 'Aircraft',
                        position: positionProperty,
                        point: {
                            pixelSize: 10,
                            color: Color.YELLOW,
                            outlineColor: Color.BLACK,
                            outlineWidth: 2,
                            heightReference: HeightReference.RELATIVE_TO_GROUND
                        },
                        label: {
                            text: 'UAV',
                            font: '14pt sans-serif',
                            pixelOffset: new Cartesian3(0, -40, 0),
                            fillColor: Color.WHITE,
                            outlineColor: Color.BLACK,
                            outlineWidth: 2,
                            style: LabelStyle.FILL_AND_OUTLINE,
                            verticalOrigin: VerticalOrigin.BOTTOM,
                            horizontalOrigin: HorizontalOrigin.CENTER
                        }
                    })

                    // Set up timeline
                    if (times.length > 1) {
                        this.viewer.clock.startTime = times[0]
                        this.viewer.clock.stopTime = times[times.length - 1]
                        this.viewer.clock.currentTime = times[0]
                        this.viewer.clock.clockRange = ClockRange.LOOP_STOP
                        this.viewer.clock.clockStep = ClockStep.SYSTEM_CLOCK_MULTIPLIER
                        this.viewer.clock.multiplier = 1
                        this.viewer.timeline.zoomTo(times[0], times[times.length - 1])
                    }
                }

                // Center camera on trajectory
                this.viewer.flyTo(this.viewer.entities)

                console.log(`Trajectory updated with ${positions.length} points`)
            } catch (error) {
                console.error('Error updating trajectory:', error)
            }
        },

        updateFlightModes() {
            if (!this.viewer || !this.state.flightModeChanges || this.state.flightModeChanges.length === 0) {
                return
            }

            try {
                // Add flight mode change markers
                for (const modeChange of this.state.flightModeChanges) {
                    const [timestamp, mode] = modeChange
                    
                    // Find corresponding position in trajectory
                    const trajectoryIndex = this.findTrajectoryIndexByTime(timestamp)
                    if (trajectoryIndex >= 0 && trajectoryIndex < this.state.currentTrajectory.length) {
                        const point = this.state.currentTrajectory[trajectoryIndex]
                        
                        if (point.lat !== undefined && point.lon !== undefined && point.alt !== undefined) {
                            this.viewer.entities.add({
                                name: `Mode: ${mode}`,
                                position: Cartesian3.fromDegrees(point.lon, point.lat, point.alt + 10),
                                point: {
                                    pixelSize: 8,
                                    color: this.getModeColor(mode),
                                    outlineColor: Color.WHITE,
                                    outlineWidth: 1,
                                    heightReference: HeightReference.RELATIVE_TO_GROUND
                                },
                                label: {
                                    text: mode,
                                    font: '12pt sans-serif',
                                    pixelOffset: new Cartesian3(0, -30, 0),
                                    fillColor: Color.WHITE,
                                    outlineColor: Color.BLACK,
                                    outlineWidth: 1,
                                    style: LabelStyle.FILL_AND_OUTLINE,
                                    verticalOrigin: VerticalOrigin.BOTTOM,
                                    horizontalOrigin: HorizontalOrigin.CENTER,
                                    scale: 0.8
                                }
                            })
                        }
                    }
                }
            } catch (error) {
                console.error('Error updating flight modes:', error)
            }
        },

        findTrajectoryIndexByTime(timestamp) {
            if (!this.state.timeTrajectory) return -1
            
            for (let i = 0; i < this.state.timeTrajectory.length; i++) {
                if (this.state.timeTrajectory[i] >= timestamp) {
                    return i
                }
            }
            return -1
        },

        getModeColor(mode) {
            const modeColors = {
                'STABILIZE': Color.GREEN,
                'LOITER': Color.BLUE,
                'RTL': Color.RED,
                'AUTO': Color.PURPLE,
                'GUIDED': Color.ORANGE,
                'LAND': Color.BROWN,
                'CIRCLE': Color.PINK,
                'POSHOLD': Color.CYAN,
                'BRAKE': Color.DARKRED,
                'THROW': Color.MAGENTA
            }
            return modeColors[mode] || Color.YELLOW
        },

        onClockTick(clock) {
            if (this.aircraftEntity && this.followAircraft) {
                const position = this.aircraftEntity.position.getValue(clock.currentTime)
                if (defined(position)) {
                    // Follow aircraft with camera
                    this.viewer.camera.lookAt(position, new Cartesian3(0, -100, 50))
                }
            }

            // Emit time change event
            this.$eventHub.$emit('cesium-time-changed', JulianDate.toDate(clock.currentTime))
        },

        onTimeChanged(time) {
            if (this.viewer && this.viewer.clock) {
                this.viewer.clock.currentTime = JulianDate.fromDate(new Date(time))
            }
        },

        onFollowAircraft(follow) {
            this.followAircraft = follow
        },

        onAnimationSpeedChanged(speed) {
            if (this.viewer && this.viewer.clock) {
                this.viewer.clock.multiplier = speed
            }
        },

        cleanup() {
            if (this.viewer) {
                this.viewer.clock.onTick.removeEventListener(this.onClockTick)
                this.viewer.destroy()
                this.viewer = null
            }
            
            // Remove event listeners
            this.$eventHub.$off('cesium-time-changed', this.onTimeChanged)
            this.$eventHub.$off('cesium-follow-aircraft', this.onFollowAircraft)
            this.$eventHub.$off('cesium-animation-speed', this.onAnimationSpeedChanged)
        },

        // Public methods for external control
        flyTo(entity) {
            if (this.viewer && entity) {
                this.viewer.flyTo(entity)
            }
        },

        zoomToTrajectory() {
            if (this.viewer && this.viewer.entities.values.length > 0) {
                this.viewer.flyTo(this.viewer.entities)
            }
        },

        setAnimationSpeed(speed) {
            this.onAnimationSpeedChanged(speed)
        },

        toggleFollowAircraft() {
            this.followAircraft = !this.followAircraft
        }
    },

    watch: {
        'state.currentTrajectory': {
            handler: 'updateTrajectory',
            immediate: true
        },
        'state.flightModeChanges': {
            handler: 'updateFlightModes',
            immediate: true
        }
    }
}
</script>

<style scoped>
#cesiumContainer {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
}
</style>