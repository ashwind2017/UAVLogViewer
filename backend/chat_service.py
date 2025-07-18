import openai
import anthropic
import json
from typing import Dict, Any, Optional
import os
from datetime import datetime
from dotenv import load_dotenv
from memory_service import agent_memory

# Load environment variables from .env file
load_dotenv()

class ChatService:
    def __init__(self):
        # Initialize API clients
        self.openai_client = None
        self.anthropic_client = None

        # Try to initialize OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = openai.OpenAI(api_key=openai_key)

        # Try to initialize Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)

        # Flight data cache
        self.flight_cache = {}
        self.flight_cache_file = "flight_cache.json"
        self.load_flight_cache()

    async def process_message(self, message: str, flight_id: str = None) -> Dict[str, Any]:
        """Process chat message about flight data with advanced memory"""
        try:
            # Validate input
            if not message or not message.strip():
                return {
                    "answer": "Please enter a message to get started!",
                    "flight_data": None,
                    "proactive_suggestions": [],
                    "comparison_insights": "",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Truncate very long messages
            if len(message) > 2000:
                message = message[:2000] + "..."

            # Get flight data if flight_id provided
            flight_data = None
            if flight_id:
                flight_data = self._get_flight_data(flight_id)

            # Get conversation context from memory
            conversation_context = ""
            if flight_id:
                conversation_context = agent_memory.get_conversation_context(flight_id)

            # Generate response using LLM with timeout protection
            response = None
            try:
                if self.openai_client:
                    response = await self._query_openai(message, flight_data, conversation_context)
                elif self.anthropic_client:
                    response = await self._query_anthropic(message, flight_data, conversation_context)
                else:
                    response = self._fallback_response(message, flight_data)
            except Exception as llm_error:
                print(f"LLM Error: {llm_error}")
                response = self._fallback_response(message, flight_data, error=str(llm_error))

            # Store conversation in memory
            if flight_id:
                agent_memory.add_conversation_turn(
                    user_message=message,
                    assistant_response=response,
                    flight_id=flight_id,
                    context={"flight_data": flight_data}
                )

            # Get proactive suggestions
            suggestions = []
            if flight_id and flight_data:
                suggestions = agent_memory.get_proactive_suggestions(flight_id, flight_data)

            # Get flight comparison insights
            comparison_insights = ""
            if flight_id and flight_data:
                comparison_insights = agent_memory.get_flight_comparison_insights(flight_id, flight_data)

            return {
                "answer": response,
                "flight_data": flight_data or {},
                "proactive_suggestions": suggestions,
                "comparison_insights": comparison_insights,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Chat service error: {e}")
            return {
                "answer": f"I'm having trouble processing your request. Please try again or upload a new flight file. Error: {str(e)}",
                "flight_data": None,
                "proactive_suggestions": ["Try uploading a different .bin file", "Ask a simpler question", "Check your internet connection"],
                "comparison_insights": "",
                "timestamp": datetime.now().isoformat()
            }

    async def _query_openai(self, message: str, flight_data: Optional[Dict], conversation_context: str = "") -> str:
        """Query OpenAI with flight data context and conversation memory"""
        system_prompt = self._build_system_prompt(flight_data, conversation_context)

        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=700,
            temperature=0.7
        )

        return response.choices[0].message.content

    async def _query_anthropic(self, message: str, flight_data: Optional[Dict], conversation_context: str = "") -> str:
        """Query Anthropic with flight data context and conversation memory"""
        system_prompt = self._build_system_prompt(flight_data, conversation_context)

        response = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=700,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ]
        )

        return response.content[0].text

    def _build_system_prompt(self, flight_data: Optional[Dict], conversation_context: str = "") -> str:
        """Build system prompt with flight data context and conversation memory"""
        base_prompt = """You are an expert UAV flight data analyst with advanced memory capabilities. You help users understand flight telemetry data, identify issues, and provide insights about drone flights.

You can analyze:
- GPS coordinates and flight paths
- Altitude and speed data
- Battery performance
- Vibration levels
- Flight anomalies
- Safety concerns

IMPORTANT: You have conversation memory and should:
1. Reference previous discussions when relevant
2. Build upon earlier analyses
3. Avoid repeating information already covered
4. Provide progressive insights that deepen understanding
5. Be proactive in suggesting related topics

Provide clear, technical answers while being accessible to users."""

        context_parts = []
        
        if conversation_context:
            context_parts.append(f"\nConversation History:\n{conversation_context}")

        if flight_data:
            summary = flight_data.get("summary", {})
            telemetry_summary = summary.get("telemetry_summary", {})

            flight_context = f"""
Current Flight Data:
- Duration: {summary.get('duration', 'Unknown')} seconds
- Max Altitude: {summary.get('max_altitude', 'Unknown')} meters
- GPS Points: {len(flight_data.get('telemetry', {}).get('gps', []))}
- Battery Data Points: {len(flight_data.get('telemetry', {}).get('battery', []))}

Telemetry Analysis Patterns (analyze for anomalies dynamically):
{self._format_telemetry_patterns(telemetry_summary)}

Automatic Anomaly Analysis Results:
{self._format_anomaly_analysis(summary.get('anomaly_analysis', {}))}

IMPORTANT: Instead of rigid rules, analyze these patterns to identify:
- Unusual GPS behavior (look for patterns, not fixed thresholds)
- Concerning vibration trends (consider context and flight phase)
- Battery performance issues (analyze voltage trends and current draw)
- Altitude anomalies (sudden changes, unexpected patterns)
- System stability indicators (correlate multiple sensors)

Use your expertise to reason about these patterns contextually."""
            
            context_parts.append(flight_context)
        else:
            no_flight_context = """
No flight data is currently loaded. You can:
1. Answer general questions about UAV analysis, MAVLink protocol, or flight safety
2. Provide guidance on what to look for in flight logs
3. Explain common flight anomalies and their causes
4. Help interpret flight telemetry data concepts
5. Suggest the user upload a .bin flight log file for specific analysis

Be helpful and informative even without specific flight data."""
            
            context_parts.append(no_flight_context)

        return base_prompt + "".join(context_parts)

    def _format_telemetry_patterns(self, telemetry_summary: Dict[str, Any]) -> str:
        """Format telemetry patterns for LLM analysis"""
        if not telemetry_summary:
            return "No telemetry patterns available for analysis."
        
        formatted_patterns = []
        
        # GPS patterns
        if "gps_patterns" in telemetry_summary:
            gps = telemetry_summary["gps_patterns"]
            formatted_patterns.append(f"""
GPS Signal Quality:
- Total GPS readings: {gps.get('total_points', 0)}
- Fix types: {gps.get('fix_type_distribution', {})}
- HDOP range: {gps.get('hdop_range', {})}
- Satellite count range: {gps.get('satellite_range', {})}""")
        
        # Vibration patterns
        if "vibration_patterns" in telemetry_summary:
            vibe = telemetry_summary["vibration_patterns"]
            formatted_patterns.append(f"""
Vibration Analysis:
- Total vibration readings: {vibe.get('total_readings', 0)}
- X-axis range: {vibe.get('x_axis', {})}
- Y-axis range: {vibe.get('y_axis', {})}
- Z-axis range: {vibe.get('z_axis', {})}""")
        
        # Battery patterns
        if "battery_patterns" in telemetry_summary:
            battery = telemetry_summary["battery_patterns"]
            formatted_patterns.append(f"""
Battery Performance:
- Total battery readings: {battery.get('total_readings', 0)}
- Voltage trend: {battery.get('voltage_trend', [])}
- Voltage range: {battery.get('voltage_range', {})}
- Current range: {battery.get('current_range', {})}""")
        
        # Altitude patterns
        if "altitude_patterns" in telemetry_summary:
            altitude = telemetry_summary["altitude_patterns"]
            formatted_patterns.append(f"""
Altitude Behavior:
- Total position readings: {altitude.get('total_points', 0)}
- Altitude range: {altitude.get('altitude_range', {})}
- Largest climb: {altitude.get('largest_climb', 0)}m
- Largest descent: {altitude.get('largest_descent', 0)}m
- Altitude profile: {altitude.get('altitude_profile', [])}""")
        
        return "\n".join(formatted_patterns) if formatted_patterns else "No detailed telemetry patterns available."
    
    def _format_anomaly_analysis(self, anomaly_analysis: Dict[str, Any]) -> str:
        """Format anomaly analysis results for LLM context"""
        if not anomaly_analysis:
            return "No automatic anomaly analysis available."
        
        formatted_analysis = []
        
        # Anomalies detected
        anomalies = anomaly_analysis.get("anomalies_detected", [])
        if anomalies:
            formatted_analysis.append(f"Anomalies Detected: {', '.join(anomalies)}")
        else:
            formatted_analysis.append("Anomalies Detected: None")
        
        # Severity assessment
        severity = anomaly_analysis.get("severity_assessment", "unknown")
        formatted_analysis.append(f"Severity Level: {severity.title()}")
        
        # Analysis summary
        analysis_summary = anomaly_analysis.get("analysis_summary", "")
        if analysis_summary:
            formatted_analysis.append(f"Analysis Summary: {analysis_summary}")
        
        # Recommendations
        recommendations = anomaly_analysis.get("recommendations", [])
        if recommendations:
            formatted_analysis.append(f"Recommendations: {', '.join(recommendations)}")
        
        return "\n".join(formatted_analysis)

    def _fallback_response(self, message: str, flight_data: Optional[Dict], error: str = None) -> str:
        """Fallback response when no LLM API is available"""
        if flight_data:
            summary = flight_data.get("summary", {})
            anomalies = summary.get("anomalies", [])
            anomaly_analysis = summary.get("anomaly_analysis", {})

            analysis_text = ""
            if anomaly_analysis:
                analysis_text = f"""
Automatic Anomaly Analysis:
{self._format_anomaly_analysis(anomaly_analysis)}
"""

            return f"""I can see you're asking about flight data. Here's what I found:

Flight Summary:
- Duration: {summary.get('duration', 'Unknown')} seconds
- Max Altitude: {summary.get('max_altitude', 'Unknown')} meters
- Legacy Anomalies: {', '.join(anomalies) if anomalies else 'None detected'}
{analysis_text}
To get more detailed AI analysis, please set up your OpenAI or Anthropic API key in the environment variables.
{f"Note: {error}" if error else ""}"""
        else:
            return "I'm ready to analyze flight data! Please upload a .bin file first, then I can answer questions about the flight telemetry."

    def _get_flight_data(self, flight_id: str) -> Optional[Dict]:
        """Get flight data from cache or parser"""
        # This would normally get data from the parser
        # For now, return cached data
        return self.flight_cache.get(flight_id)

    def cache_flight_data(self, flight_id: str, data: Dict[str, Any]):
        """Cache flight data for quick access"""
        self.flight_cache[flight_id] = data
        self.save_flight_cache()
        
    def get_most_recent_flight(self) -> Optional[Dict[str, Any]]:
        """Get the most recently cached flight data"""
        if not self.flight_cache:
            return None
        
        # Get the most recent flight based on timestamp or just return the last one
        most_recent_flight_id = max(self.flight_cache.keys(), 
                                   key=lambda fid: self.flight_cache[fid].get('timestamp', ''))
        return self.flight_cache.get(most_recent_flight_id)
    
    def load_flight_cache(self):
        """Load flight cache from file"""
        try:
            if os.path.exists(self.flight_cache_file):
                with open(self.flight_cache_file, 'r') as f:
                    self.flight_cache = json.load(f)
                print(f"Loaded {len(self.flight_cache)} flights from cache")
        except Exception as e:
            print(f"Error loading flight cache: {e}")
    
    def save_flight_cache(self):
        """Save flight cache to file"""
        try:
            with open(self.flight_cache_file, 'w') as f:
                json.dump(self.flight_cache, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving flight cache: {e}")
