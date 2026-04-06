"""
SupportAI-Env — Inference Script for OpenEnv Validation
This script demonstrates how to interact with the environment via API endpoints.
"""

import requests
import json
import time

BASE_URL = "http://localhost:7860"

def run_inference():
    """Run a sample inference session through the API."""
    print("=" * 60)
    print("SupportAI-Env Inference Script")
    print("=" * 60)
    
    try:
        # Step 1: Reset environment
        print("\n[1] Resetting environment...")
        reset_response = requests.post(f"{BASE_URL}/reset", json={})
        reset_data = reset_response.json()
        
        session_id = reset_data.get("session_id")
        task = reset_data.get("task")
        observation = reset_data.get("observation", {})
        
        print(f"✓ Session ID: {session_id}")
        print(f"✓ Task: {task}")
        print(f"✓ Initial State: {observation.get('current_state')}")
        print(f"✓ Customer Message: {observation.get('customer_message')}")
        print(f"✓ Intent: {observation.get('intent')}")
        print(f"✓ Sentiment: {observation.get('sentiment')}")
        
        # Step 2: Send first action
        print("\n[2] Sending action: ask_details...")
        step_payload = {
            "session_id": session_id,
            "action_type": "ask_details",
            "content": "Could you please provide your order number?"
        }
        step_response = requests.post(f"{BASE_URL}/step", json=step_payload)
        step_data = step_response.json()
        
        observation = step_data.get("observation", {})
        reward = step_data.get("reward", 0)
        done = step_data.get("done", False)
        
        print(f"✓ Reward: {reward}")
        print(f"✓ Done: {done}")
        print(f"✓ Current State: {observation.get('current_state')}")
        print(f"✓ Step Count: {observation.get('step_count')}")
        
        # Step 3: Send second action if not done
        if not done:
            print("\n[3] Sending action: reply...")
            step_payload = {
                "session_id": session_id,
                "action_type": "reply",
                "content": "I've checked your order status. It's on the way!"
            }
            step_response = requests.post(f"{BASE_URL}/step", json=step_payload)
            step_data = step_response.json()
            
            observation = step_data.get("observation", {})
            reward = step_data.get("reward", 0)
            done = step_data.get("done", False)
            
            print(f"✓ Reward: {reward}")
            print(f"✓ Done: {done}")
            print(f"✓ Current State: {observation.get('current_state')}")
            
            # Check if we have a grade
            if done and "grade" in step_data:
                grade = step_data["grade"]
                print(f"\n[GRADE]")
                print(f"✓ Score: {grade.get('final_score')}")
                print(f"✓ Label: {grade.get('label')}")
                print(f"✓ Assessment: {grade.get('assessment', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("Inference completed successfully!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to server at", BASE_URL)
        print("  Make sure the server is running: python start_server.py")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def run_all_tasks():
    """Run inference on all available tasks."""
    tasks = ["easy", "medium", "hard"]
    
    print("=" * 60)
    print("Running inference on all tasks")
    print("=" * 60)
    
    for task_id in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task_id.upper()}")
        print(f"{'='*60}")
        
        try:
            # Reset with specific task
            reset_response = requests.post(
                f"{BASE_URL}/reset",
                json={"task_id": task_id}
            )
            reset_data = reset_response.json()
            session_id = reset_data.get("session_id")
            
            print(f"Session: {session_id}")
            print(f"Message: {reset_data.get('observation', {}).get('customer_message')}")
            
            # Simple action sequence
            actions = ["ask_details", "reply"]
            
            for i, action_type in enumerate(actions, 1):
                step_payload = {
                    "session_id": session_id,
                    "action_type": action_type,
                    "content": f"Action {i}"
                }
                step_response = requests.post(f"{BASE_URL}/step", json=step_payload)
                step_data = step_response.json()
                
                done = step_data.get("done", False)
                reward = step_data.get("reward", 0)
                
                print(f"  Step {i}: {action_type} | Reward: {reward:.2f} | Done: {done}")
                
                if done:
                    if "grade" in step_data:
                        grade = step_data["grade"]
                        print(f"  Grade: {grade.get('final_score')} ({grade.get('label')})")
                    break
            
            time.sleep(0.5)  # Brief pause between tasks
            
        except Exception as e:
            print(f"  Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("All tasks completed!")
    print("=" * 60)

if __name__ == "__main__":
    # Run basic inference
    run_inference()
    
    # Optionally run all tasks
    # Uncomment the line below to test all tasks
    # run_all_tasks()
