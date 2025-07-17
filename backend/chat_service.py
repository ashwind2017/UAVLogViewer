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

    async def process_message(self, message: str, flight_id: str = None) -> Dict[str, Any]:
        """Process chat message about flight data with advanced memory"""
        try:
            # Get flight data if flight_id provided
            flight_data = None
            if flight_id:
                flight_data = self._get_flight_data(flight_id)

            # Get conversation context from memory
            conversation_context = ""
            if flight_id:
                conversation_context = agent_memory.get_conversation_context(flight_id)

            # Generate response using LLM
            if self.openai_client:
                response = await self._query_openai(message, flight_data, conversation_context)
            elif self.anthropic_client:
                response = await self._query_anthropic(message, flight_data, conversation_context)
            else:
                response = self._fallback_response(message, flight_data)

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
            return {
                "answer": f"Sorry, I encountered an error: {str(e)}",
                "flight_data": None,
                "proactive_suggestions": [],
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
            anomalies = summary.get("anomalies", [])

            flight_context = f"""
Current Flight Data:
- Duration: {summary.get('duration', 'Unknown')} seconds
- Max Altitude: {summary.get('max_altitude', 'Unknown')} meters
- GPS Points: {len(flight_data.get('telemetry', {}).get('gps', []))}
- Battery Data Points: {len(flight_data.get('telemetry', {}).get('battery', []))}
- Detected Anomalies: {', '.join(anomalies) if anomalies else 'None'}

Use this data to answer questions about the flight."""
            
            context_parts.append(flight_context)

        return base_prompt + "".join(context_parts)

    def _fallback_response(self, message: str, flight_data: Optional[Dict]) -> str:
        """Fallback response when no LLM API is available"""
        if flight_data:
            summary = flight_data.get("summary", {})
            anomalies = summary.get("anomalies", [])

            return f"""I can see you're asking about flight data. Here's what I found:

Flight Summary:
- Duration: {summary.get('duration', 'Unknown')} seconds
- Max Altitude: {summary.get('max_altitude', 'Unknown')} meters
- Anomalies: {', '.join(anomalies) if anomalies else 'None detected'}

To get more detailed AI analysis, please set up your OpenAI or Anthropic API key in the environment variables."""
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
