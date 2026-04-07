"""
SupportAI-Env — Inference Script for OpenEnv Validation
This script demonstrates how to interact with the environment via API endpoints.
Outputs structured logs in the format required by OpenEnv validator.
"""

import requests
import sys

BASE_URL = "http://localhost:7860"

def run_inference():
    """Run a sample inference session through the API with structured output."""
    
    try:
        # Step 1: Reset environment
        print("[START] task=easy", flush=True)
        
        reset_response = requests.post(f"{BASE_URL}/reset", json={})
        reset_data = reset_response.json()
        
        session_id = reset_data.get("session_id")
        task = reset_data.get("task", "easy")
        
        # Step 2: Send first action
        step_count = 1
        step_payload = {
            "session_id": session_id,
            "action_type": "ask_details",
            "content": "Could you please provide your order number?"
        }
        step_response = requests.post(f"{BASE_URL}/step", json=step_payload)
        step_data = step_response.json()
        
        reward = step_data.get("reward", 0)
        done = step_data.get("done", False)
        
        print(f"[STEP] step={step_count} reward={reward:.2f}", flush=True)
        
        # Step 3: Send second action if not done
        if not done:
            step_count += 1
            step_payload = {
                "session_id": session_id,
                "action_type": "reply",
                "content": "I've checked your order status. It's on the way!"
            }
            step_response = requests.post(f"{BASE_URL}/step", json=step_payload)
            step_data = step_response.json()
            
            reward = step_data.get("reward", 0)
            done = step_data.get("done", False)
            
            print(f"[STEP] step={step_count} reward={reward:.2f}", flush=True)
        
        # Get final score
        final_score = 0.0
        if done and "grade" in step_data:
            grade = step_data["grade"]
            final_score = grade.get("final_score", 0.0)
        
        print(f"[END] task={task} score={final_score:.2f} steps={step_count}", flush=True)
        
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to server", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {str(e)}", flush=True)
        sys.exit(1)

def run_all_tasks():
    """Run inference on all available tasks with structured output."""
    tasks = ["easy", "medium", "hard"]
    
    for task_id in tasks:
        try:
            print(f"[START] task={task_id}", flush=True)
            
            # Reset with specific task
            reset_response = requests.post(
                f"{BASE_URL}/reset",
                json={"task_id": task_id}
            )
            reset_data = reset_response.json()
            session_id = reset_data.get("session_id")
            
            # Simple action sequence
            actions = ["ask_details", "reply"]
            step_count = 0
            final_score = 0.0
            
            for action_type in actions:
                step_count += 1
                step_payload = {
                    "session_id": session_id,
                    "action_type": action_type,
                    "content": f"Action {step_count}"
                }
                step_response = requests.post(f"{BASE_URL}/step", json=step_payload)
                step_data = step_response.json()
                
                done = step_data.get("done", False)
                reward = step_data.get("reward", 0)
                
                print(f"[STEP] step={step_count} reward={reward:.2f}", flush=True)
                
                if done:
                    if "grade" in step_data:
                        grade = step_data["grade"]
                        final_score = grade.get("final_score", 0.0)
                    break
            
            print(f"[END] task={task_id} score={final_score:.2f} steps={step_count}", flush=True)
            
        except Exception as e:
            print(f"[ERROR] task={task_id} error={str(e)}", flush=True)

if __name__ == "__main__":
    # Run basic inference with structured output
    run_inference()
    
    # Optionally run all tasks
    # Uncomment the line below to test all tasks
    # run_all_tasks()
