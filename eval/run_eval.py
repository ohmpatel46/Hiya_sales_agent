import json
import sys
import os
from typing import Dict, Any, List
from agent.orchestrator import handle_turn, clear_session
from agent.schemas import Lead


def load_stories(stories_file: str = "eval/stories.json") -> List[Dict[str, Any]]:
    """Load test stories from JSON file"""
    try:
        with open(stories_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Stories file {stories_file} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {stories_file}: {e}")
        sys.exit(1)


def run_story(story: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single story and return results"""
    story_name = story["name"]
    lead_data = story["lead"]
    turns = story["turns"]
    expected = story["expect"]
    
    print(f"\n📖 Running story: {story_name}")
    print(f"   Lead: {lead_data['name']} ({lead_data['company']})")
    
    # Create lead object
    lead = Lead(**lead_data)
    
    # Generate session ID
    session_id = f"eval_{story_name}"
    
    # Clear any existing session
    clear_session(session_id)
    
    # Track results
    results = {
        "scheduled": False,
        "followup": False,
        "info_requested": False,
        "rejected": False,
        "errors": []
    }
    
    try:
        # Run conversation turns
        for i, turn in enumerate(turns):
            user_input = turn["user"]
            print(f"   Turn {i+1}: User says '{user_input}'")
            
            # Handle the turn
            response = handle_turn(session_id, lead, user_input)
            
            # Check tool results for outcomes
            for tool_result in response.get("tool_results", []):
                if tool_result.get("created") and "calendar" in str(tool_result):
                    results["scheduled"] = True
                    print(f"   ✅ Calendar event created: {tool_result.get('htmlLink', 'N/A')}")
                
                if tool_result.get("logged"):
                    if "followup" in str(tool_result):
                        results["followup"] = True
                        print(f"   ✅ Follow-up logged")
                    elif "requested_info" in str(tool_result):
                        results["info_requested"] = True
                        print(f"   ✅ Info request logged")
                    elif "rejected" in str(tool_result):
                        results["rejected"] = True
                        print(f"   ✅ Rejection logged")
            
            # Check if conversation ended
            if response.get("final"):
                print(f"   🏁 Conversation ended")
                break
            
            print(f"   Agent: {response['reply'][:100]}...")
    
    except Exception as e:
        error_msg = f"Error in story {story_name}: {e}"
        print(f"   ❌ {error_msg}")
        results["errors"].append(error_msg)
    
    # Evaluate results
    success = True
    for key, expected_value in expected.items():
        if results[key] != expected_value:
            success = False
            print(f"   ❌ Expected {key}={expected_value}, got {results[key]}")
        else:
            print(f"   ✅ {key}={expected_value}")
    
    return {
        "story_name": story_name,
        "success": success,
        "results": results,
        "expected": expected
    }


def main():
    """Run evaluation harness"""
    print("🚀 Starting Hiya Sales Agent Evaluation")
    print("=" * 50)
    
    # Load stories
    stories = load_stories()
    print(f"Loaded {len(stories)} test stories")
    
    # Run all stories
    all_results = []
    for story in stories:
        result = run_story(story)
        all_results.append(result)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 EVALUATION SUMMARY")
    print("=" * 50)
    
    successful = sum(1 for r in all_results if r["success"])
    total = len(all_results)
    
    print(f"Stories passed: {successful}/{total}")
    print(f"Success rate: {successful/total*100:.1f}%")
    
    if successful == total:
        print("🎉 All stories passed!")
    else:
        print("⚠️  Some stories failed:")
        for result in all_results:
            if not result["success"]:
                print(f"   - {result['story_name']}")
    
    # Detailed results
    print("\n📋 DETAILED RESULTS:")
    for result in all_results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} {result['story_name']}")
        
        if result["errors"]:
            for error in result["errors"]:
                print(f"     Error: {error}")


if __name__ == "__main__":
    main()
