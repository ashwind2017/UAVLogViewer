import pymavlink.mavutil as mavutil
import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Any
# import numpy as np

class MAVLinkParser:
    def __init__(self):
        self.flights = {}
        self.upload_dir = "uploads"

    def parse_bin_file(self, file_path: str) -> Dict[str, Any]:
        """Parse MAVLink .bin file and extract flight data"""
        try:
            # Create connection to log file
            mlog = mavutil.mavlink_connection(file_path)

            flight_id = str(uuid.uuid4())
            flight_data = {
                "flight_id": flight_id,
                "file_path": file_path,
                "messages": [],
                "summary": {},
                "telemetry": {
                    "gps": [],
                    "attitude": [],
                    "battery": [],
                    "vibration": [],
                    "position": [],
                    "system_status": [],
                    "barometer": [],
                    "mode": []
                },
                "message_types": {},
                "total_messages": 0
            }

            # Parse messages
            message_count = 0
            message_types = {}
            
            while True:
                msg = mlog.recv_match(blocking=False)
                if msg is None:
                    break

                message_count += 1
                msg_type = msg.get_type()
                message_types[msg_type] = message_types.get(msg_type, 0) + 1

                # Extract key telemetry data with better error handling
                try:
                    # Handle ArduPilot log format messages
                    if msg_type == 'GPS':
                        flight_data["telemetry"]["gps"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "lat": getattr(msg, 'Lat', 0),
                            "lon": getattr(msg, 'Lng', 0),
                            "alt": getattr(msg, 'Alt', 0),
                            "fix_type": getattr(msg, 'Status', 0),
                            "hdop": getattr(msg, 'HDop', 0),
                            "speed": getattr(msg, 'Spd', 0)
                        })
                    elif msg_type == 'ATT':
                        flight_data["telemetry"]["attitude"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "roll": getattr(msg, 'Roll', 0),
                            "pitch": getattr(msg, 'Pitch', 0),
                            "yaw": getattr(msg, 'Yaw', 0)
                        })
                    elif msg_type == 'BAT':
                        flight_data["telemetry"]["battery"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "voltage": getattr(msg, 'Volt', 0),
                            "current": getattr(msg, 'Curr', 0),
                            "remaining": getattr(msg, 'CurrTot', 0)
                        })
                    elif msg_type == 'VIBE':
                        flight_data["telemetry"]["vibration"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "vibe_x": getattr(msg, 'VibeX', 0),
                            "vibe_y": getattr(msg, 'VibeY', 0),
                            "vibe_z": getattr(msg, 'VibeZ', 0)
                        })
                    elif msg_type == 'BARO':
                        flight_data["telemetry"]["barometer"] = flight_data["telemetry"].get("barometer", [])
                        flight_data["telemetry"]["barometer"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "altitude": getattr(msg, 'Alt', 0),
                            "pressure": getattr(msg, 'Press', 0),
                            "temperature": getattr(msg, 'Temp', 0)
                        })
                    elif msg_type == 'MODE':
                        flight_data["telemetry"]["mode"] = flight_data["telemetry"].get("mode", [])
                        flight_data["telemetry"]["mode"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "mode": getattr(msg, 'Mode', 0),
                            "mode_num": getattr(msg, 'ModeNum', 0)
                        })
                    # Handle standard MAVLink messages as fallback
                    elif msg_type == 'GPS_RAW_INT':
                        flight_data["telemetry"]["gps"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "lat": msg.lat / 1e7,
                            "lon": msg.lon / 1e7,
                            "alt": msg.alt / 1000,
                            "fix_type": msg.fix_type
                        })
                    elif msg_type == 'GLOBAL_POSITION_INT':
                        flight_data["telemetry"]["position"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "lat": msg.lat / 1e7,
                            "lon": msg.lon / 1e7,
                            "alt": msg.alt / 1000,
                            "relative_alt": msg.relative_alt / 1000,
                            "vx": msg.vx / 100.0,
                            "vy": msg.vy / 100.0,
                            "vz": msg.vz / 100.0
                        })
                    elif msg_type == 'ATTITUDE':
                        flight_data["telemetry"]["attitude"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "roll": msg.roll,
                            "pitch": msg.pitch,
                            "yaw": msg.yaw
                        })
                    elif msg_type == 'BATTERY_STATUS':
                        flight_data["telemetry"]["battery"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "voltage": msg.voltages[0] / 1000.0,
                            "current": msg.current_battery / 100.0,
                            "remaining": msg.battery_remaining
                        })
                    elif msg_type == 'SYS_STATUS':
                        flight_data["telemetry"]["system_status"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "voltage_battery": msg.voltage_battery / 1000.0,
                            "current_battery": msg.current_battery / 100.0,
                            "battery_remaining": msg.battery_remaining
                        })
                    elif msg_type == 'VIBRATION':
                        flight_data["telemetry"]["vibration"].append({
                            "timestamp": getattr(msg, '_timestamp', 0),
                            "vibe_x": msg.vibration_x,
                            "vibe_y": msg.vibration_y,
                            "vibe_z": msg.vibration_z
                        })
                except Exception as msg_error:
                    # Skip problematic messages but don't fail the entire parse
                    print(f"Warning: Could not parse {msg_type}: {msg_error}")
                    continue

            # Store debug info
            flight_data["message_types"] = message_types
            flight_data["total_messages"] = message_count

            # Generate summary
            flight_data["summary"] = self._generate_summary(flight_data)

            # Store flight data
            self.flights[flight_id] = flight_data

            return flight_data

        except Exception as e:
            raise Exception(f"Error parsing MAVLink file: {str(e)}")

    def _generate_summary(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate flight summary statistics"""
        summary = {
            "duration": 0,
            "max_altitude": 0,
            "max_speed": 0,
            "total_distance": 0,
            "battery_usage": 0,
            "anomalies": [],
            "message_stats": flight_data.get("message_types", {}),
            "total_messages": flight_data.get("total_messages", 0)
        }

        # Try both GPS and position data for calculations
        position_data = flight_data["telemetry"]["position"] or flight_data["telemetry"]["gps"]
        
        # Calculate duration
        if position_data:
            start_time = position_data[0]["timestamp"]
            end_time = position_data[-1]["timestamp"]
            summary["duration"] = end_time - start_time

        # Calculate max altitude
        if position_data:
            altitudes = [point.get("alt", 0) for point in position_data]
            summary["max_altitude"] = max(altitudes) if altitudes else 0

        # Calculate max speed from position data
        if flight_data["telemetry"]["position"]:
            speeds = []
            for point in flight_data["telemetry"]["position"]:
                vx = point.get("vx", 0)
                vy = point.get("vy", 0)
                vz = point.get("vz", 0)
                speed = (vx**2 + vy**2 + vz**2)**0.5
                speeds.append(speed)
            summary["max_speed"] = max(speeds) if speeds else 0

        # Battery usage from system status or battery data
        battery_data = flight_data["telemetry"]["system_status"] or flight_data["telemetry"]["battery"]
        if battery_data:
            initial_battery = battery_data[0].get("battery_remaining", 100)
            final_battery = battery_data[-1].get("battery_remaining", 100)
            summary["battery_usage"] = initial_battery - final_battery

        # Detect anomalies
        summary["anomalies"] = self._detect_anomalies(flight_data)

        return summary

    def _detect_anomalies(self, flight_data: Dict[str, Any]) -> List[str]:
        """Detect flight anomalies"""
        anomalies = []

        # Check for GPS signal loss
        gps_data = flight_data["telemetry"]["gps"]
        if gps_data:
            poor_gps_count = sum(1 for point in gps_data if point.get("fix_type", 0) < 3)
            if poor_gps_count > len(gps_data) * 0.1:  # More than 10% poor GPS
                anomalies.append("GPS signal instability detected")

        # Check for high vibration
        vibe_data = flight_data["telemetry"]["vibration"]
        if vibe_data:
            high_vibe_count = sum(1 for v in vibe_data if v.get("vibe_x", 0) > 30 or v.get("vibe_y", 0) > 30)
            if high_vibe_count > len(vibe_data) * 0.05:  # More than 5% high vibration
                anomalies.append("High vibration levels detected")

        # Check for battery issues using system status or battery data
        battery_data = flight_data["telemetry"]["system_status"] or flight_data["telemetry"]["battery"]
        if battery_data:
            low_voltage_count = sum(1 for b in battery_data if b.get("voltage_battery", b.get("voltage", 0)) < 3.3)
            if low_voltage_count > 0:
                anomalies.append("Low battery voltage detected")

        # Check for altitude drops (potential crashes)
        position_data = flight_data["telemetry"]["position"] or flight_data["telemetry"]["gps"]
        if position_data and len(position_data) > 10:
            altitudes = [point.get("alt", 0) for point in position_data]
            for i in range(1, len(altitudes)):
                if altitudes[i-1] - altitudes[i] > 5:  # Sudden 5m drop
                    anomalies.append("Sudden altitude drop detected")
                    break

        return anomalies

    def get_flight_list(self) -> List[Dict[str, Any]]:
        """Get list of all flights"""
        return [
            {
                "flight_id": flight_id,
                "summary": data["summary"]
            }
            for flight_id, data in self.flights.items()
        ]

    def get_flight_details(self, flight_id: str) -> Dict[str, Any]:
        """Get detailed flight information"""
        if flight_id not in self.flights:
            raise Exception(f"Flight {flight_id} not found")

        return self.flights[flight_id]
