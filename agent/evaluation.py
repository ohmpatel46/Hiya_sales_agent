"""
Evaluation Framework for Sales Agent
Tracks conversation quality, success metrics, and performance indicators
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from agent.schemas import SessionState, TraceTurn


@dataclass
class ConversationMetrics:
    """Metrics for a single conversation"""
    session_id: str
    lead_name: str
    lead_phone: str
    start_time: datetime
    end_time: Optional[datetime]
    total_turns: int
    success: bool
    meeting_scheduled: bool
    meeting_time: Optional[str]
    outcome: str  # "interested", "not_interested", "callback", "no_answer"
    tools_used: List[str]
    error_count: int
    conversation_quality_score: float  # 0-10 scale


@dataclass
class AgentPerformance:
    """Overall agent performance metrics"""
    total_conversations: int
    successful_conversations: int
    meetings_scheduled: int
    success_rate: float
    meeting_rate: float
    average_turns_per_conversation: float
    average_conversation_duration: float
    common_outcomes: Dict[str, int]
    error_rate: float
    quality_score_average: float


class SalesAgentEvaluator:
    """Evaluates sales agent performance"""
    
    def __init__(self, log_file: str = "evaluation_log.jsonl"):
        self.log_file = log_file
        self.metrics: List[ConversationMetrics] = []
        self._load_existing_metrics()
    
    def _load_existing_metrics(self):
        """Load existing metrics from log file"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Convert datetime strings back to datetime objects
                        data['start_time'] = datetime.fromisoformat(data['start_time'])
                        if data['end_time']:
                            data['end_time'] = datetime.fromisoformat(data['end_time'])
                        self.metrics.append(ConversationMetrics(**data))
    
    def log_conversation(self, session: SessionState, outcome: str = "unknown"):
        """Log a completed conversation"""
        
        # Calculate metrics
        total_turns = len(session.history)
        success = session.done and outcome in ["interested", "callback"]
        
        # Check if meeting was scheduled
        meeting_scheduled = False
        meeting_time = None
        tools_used = []
        
        for turn in session.history:
            for tool_call in turn.tool_calls:
                tools_used.append(tool_call.name)
                if tool_call.name == "calendar.create_event":
                    meeting_scheduled = True
                    # Extract meeting time from tool call args
                    if "start_dt" in tool_call.args:
                        meeting_time = tool_call.args["start_dt"]
        
        # Calculate conversation quality score
        quality_score = self._calculate_quality_score(session, outcome)
        
        # Count errors
        error_count = sum(1 for turn in session.history 
                         for result in turn.tool_results 
                         if "error" in result)
        
        # Create metrics
        metrics = ConversationMetrics(
            session_id=session.session_id,
            lead_name=session.lead.name if session.lead else "Unknown",
            lead_phone=session.lead.phone if session.lead else "Unknown",
            start_time=datetime.now(),  # This should be tracked from session start
            end_time=datetime.now(),
            total_turns=total_turns,
            success=success,
            meeting_scheduled=meeting_scheduled,
            meeting_time=meeting_time,
            outcome=outcome,
            tools_used=list(set(tools_used)),
            error_count=error_count,
            conversation_quality_score=quality_score
        )
        
        # Add to metrics
        self.metrics.append(metrics)
        
        # Log to file
        self._save_metrics(metrics)
        
        return metrics
    
    def _calculate_quality_score(self, session: SessionState, outcome: str) -> float:
        """Calculate conversation quality score (0-10)"""
        score = 5.0  # Base score
        
        # Adjust based on outcome
        if outcome == "interested":
            score += 3.0
        elif outcome == "callback":
            score += 2.0
        elif outcome == "not_interested":
            score += 1.0
        else:
            score -= 1.0
        
        # Adjust based on conversation length
        turn_count = len(session.history)
        if 3 <= turn_count <= 8:  # Optimal conversation length
            score += 1.0
        elif turn_count > 10:  # Too long
            score -= 0.5
        
        # Adjust based on errors
        error_count = sum(1 for turn in session.history 
                         for result in turn.tool_results 
                         if "error" in result)
        score -= error_count * 0.5
        
        # Adjust based on tools used
        tools_used = set()
        for turn in session.history:
            for tool_call in turn.tool_calls:
                tools_used.add(tool_call.name)
        
        if "calendar.create_event" in tools_used:
            score += 1.0
        if "crm_stub.log_outcome" in tools_used:
            score += 0.5
        
        return max(0.0, min(10.0, score))
    
    def _save_metrics(self, metrics: ConversationMetrics):
        """Save metrics to log file"""
        with open(self.log_file, 'a') as f:
            # Convert datetime objects to strings for JSON serialization
            data = asdict(metrics)
            data['start_time'] = data['start_time'].isoformat()
            if data['end_time']:
                data['end_time'] = data['end_time'].isoformat()
            f.write(json.dumps(data) + '\n')
    
    def get_performance_summary(self) -> AgentPerformance:
        """Get overall performance summary"""
        if not self.metrics:
            return AgentPerformance(
                total_conversations=0,
                successful_conversations=0,
                meetings_scheduled=0,
                success_rate=0.0,
                meeting_rate=0.0,
                average_turns_per_conversation=0.0,
                average_conversation_duration=0.0,
                common_outcomes={},
                error_rate=0.0,
                quality_score_average=0.0
            )
        
        total_conversations = len(self.metrics)
        successful_conversations = sum(1 for m in self.metrics if m.success)
        meetings_scheduled = sum(1 for m in self.metrics if m.meeting_scheduled)
        
        success_rate = successful_conversations / total_conversations if total_conversations > 0 else 0
        meeting_rate = meetings_scheduled / total_conversations if total_conversations > 0 else 0
        
        average_turns = sum(m.total_turns for m in self.metrics) / total_conversations
        
        # Calculate average duration
        durations = []
        for m in self.metrics:
            if m.end_time:
                duration = (m.end_time - m.start_time).total_seconds()
                durations.append(duration)
        average_duration = sum(durations) / len(durations) if durations else 0
        
        # Count outcomes
        outcomes = {}
        for m in self.metrics:
            outcomes[m.outcome] = outcomes.get(m.outcome, 0) + 1
        
        # Calculate error rate
        total_errors = sum(m.error_count for m in self.metrics)
        total_turns = sum(m.total_turns for m in self.metrics)
        error_rate = total_errors / total_turns if total_turns > 0 else 0
        
        # Average quality score
        quality_average = sum(m.conversation_quality_score for m in self.metrics) / total_conversations
        
        return AgentPerformance(
            total_conversations=total_conversations,
            successful_conversations=successful_conversations,
            meetings_scheduled=meetings_scheduled,
            success_rate=success_rate,
            meeting_rate=meeting_rate,
            average_turns_per_conversation=average_turns,
            average_conversation_duration=average_duration,
            common_outcomes=outcomes,
            error_rate=error_rate,
            quality_score_average=quality_average
        )
    
    def print_performance_report(self):
        """Print a formatted performance report"""
        performance = self.get_performance_summary()
        
        print("=" * 60)
        print("SALES AGENT PERFORMANCE REPORT")
        print("=" * 60)
        print(f"Total Conversations: {performance.total_conversations}")
        print(f"Successful Conversations: {performance.successful_conversations}")
        print(f"Meetings Scheduled: {performance.meetings_scheduled}")
        print(f"Success Rate: {performance.success_rate:.1%}")
        print(f"Meeting Rate: {performance.meeting_rate:.1%}")
        print(f"Average Turns per Conversation: {performance.average_turns_per_conversation:.1f}")
        print(f"Average Duration: {performance.average_conversation_duration:.1f} seconds")
        print(f"Error Rate: {performance.error_rate:.1%}")
        print(f"Average Quality Score: {performance.quality_score_average:.1f}/10")
        
        print("\nOutcome Distribution:")
        for outcome, count in performance.common_outcomes.items():
            percentage = count / performance.total_conversations * 100
            print(f"  {outcome}: {count} ({percentage:.1f}%)")
        
        print("=" * 60)


# Global evaluator instance
evaluator = SalesAgentEvaluator()


def evaluate_conversation(session: SessionState, outcome: str = "unknown") -> ConversationMetrics:
    """Evaluate a completed conversation"""
    return evaluator.log_conversation(session, outcome)


def get_performance_summary() -> AgentPerformance:
    """Get overall performance summary"""
    return evaluator.get_performance_summary()


def print_performance_report():
    """Print performance report"""
    evaluator.print_performance_report()


# Example usage
if __name__ == "__main__":
    # Test the evaluator
    from agent.schemas import Lead, SessionState, TraceTurn
    
    # Create a test session
    test_lead = Lead(
        id="test",
        name="John Doe",
        phone="+1234567890",
        email="john@example.com",
        company="Test Corp"
    )
    
    test_session = SessionState(
        session_id="test_session",
        lead=test_lead,
        slots={},
        history=[],
        done=True
    )
    
    # Add some test history
    test_session.history.append(TraceTurn(
        user="Hello",
        agent="Hi John, I'm calling about TopSales...",
        tool_calls=[],
        tool_results=[],
        state=test_session.dict()
    ))
    
    # Evaluate the conversation
    metrics = evaluate_conversation(test_session, "interested")
    print("Test Metrics:", metrics)
    
    # Print performance report
    print_performance_report()
