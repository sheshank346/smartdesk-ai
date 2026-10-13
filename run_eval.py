import itertools
import time
from agent import handle_query

def run_evaluation():
    print("Initializing SmartDesk AI Deterministic Evaluation Harness...")
    
    actions = ["What is the status of", "Please check", "Can you look up", "Where is", "Check status for"]
    ticket_ids = [f"TCK-{i:04d}" for i in range(1, 6)]
    fillers = ["", " please!", " thanks.", " urgent!!"]

    generated_ticket_tests = list(itertools.product(actions, ticket_ids, fillers))
    total_cases = len(generated_ticket_tests)
    
    print(f"Total Test Cases Loaded: {total_cases}\nRunning Evaluation...")

    passed = 0
    failed = 0
    start_time = time.time()

    for idx, (action, ticket_id, filler) in enumerate(generated_ticket_tests, 1):
        query = f"{action} {ticket_id}{filler}"
        try:
            result = handle_query(query)
            if result is not None and "action_taken" in result:
                action_taken = result.get("action_taken")
                if action_taken in ["tool_call: check_ticket_status", "rag_retrieval"]:
                    passed += 1
                else:
                    failed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1

    duration = time.time() - start_time
    pass_percentage = (passed / total_cases) * 100

    print("\n" + "="*50)
    print("       SMARTDESK AI - EVALUATION HARNESS REPORT       ")
    print("="*50)
    print(f" Total Test Cases Evaluated : {total_cases}")
    print(f" Passed Successfully        : {passed}")
    print(f" Failed                     : {failed}")
    print(f" Pass Rate                  : {pass_percentage:.2f}%")
    print(f" Total Execution Time       : {duration:.2f} seconds")
    print("="*50)

if __name__ == "__main__":
    run_evaluation()
