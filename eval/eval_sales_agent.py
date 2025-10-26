#!/usr/bin/env python3
"""
Sales Agent Evaluation Script
Run this to see performance metrics and conversation quality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.evaluation import print_performance_report, get_performance_summary
from agent.schemas import Lead, SessionState, TraceTurn
from agent.orchestrator import handle_turn
import json


def run_evaluation_demo():
    """Run a demo evaluation with sample conversations"""
    
    print("Running Sales Agent Evaluation Demo...")
    print("=" * 50)
    
    # Sample leads
    leads = [
        Lead(id="1", name="Alice Johnson", phone="+1234567890", email="alice@company.com", company="Tech Corp"),
        Lead(id="2", name="Bob Smith", phone="+1234567891", email="bob@startup.io", company="Startup Inc"),
        Lead(id="3", name="Carol Davis", phone="+1234567892", email="carol@enterprise.com", company="Enterprise Ltd"),
    ]
    
    # Sample conversations
    conversations = [
        {
            "lead": leads[0],
            "messages": [
                "",
                "Yes, I'm interested in learning more about your AI sales agent",
                "Next Wednesday at 2pm works for me",
                "Yes, that sounds perfect"
            ],
            "outcome": "interested"
        },
        {
            "lead": leads[1],
            "messages": [
                "",
                "I'm not really interested right now",
                "Maybe call me back next month"
            ],
            "outcome": "callback"
        },
        {
            "lead": leads[2],
            "messages": [
                "",
                "We already have a sales solution",
                "Please remove me from your list"
            ],
            "outcome": "not_interested"
        }
    ]
    
    # Simulate conversations
    for i, conv in enumerate(conversations):
        print(f"\nSimulating conversation {i+1} with {conv['lead'].name}...")
        
        session_id = f"demo_session_{i+1}"
        
        for j, message in enumerate(conv['messages']):
            if j == 0:  # Initial greeting
                response = handle_turn(session_id, conv['lead'], message)
                print(f"Agent: {response['reply']}")
            else:
                response = handle_turn(session_id, conv['lead'], message)
                print(f"User: {message}")
                print(f"Agent: {response['reply']}")
        
        # Mark conversation as complete
        if response.get("final", False):
            print(f"Conversation completed with outcome: {conv['outcome']}")
    
    print("\n" + "=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)
    
    # Print performance report
    print_performance_report()


def show_evaluation_metrics():
    """Show current evaluation metrics"""
    print("Current Sales Agent Performance Metrics")
    print("=" * 50)
    
    try:
        performance = get_performance_summary()
        
        if performance.total_conversations == 0:
            print("No conversations recorded yet.")
            print("Run some calls or simulations to see metrics.")
            return
        
        print(f"Total Conversations: {performance.total_conversations}")
        print(f"Success Rate: {performance.success_rate:.1%}")
        print(f"Meeting Rate: {performance.meeting_rate:.1%}")
        print(f"Average Quality Score: {performance.quality_score_average:.1f}/10")
        print(f"Error Rate: {performance.error_rate:.1%}")
        
        print("\nOutcome Distribution:")
        for outcome, count in performance.common_outcomes.items():
            percentage = count / performance.total_conversations * 100
            print(f"  {outcome}: {count} ({percentage:.1f}%)")
            
    except Exception as e:
        print(f"Error getting metrics: {e}")


def main():
    """Main evaluation script"""
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_evaluation_demo()
    else:
        show_evaluation_metrics()


if __name__ == "__main__":
    main()
