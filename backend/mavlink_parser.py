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
            # Validate file exists and size
            if not os.path.exists(file_path):
                raise Exception("File not found")
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise Exception("Empty file - please upload a valid .bin flight log")
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                raise Exception("File too large (>100MB) - please upload a smaller flight log")
            
            # Validate it's a .bin file
            if not file_path.lower().endswith('.bin'):
                raise Exception("Invalid file type - please upload a .bin flight log file")
            
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
            
            # Add timeout protection for parsing
            import time
            start_time = time.time()
            max_parse_time = 60  # 60 seconds max
            
            while True:
                # Check timeout
                if time.time() - start_time > max_parse_time:
                    raise Exception("File parsing timeout - file may be corrupted or too complex")
                
                msg = mlog.recv_match(blocking=False)
                if msg is None:
                    break

                message_count += 1
                msg_type = msg.get_type()
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
                
                # Basic validation
                if message_count > 1000000:  # Prevent memory issues
                    raise Exception("File too complex - contains too many messages")

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

            # Validate we got some useful data
            if message_count == 0:
                raise Exception("No MAVLink messages found - file may be corrupted or not a valid flight log")
            
            # Check for essential telemetry
            essential_data = False
            if (flight_data["telemetry"]["gps"] or 
                flight_data["telemetry"]["position"] or 
                flight_data["telemetry"]["attitude"]):
                essential_data = True
            
            if not essential_data:
                raise Exception("No essential telemetry data found - file may not contain flight data")

            # Store flight data
            self.flights[flight_id] = flight_data

            return flight_data

        except Exception as e:
            # Clean up any partial data
            if 'flight_id' in locals() and flight_id in self.flights:
                del self.flights[flight_id]
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

        # Prepare telemetry summary for LLM analysis (no hardcoded rules)
        summary["telemetry_summary"] = self._prepare_telemetry_summary(flight_data)
        
        # Proactively analyze anomalies using LLM
        summary["anomaly_analysis"] = self._analyze_anomalies_with_llm(summary["telemetry_summary"])

        return summary

    def _prepare_telemetry_summary(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare telemetry data summary for LLM analysis without hardcoded rules"""
        telemetry_summary = {}
        
        # GPS data patterns
        gps_data = flight_data["telemetry"]["gps"]
        if gps_data:
            fix_types = [point.get("fix_type", 0) for point in gps_data]
            hdop_values = [point.get("hdop", 0) for point in gps_data if point.get("hdop", 0) > 0]
            satellite_counts = [point.get("satellites_visible", 0) for point in gps_data]
            
            telemetry_summary["gps_patterns"] = {
                "total_points": len(gps_data),
                "fix_type_distribution": {
                    "no_fix": fix_types.count(0),
                    "gps_fix": fix_types.count(3),
                    "dgps_fix": fix_types.count(4),
                    "rtk_fix": fix_types.count(5)
                },
                "hdop_range": {"min": min(hdop_values) if hdop_values else 0, "max": max(hdop_values) if hdop_values else 0},
                "satellite_range": {"min": min(satellite_counts) if satellite_counts else 0, "max": max(satellite_counts) if satellite_counts else 0}
            }
        
        # Vibration patterns
        vibe_data = flight_data["telemetry"]["vibration"]
        if vibe_data:
            vibe_x_values = [v.get("vibe_x", 0) for v in vibe_data]
            vibe_y_values = [v.get("vibe_y", 0) for v in vibe_data]
            vibe_z_values = [v.get("vibe_z", 0) for v in vibe_data]
            
            telemetry_summary["vibration_patterns"] = {
                "total_readings": len(vibe_data),
                "x_axis": {"min": min(vibe_x_values) if vibe_x_values else 0, "max": max(vibe_x_values) if vibe_x_values else 0},
                "y_axis": {"min": min(vibe_y_values) if vibe_y_values else 0, "max": max(vibe_y_values) if vibe_y_values else 0},
                "z_axis": {"min": min(vibe_z_values) if vibe_z_values else 0, "max": max(vibe_z_values) if vibe_z_values else 0}
            }
        
        # Battery voltage patterns
        battery_data = flight_data["telemetry"]["system_status"] or flight_data["telemetry"]["battery"]
        if battery_data:
            voltage_values = [b.get("voltage_battery", b.get("voltage", 0)) for b in battery_data if b.get("voltage_battery", b.get("voltage", 0)) > 0]
            current_values = [b.get("current_battery", b.get("current", 0)) for b in battery_data if b.get("current_battery", b.get("current", 0)) != 0]
            
            telemetry_summary["battery_patterns"] = {
                "total_readings": len(battery_data),
                "voltage_trend": voltage_values[:5] + voltage_values[-5:] if len(voltage_values) > 10 else voltage_values,
                "voltage_range": {"min": min(voltage_values) if voltage_values else 0, "max": max(voltage_values) if voltage_values else 0},
                "current_range": {"min": min(current_values) if current_values else 0, "max": max(current_values) if current_values else 0}
            }
        
        # Altitude and position patterns
        position_data = flight_data["telemetry"]["position"] or flight_data["telemetry"]["gps"]
        if position_data and len(position_data) > 1:
            altitudes = [point.get("alt", 0) for point in position_data]
            altitude_changes = [altitudes[i] - altitudes[i-1] for i in range(1, len(altitudes))]
            
            telemetry_summary["altitude_patterns"] = {
                "total_points": len(position_data),
                "altitude_range": {"min": min(altitudes) if altitudes else 0, "max": max(altitudes) if altitudes else 0},
                "largest_climb": max(altitude_changes) if altitude_changes else 0,
                "largest_descent": min(altitude_changes) if altitude_changes else 0,
                "altitude_profile": altitudes[::max(1, len(altitudes)//20)]  # Sample 20 points
            }
        
        return telemetry_summary
    
    def _analyze_anomalies_with_llm(self, telemetry_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze anomalies using LLM for proactive detection"""
        try:
            # Import here to avoid circular import
            from chat_service import ChatService
            
            chat_service = ChatService()
            
            # Create a focused prompt for anomaly detection
            anomaly_prompt = self._build_anomaly_detection_prompt(telemetry_summary)
            
            # Get LLM analysis if available
            if chat_service.openai_client:
                response = chat_service.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert UAV flight data analyst. Analyze the provided telemetry patterns and identify potential anomalies with reasoning."},
                        {"role": "user", "content": anomaly_prompt}
                    ],
                    max_tokens=500,
                    temperature=0.3
                )
                analysis_result = response.choices[0].message.content
            elif chat_service.anthropic_client:
                response = chat_service.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=500,
                    system="You are an expert UAV flight data analyst. Analyze the provided telemetry patterns and identify potential anomalies with reasoning.",
                    messages=[
                        {"role": "user", "content": anomaly_prompt}
                    ]
                )
                analysis_result = response.content[0].text
            else:
                # Fallback analysis without LLM
                analysis_result = self._fallback_anomaly_analysis(telemetry_summary)
            
            # Parse the analysis result into structured format
            return self._parse_anomaly_analysis(analysis_result, telemetry_summary)
            
        except Exception as e:
            print(f"Error in LLM anomaly analysis: {e}")
            return {
                "anomalies_detected": [],
                "severity_assessment": "unknown",
                "analysis_summary": "Unable to perform automatic anomaly analysis",
                "recommendations": []
            }
    
    def _build_anomaly_detection_prompt(self, telemetry_summary: Dict[str, Any]) -> str:
        """Build focused prompt for anomaly detection"""
        prompt = """Please analyze the following flight telemetry patterns and identify any anomalies or concerning behaviors. Focus on:

1. GPS signal quality and stability
2. Vibration patterns that might indicate mechanical issues
3. Battery performance and voltage trends
4. Altitude behavior and sudden changes
5. Correlations between different sensors

Telemetry Data:
"""
        
        # Add each telemetry section with clear formatting
        for section_name, section_data in telemetry_summary.items():
            prompt += f"\n{section_name.replace('_', ' ').title()}:\n"
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    prompt += f"  - {key}: {value}\n"
            else:
                prompt += f"  {section_data}\n"
        
        prompt += """
Please provide your analysis in the following format:
ANOMALIES: [List specific anomalies found, or "None detected"]
SEVERITY: [Low/Medium/High/Critical]
REASONING: [Explain your reasoning for each anomaly]
RECOMMENDATIONS: [Specific actions to take]
"""
        
        return prompt
    
    def _fallback_anomaly_analysis(self, telemetry_summary: Dict[str, Any]) -> str:
        """Fallback analysis when no LLM is available"""
        analysis = "ANOMALIES: "
        anomalies = []
        
        # Basic pattern-based analysis (not hardcoded rules, but pattern recognition)
        if "gps_patterns" in telemetry_summary:
            gps = telemetry_summary["gps_patterns"]
            if gps.get("fix_type_distribution", {}).get("no_fix", 0) > 0:
                anomalies.append("GPS signal loss detected")
        
        if "vibration_patterns" in telemetry_summary:
            vibe = telemetry_summary["vibration_patterns"]
            if any(axis.get("max", 0) > 30 for axis in [vibe.get("x_axis", {}), vibe.get("y_axis", {}), vibe.get("z_axis", {})]):
                anomalies.append("High vibration levels detected")
        
        if "battery_patterns" in telemetry_summary:
            battery = telemetry_summary["battery_patterns"]
            voltage_trend = battery.get("voltage_trend", [])
            if len(voltage_trend) > 1 and voltage_trend[-1] < voltage_trend[0] * 0.8:
                anomalies.append("Significant battery voltage drop")
        
        if anomalies:
            analysis += ", ".join(anomalies)
            analysis += "\nSEVERITY: Medium\nREASONING: Pattern-based analysis without LLM\nRECOMMENDATIONS: Review flight data manually"
        else:
            analysis += "None detected\nSEVERITY: Low\nREASONING: No obvious patterns detected\nRECOMMENDATIONS: Flight appears normal"
        
        return analysis
    
    def _parse_anomaly_analysis(self, analysis_result: str, telemetry_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM analysis result into structured format"""
        try:
            lines = analysis_result.strip().split('\n')
            parsed = {
                "anomalies_detected": [],
                "severity_assessment": "unknown",
                "analysis_summary": "",
                "recommendations": [],
                "raw_analysis": analysis_result
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith("ANOMALIES:"):
                    current_section = "anomalies"
                    anomalies_text = line[10:].strip()
                    if anomalies_text and anomalies_text.lower() != "none detected":
                        parsed["anomalies_detected"] = [a.strip() for a in anomalies_text.split(',')]
                elif line.startswith("SEVERITY:"):
                    current_section = "severity"
                    parsed["severity_assessment"] = line[9:].strip().lower()
                elif line.startswith("REASONING:"):
                    current_section = "reasoning"
                    parsed["analysis_summary"] = line[10:].strip()
                elif line.startswith("RECOMMENDATIONS:"):
                    current_section = "recommendations"
                    rec_text = line[16:].strip()
                    if rec_text:
                        parsed["recommendations"] = [r.strip() for r in rec_text.split(',')]
                elif current_section == "anomalies" and line and line[0].isdigit():
                    # Handle numbered anomaly list
                    parsed["anomalies_detected"].append(line.split('.', 1)[1].strip() if '.' in line else line)
                elif current_section == "reasoning" and line:
                    if line[0].isdigit():
                        # Skip numbered reasoning, focus on main text
                        if ':' in line:
                            parsed["analysis_summary"] += " " + line.split(':', 1)[1].strip()
                    else:
                        parsed["analysis_summary"] += " " + line
                elif current_section == "recommendations" and line:
                    if line[0].isdigit():
                        # Handle numbered recommendations
                        rec_text = line.split('.', 1)[1].strip() if '.' in line else line
                        if ':' in rec_text:
                            rec_text = rec_text.split(':', 1)[1].strip()
                        parsed["recommendations"].append(rec_text)
                    else:
                        parsed["recommendations"].append(line.strip())
            
            # Take highest severity if multiple mentioned
            if "critical" in parsed["severity_assessment"]:
                parsed["severity_assessment"] = "critical"
            elif "high" in parsed["severity_assessment"]:
                parsed["severity_assessment"] = "high"
            elif "medium" in parsed["severity_assessment"]:
                parsed["severity_assessment"] = "medium"
            elif "low" in parsed["severity_assessment"]:
                parsed["severity_assessment"] = "low"
            
            return parsed
            
        except Exception as e:
            print(f"Error parsing anomaly analysis: {e}")
            return {
                "anomalies_detected": ["Analysis parsing error"],
                "severity_assessment": "unknown",
                "analysis_summary": analysis_result,
                "recommendations": [],
                "raw_analysis": analysis_result
            }

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
