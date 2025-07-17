import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uuid

@dataclass
class ConversationTurn:
    id: str
    timestamp: datetime
    user_message: str
    assistant_response: str
    flight_id: str
    context: Dict[str, Any]
    topic: str
    sentiment: str
    follow_up_suggested: bool = False

@dataclass
class FlightSession:
    flight_id: str
    start_time: datetime
    last_activity: datetime
    conversation_turns: List[ConversationTurn]
    topics_discussed: List[str]
    insights_shared: List[str]
    user_interests: List[str]
    anomalies_explored: List[str]

class AgentMemory:
    def __init__(self):
        self.memory_file = "agent_memory.json"
        self.flight_sessions: Dict[str, FlightSession] = {}
        self.user_profile = {
            "preferred_analysis_depth": "detailed",
            "frequently_asked_topics": [],
            "response_preferences": "technical",
            "flight_history": [],
            "learning_patterns": []
        }
        self.load_memory()
    
    def load_memory(self):
        """Load conversation memory from file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    
                # Reconstruct flight sessions
                for session_data in data.get("flight_sessions", []):
                    session = FlightSession(
                        flight_id=session_data["flight_id"],
                        start_time=datetime.fromisoformat(session_data["start_time"]),
                        last_activity=datetime.fromisoformat(session_data["last_activity"]),
                        conversation_turns=[],
                        topics_discussed=session_data.get("topics_discussed", []),
                        insights_shared=session_data.get("insights_shared", []),
                        user_interests=session_data.get("user_interests", []),
                        anomalies_explored=session_data.get("anomalies_explored", [])
                    )
                    
                    # Reconstruct conversation turns
                    for turn_data in session_data.get("conversation_turns", []):
                        turn = ConversationTurn(
                            id=turn_data["id"],
                            timestamp=datetime.fromisoformat(turn_data["timestamp"]),
                            user_message=turn_data["user_message"],
                            assistant_response=turn_data["assistant_response"],
                            flight_id=turn_data["flight_id"],
                            context=turn_data.get("context", {}),
                            topic=turn_data.get("topic", "general"),
                            sentiment=turn_data.get("sentiment", "neutral"),
                            follow_up_suggested=turn_data.get("follow_up_suggested", False)
                        )
                        session.conversation_turns.append(turn)
                    
                    self.flight_sessions[session.flight_id] = session
                
                # Load user profile
                self.user_profile.update(data.get("user_profile", {}))
                
            except Exception as e:
                print(f"Error loading memory: {e}")
    
    def save_memory(self):
        """Save conversation memory to file"""
        try:
            data = {
                "flight_sessions": [],
                "user_profile": self.user_profile,
                "last_updated": datetime.now().isoformat()
            }
            
            # Convert flight sessions to serializable format
            for session in self.flight_sessions.values():
                session_data = {
                    "flight_id": session.flight_id,
                    "start_time": session.start_time.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "topics_discussed": session.topics_discussed,
                    "insights_shared": session.insights_shared,
                    "user_interests": session.user_interests,
                    "anomalies_explored": session.anomalies_explored,
                    "conversation_turns": []
                }
                
                # Convert conversation turns
                for turn in session.conversation_turns:
                    turn_data = {
                        "id": turn.id,
                        "timestamp": turn.timestamp.isoformat(),
                        "user_message": turn.user_message,
                        "assistant_response": turn.assistant_response,
                        "flight_id": turn.flight_id,
                        "context": turn.context,
                        "topic": turn.topic,
                        "sentiment": turn.sentiment,
                        "follow_up_suggested": turn.follow_up_suggested
                    }
                    session_data["conversation_turns"].append(turn_data)
                
                data["flight_sessions"].append(session_data)
            
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def add_conversation_turn(self, user_message: str, assistant_response: str, 
                           flight_id: str, context: Dict[str, Any] = None):
        """Add a new conversation turn to memory"""
        if flight_id not in self.flight_sessions:
            self.flight_sessions[flight_id] = FlightSession(
                flight_id=flight_id,
                start_time=datetime.now(),
                last_activity=datetime.now(),
                conversation_turns=[],
                topics_discussed=[],
                insights_shared=[],
                user_interests=[],
                anomalies_explored=[]
            )
        
        session = self.flight_sessions[flight_id]
        
        # Analyze topic and sentiment
        topic = self._analyze_topic(user_message)
        sentiment = self._analyze_sentiment(user_message)
        
        # Create conversation turn
        turn = ConversationTurn(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            user_message=user_message,
            assistant_response=assistant_response,
            flight_id=flight_id,
            context=context or {},
            topic=topic,
            sentiment=sentiment
        )
        
        session.conversation_turns.append(turn)
        session.last_activity = datetime.now()
        
        # Update session insights
        if topic not in session.topics_discussed:
            session.topics_discussed.append(topic)
        
        # Update user profile
        self._update_user_profile(topic, sentiment)
        
        # Save memory
        self.save_memory()
    
    def get_conversation_context(self, flight_id: str, recent_turns: int = 5) -> str:
        """Get recent conversation context for the flight"""
        if flight_id not in self.flight_sessions:
            return ""
        
        session = self.flight_sessions[flight_id]
        recent_turns_data = session.conversation_turns[-recent_turns:]
        
        context = f"Previous conversation context for flight {flight_id}:\n"
        for turn in recent_turns_data:
            context += f"User: {turn.user_message}\n"
            context += f"Assistant: {turn.assistant_response[:200]}...\n"
            context += f"Topic: {turn.topic}\n\n"
        
        return context
    
    def get_proactive_suggestions(self, flight_id: str, flight_data: Dict[str, Any]) -> List[str]:
        """Generate proactive suggestions based on conversation history and flight data"""
        suggestions = []
        
        if flight_id not in self.flight_sessions:
            return []
        
        session = self.flight_sessions[flight_id]
        
        # Analyze what hasn't been discussed yet
        all_topics = {"gps", "battery", "altitude", "vibration", "safety", "performance", "anomalies"}
        discussed_topics = set(session.topics_discussed)
        undiscussed = all_topics - discussed_topics
        
        # Get flight anomalies
        anomalies = flight_data.get("summary", {}).get("anomalies", [])
        
        # Generate suggestions based on undiscussed topics and anomalies
        if "gps" in undiscussed and any("GPS" in anomaly for anomaly in anomalies):
            suggestions.append("I notice we haven't discussed the GPS signal instability yet. Would you like me to analyze the GPS performance patterns?")
        
        if "battery" in undiscussed and any("battery" in anomaly.lower() for anomaly in anomalies):
            suggestions.append("You might want to know about the battery performance degradation I detected. Should I explain the voltage patterns?")
        
        if "safety" in undiscussed and len(anomalies) > 2:
            suggestions.append("Given the multiple anomalies detected, would you like me to provide a comprehensive safety assessment?")
        
        # Based on conversation patterns
        if len(session.conversation_turns) > 3:
            recent_topics = [turn.topic for turn in session.conversation_turns[-3:]]
            if recent_topics.count("technical") > 1:
                suggestions.append("I see you're interested in technical details. Would you like me to dive deeper into the telemetry data analysis?")
        
        return suggestions[:2]  # Return max 2 suggestions
    
    def get_flight_comparison_insights(self, current_flight_id: str, flight_data: Dict[str, Any]) -> str:
        """Compare current flight with previous flights"""
        if len(self.flight_sessions) < 2:
            return ""
        
        # Get flight metrics
        current_metrics = self._extract_flight_metrics(flight_data)
        
        # Compare with previous flights
        previous_metrics = []
        for session_id, session in self.flight_sessions.items():
            if session_id != current_flight_id and session.conversation_turns:
                # Extract metrics from conversation context
                for turn in session.conversation_turns:
                    if "altitude" in turn.context:
                        prev_metrics = self._extract_flight_metrics(turn.context)
                        if prev_metrics:
                            previous_metrics.append(prev_metrics)
                            break
        
        if not previous_metrics:
            return ""
        
        # Generate comparison insights
        insights = []
        
        avg_prev_altitude = sum(m.get("max_altitude", 0) for m in previous_metrics) / len(previous_metrics)
        if current_metrics.get("max_altitude", 0) > avg_prev_altitude * 1.2:
            insights.append(f"This flight reached {current_metrics.get('max_altitude', 0):.1f}m - significantly higher than your average of {avg_prev_altitude:.1f}m")
        
        avg_prev_duration = sum(m.get("duration", 0) for m in previous_metrics) / len(previous_metrics)
        if current_metrics.get("duration", 0) > avg_prev_duration * 1.3:
            insights.append(f"This was a longer flight ({current_metrics.get('duration', 0):.1f}s vs avg {avg_prev_duration:.1f}s)")
        
        return " | ".join(insights)
    
    def _analyze_topic(self, message: str) -> str:
        """Analyze the topic of a user message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["gps", "signal", "satellite", "location"]):
            return "gps"
        elif any(word in message_lower for word in ["battery", "voltage", "power", "charge"]):
            return "battery"
        elif any(word in message_lower for word in ["altitude", "height", "elevation", "drop"]):
            return "altitude"
        elif any(word in message_lower for word in ["vibration", "shake", "oscillation"]):
            return "vibration"
        elif any(word in message_lower for word in ["safety", "danger", "risk", "concern"]):
            return "safety"
        elif any(word in message_lower for word in ["performance", "efficiency", "optimize"]):
            return "performance"
        elif any(word in message_lower for word in ["anomaly", "error", "issue", "problem"]):
            return "anomalies"
        elif any(word in message_lower for word in ["technical", "detail", "data", "metric"]):
            return "technical"
        else:
            return "general"
    
    def _analyze_sentiment(self, message: str) -> str:
        """Analyze the sentiment of a user message"""
        message_lower = message.lower()
        
        positive_words = ["good", "great", "excellent", "perfect", "amazing", "thanks"]
        negative_words = ["bad", "terrible", "awful", "concerned", "worried", "problem"]
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _update_user_profile(self, topic: str, sentiment: str):
        """Update user profile based on conversation patterns"""
        # Update frequently asked topics
        if topic not in self.user_profile["frequently_asked_topics"]:
            self.user_profile["frequently_asked_topics"].append(topic)
        
        # Update response preferences based on topics
        if topic == "technical":
            self.user_profile["preferred_analysis_depth"] = "detailed"
        elif topic == "general":
            self.user_profile["preferred_analysis_depth"] = "summary"
    
    def _extract_flight_metrics(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from flight data"""
        summary = flight_data.get("summary", {})
        return {
            "max_altitude": summary.get("max_altitude", 0),
            "duration": summary.get("duration", 0),
            "max_speed": summary.get("max_speed", 0),
            "anomaly_count": len(summary.get("anomalies", []))
        }
    
    def cleanup_old_sessions(self, days_to_keep: int = 30):
        """Clean up old conversation sessions"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        sessions_to_remove = []
        for flight_id, session in self.flight_sessions.items():
            if session.last_activity < cutoff_date:
                sessions_to_remove.append(flight_id)
        
        for flight_id in sessions_to_remove:
            del self.flight_sessions[flight_id]
        
        if sessions_to_remove:
            self.save_memory()

# Global memory instance
agent_memory = AgentMemory()