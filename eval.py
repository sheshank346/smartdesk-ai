"""
eval.py
Evaluation harness for SmartDesk AI.

Runs a fixed set of test queries against the agent and scores the results on
three things a real ML/AI team would actually care about before shipping:

  1. ROUTING ACCURACY  -- did the agent choose the right action (RAG vs tool
                           call)? Measured exactly (not by LLM judgment),
                           since we know the correct answer for each test case.
  2. RELEVANCE          -- does the answer actually contain the key facts we
                           expect? Checked via keyword matching (fast, cheap,
                           deterministic -- no extra LLM calls needed).
  3. FAITHFULNESS        -- for RAG answers, is the answer actually grounded in
                           the retrieved context, or did the model hallucinate
                           something not in the source material? Scored using
                           an LLM-as-judge prompt (the same LLM backend the
                           agent uses), since this is a semantic judgment that
                           keyword matching can't capture well.

Run with:
    python eval.py

Outputs a summary table to the console and a detailed JSON report to
eval_report.json.
"""

import json
import time
import statistics

import agent

# --- Test set -----------------------------------------------------------
# Each case has: a query, the expected routing action, and (for FAQ cases)
# keywords that should appear somewhere in a correct answer.
TEST_CASES = [
    {
        "query": "What are the pricing plans?",
        "expected_action": "faq",
        "expected_keywords": ["999", "2499", "starter", "professional", "enterprise"],
    },
    {
        "query": "Does CloudCRM support single sign-on?",
        "expected_action": "faq",
        "expected_keywords": ["sso", "saml", "enterprise"],
    },
    {
        "query": "Can I get a refund if I cancel my subscription?",
        "expected_action": "faq",
        "expected_keywords": ["cancel", "billing", "free tier"],
    },
    {
        "query": "What is the API rate limit on the Professional plan?",
        "expected_action": "faq",
        "expected_keywords": ["1000", "professional"],
    },
    {
        "query": "Does CloudCRM have a Zapier integration?",
        "expected_action": "faq",
        "expected_keywords": ["zapier", "webhook"],
    },
    {
        "query": "What's the status of TCK-1004?",
        "expected_action": "ticket_status",
        "expected_keywords": ["open", "sso", "meera"],
    },
    {
        "query": "Any update on ticket TCK-1009?",
        "expected_action": "ticket_status",
        "expected_keywords": ["in progress", "mobile", "crash"],
    },
    {
        "query": "What's the status of TCK-9999?",
        "expected_action": "ticket_status",
        "expected_keywords": ["couldn't find", "double check"],
    },
]

FAITHFULNESS_PROMPT = """You are evaluating an AI support assistant's answer for
faithfulness -- whether the answer only makes claims that are actually
supported by the given context, without adding invented facts.

Context the assistant had access to:
{context}

Assistant's answer:
{answer}

Score faithfulness from 1 to 5:
5 = fully grounded, every claim traceable to the context
3 = mostly grounded, minor unsupported details
1 = contains claims not supported by (or contradicting) the context

Respond with ONLY a JSON object: {{"score": <1-5>, "reason": "<one sentence>"}}
"""


def score_relevance(answer: str, expected_keywords: list) -> float:
    """Fraction of expected keywords found in the answer (case-insensitive)."""
    if not expected_keywords:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords)


def score_faithfulness(answer: str, context_chunks: list) -> dict:
    """LLM-as-judge faithfulness score for RAG answers. Returns None-ish
    defaults if context is empty (e.g. tool-call answers) since faithfulness
    to *retrieved documents* doesn't apply there."""
    if not context_chunks:
        return {"score": None, "reason": "N/A (not a RAG answer)"}

    context_text = "\n\n".join(context_chunks)
    prompt = FAITHFULNESS_PROMPT.format(context=context_text, answer=answer)
    try:
        raw = agent.call_llm(prompt, temperature=0.0)
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return {"score": parsed.get("score"), "reason": parsed.get("reason", "")}
    except Exception as e:
        return {"score": None, "reason": f"judge_error: {e}"}
    return {"score": None, "reason": "could not parse judge response"}


def run_evaluation():
    results = []
    print(f"Running evaluation on {len(TEST_CASES)} test cases...\n")

    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {case['query']}")
        start = time.time()
        try:
            output = agent.handle_query(case["query"])
            error = None
        except Exception as e:
            output = {"answer": "", "action_taken": "error", "sources": []}
            error = str(e)
        latency = time.time() - start

        # Routing accuracy: does action_taken match what we expected?
        actual_action = output["action_taken"]
        routing_correct = case["expected_action"] in actual_action or (
            case["expected_action"] == "faq" and "rag" in actual_action
        )

        relevance = score_relevance(output["answer"], case["expected_keywords"])
        faithfulness = score_faithfulness(output["answer"], output.get("sources", []))

        result = {
            "query": case["query"],
            "expected_action": case["expected_action"],
            "actual_action": actual_action,
            "routing_correct": routing_correct,
            "answer": output["answer"],
            "relevance_score": round(relevance, 2),
            "faithfulness_score": faithfulness["score"],
            "faithfulness_reason": faithfulness["reason"],
            "latency_seconds": round(latency, 2),
            "error": error,
        }
        results.append(result)

        status = "✅" if routing_correct and relevance >= 0.5 else "⚠️"
        print(f"    {status} routing={'OK' if routing_correct else 'WRONG'} "
              f"relevance={relevance:.0%} "
              f"faithfulness={faithfulness['score']} "
              f"latency={latency:.1f}s\n")

    return results


def print_summary(results: list):
    n = len(results)
    routing_acc = sum(1 for r in results if r["routing_correct"]) / n
    avg_relevance = statistics.mean(r["relevance_score"] for r in results)
    faith_scores = [r["faithfulness_score"] for r in results if r["faithfulness_score"] is not None]
    avg_faithfulness = statistics.mean(faith_scores) if faith_scores else None
    avg_latency = statistics.mean(r["latency_seconds"] for r in results)
    errors = sum(1 for r in results if r["error"])

    print("=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Test cases run:        {n}")
    print(f"Routing accuracy:      {routing_acc:.0%}")
    print(f"Avg relevance score:   {avg_relevance:.0%}")
    print(f"Avg faithfulness:      {avg_faithfulness:.2f} / 5" if avg_faithfulness else "Avg faithfulness:      N/A")
    print(f"Avg latency:           {avg_latency:.2f}s")
    print(f"Errors:                {errors}")
    print("=" * 60)


if __name__ == "__main__":
    results = run_evaluation()
    print_summary(results)

    with open("eval_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed report saved to eval_report.json")
