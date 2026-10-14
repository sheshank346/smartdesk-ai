SmartDesk AI

A support assistant for a fictional CRM product ("CloudCRM"). It answers product questions from a knowledge base (RAG) and looks up live ticket status through a tool call, deciding between the two for every message. The project is built to be inspected: routing, retrieval, guardrails and evaluation are separate modules, and the evaluation results below include the failures.

Live demo: https://smartdesk-ai-2emjgcwyos5bug3d7vgfkj.streamlit.app (The backend may be slow on the first request if it has been idle.)

Contents
Example interactions
How it works
Design decisions
Guardrails
Evaluation
Known limitations
Planned work
API reference
Configuration
Run it locally
Testing
Deployment
Project structure
Troubleshooting
Example interactions

Taken from the evaluation report (llama3.2:3b, local).

User message	Action taken	Answer
What are the pricing plans?	rag_retrieval	Lists Starter (999 rupees/user/month), Professional (2499) and Enterprise (custom) with what each includes
Does CloudCRM support single sign-on?	rag_retrieval	Yes, via SAML, on the Enterprise plan
What's the status of TCK-1004?	tool_call: check_ticket_status	The ticket is "Open"
Any update on ticket TCK-1009?	tool_call: check_ticket_status	"In Progress", assigned to Support Engineer - Meera
What's the status of TCK-9999?	tool_call: check_ticket_status	Says it couldn't find that ticket and asks the user to double-check the number

Follow-ups work because recent turns are passed along: after asking about TCK-1004, "any update on it?" resolves to the same ticket.

How it works
user message
    |
    v
[guard]    length cap, prompt-injection screen, secret redaction
    |
    v
[route]    LLM picks "ticket_status" or "faq"; a keyword/regex fallback
    |      takes over if the LLM output can't be parsed
    |
    +-- ticket_status --> tools.check_ticket_status()   (mock CRM data)
    |
    +-- faq ------------> ChromaDB top-3 chunks --> LLM answers from them
    |
    v
[guard]    block prompt leakage, redact secrets, never return an empty answer
    |
    v
answer + action taken + sources
Guard. The message is length-checked, normalised, screened for prompt-injection patterns and stripped of secret-shaped strings. The client-supplied conversation history is cleaned the same way.
Route. The LLM is asked for a JSON decision. If the output is not valid JSON, or names a ticket ID that is not in the conversation, a deterministic keyword and regex check decides instead.
Act. Ticket lookups call tools.check_ticket_status(). FAQ questions retrieve the top 3 chunks from ChromaDB.
Respond. The LLM writes the final answer from the tool result or the retrieved chunks, instructed to answer only from that context.
Guard. The answer is checked for prompt leakage and secrets before it is returned.
Failure handling
Situation	Behaviour
Router returns invalid JSON	Falls back to keyword/regex routing
Router names a ticket ID not in the conversation	Ignored; fallback routing is used
Routing raises unexpectedly	Treated as an FAQ question
LLM unreachable during a ticket lookup	Returns the raw ticket fields, labelled as such
LLM unreachable during an FAQ answer	Returns an apology with the error; the retrieved chunks are still returned as sources
Vector store query fails	Returns a "couldn't search the knowledge base" message with the support address
Ollama not running / Groq key missing	A specific, actionable error message (see Troubleshooting)
Design decisions

LLM routing with a deterministic fallback. An LLM can read intent flexibly ("any update on it?"), but a 3B model sometimes returns malformed JSON. The fallback means a parsing failure degrades to slightly less flexible routing instead of an error.

The tool is called with a validated ID. A model-proposed ticket ID goes to a backend function. Requiring it to be well-formed and present in the conversation prevents the model from inventing or being steered to an arbitrary ID.

Two LLM backends behind one function. call_llm() is the only place that knows about providers. Ollama runs locally with no API cost; Groq runs the hosted demo, which has no capacity for a local model. The agent logic is identical for both.

ChromaDB's default embeddings. Keeps install size and deployment time small. The cost is that retrieval quality is not tuned; there is no evaluation of alternative embedding models yet.

One chunk per FAQ section. ingest.py splits product_faq.md on ## headings, so each chunk is a self-contained topic and the heading travels with the text. This makes it easy to check whether the right section was retrieved.

Untrusted text is tagged. User text and history are wrapped in <user_message> and <conversation> tags, and the prompts say to treat them as data. This is a mitigation, not a guarantee, which is why the input screening exists too.

Guardrails

Implemented in guardrails.py and called from agent.handle_query. All checks are deterministic and add no dependencies or extra LLM calls.

Layer	What it does
Input	Rejects messages over 1000 characters, normalises unicode (full-width and zero-width tricks), blocks common prompt-injection patterns, redacts API-key-shaped strings and card-length numbers
History	Drops malformed turns and turns containing injection patterns, caps turn length
Routing	Accepts a ticket ID from the LLM only if it is valid and present in the conversation
Prompts	User text and history are wrapped in tags the model is told to treat as data
Output	Replaces answers that echo the system prompt, redacts secrets, replaces empty answers
Out of scope	Optional: refuses when the closest retrieved chunk is too far away. Off by default; set RETRIEVAL_MAX_DISTANCE after calibrating on your own data

Every response includes a guardrail_flags list in the Python result (for example injection:override_instructions or input_redacted) so blocked and modified requests can be audited.

Limits. Pattern matching catches common attacks, not paraphrased or obfuscated ones. The guardrails are covered by 22 unit tests with a stubbed LLM and vector store, but have not yet been measured against the real models, and their false-positive rate on real traffic is unknown.

Evaluation

eval.py runs a fixed set of queries through agent.handle_query and scores three things:

Routing accuracy: exact comparison of the action taken against the expected action. No LLM is involved in this score.
Relevance: fraction of expected keywords found in the answer (case-insensitive). Cheap and deterministic.
Faithfulness: an LLM-as-judge score from 1 to 5 for whether a RAG answer is supported by the retrieved context. Not applicable to tool answers.
Results (8 cases, llama3.2:3b as agent and judge)
Metric	Result
Routing accuracy	8 / 8
Mean relevance	73%
Mean faithfulness (5 RAG cases)	3.4 / 5
Mean latency (local)	23.4 s per query
Query	Expected	Routed	Relevance	Faithfulness
What are the pricing plans?	faq	rag	100%	5
Does CloudCRM support single sign-on?	faq	rag	100%	5
Can I get a refund if I cancel my subscription?	faq	rag	67%	1
What is the API rate limit on the Professional plan?	faq	rag	100%	1
Does CloudCRM have a Zapier integration?	faq	rag	50%	5
What's the status of TCK-1004?	ticket	tool	33%	n/a
Any update on ticket TCK-1009?	ticket	tool	33%	n/a
What's the status of TCK-9999?	ticket	tool	100%	n/a
What these results show, and what they don't
Eight cases is a small set, and the router was tuned against these same cases. 8/8 does not show that routing generalises to messier queries.
The refund answer is a real hallucination. It states that refunds are "processed within 30 days of cancellation", which is not in the knowledge base. The judge caught it (1/5).
Keyword relevance can't detect wrong claims. The API rate-limit answer received 100% relevance because the expected keywords appear in it, while the judge scored it 1/5 for misstating how the plans compare.
Low relevance on tool cases is a test-design issue. Expected keywords such as "sso", "mobile" and "crash" do not appear in the short status answers, even though routing was correct and the tool returned a status. The keyword lists need rewriting.
The judge is a small local model. Its scores are noisy and have not been checked against human labels.
Known limitations
Small test set with no held-out split (see above).
Faithfulness depends on a weak LLM judge, and relevance depends on keywords.
Ticket data is mock data in data/tickets.json; there is no real CRM integration.
Conversation history is capped by turn count (4 exchanges), not by tokens.
The API has no authentication or rate limiting, and CORS allows all origins. That is acceptable for a demo, not for production.
Only one retrieval configuration (top 3, default embeddings) has been tried.
Planned work
Expand the test set to cover out-of-scope, ambiguous, multi-intent and adversarial queries, with a held-out portion that is never tuned against.
Add non-LLM checks: whether the right FAQ section was retrieved, and whether numbers in an answer appear in the retrieved context (this would have caught the refund answer).
Rewrite the keyword lists so tool-answer relevance reflects correctness.
Run the Agent Red-Teamer attack suite against this agent as regression tests.
Calibrate RETRIEVAL_MAX_DISTANCE and measure the guardrails' false-positive rate.
Return guardrail_flags from the API.
API reference

Interactive docs are served at /docs when the API is running.

GET /health
json
{"status": "ok"}
POST /chat

Request:

json
{
  "query": "What's the status of TCK-1004?",
  "history": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello! How can I help?"}
  ]
}

history is optional. Roles must be user or assistant.

Response:

json
{
  "answer": "The current status of TCK-1004 is \"Open\".",
  "action_taken": "tool_call: check_ticket_status",
  "sources": []
}

action_taken is one of rag_retrieval, tool_call: check_ticket_status, rag_retrieval (no context found), rag_retrieval (LLM error), input_validation, guardrail: input_blocked or guardrail: out_of_scope. sources holds the retrieved FAQ chunks for FAQ answers.

bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the pricing plans?"}'
Configuration
Variable	Purpose	Default
LLM_PROVIDER	ollama or groq	ollama
GROQ_API_KEY	Required when LLM_PROVIDER=groq	none
RETRIEVAL_MAX_DISTANCE	Enables the out-of-scope check	off

Fixed in agent.py: Ollama model llama3.2:3b, Groq model openai/gpt-oss-20b, top-k of 3, and 4 history turns. Request timeouts are 120 s for Ollama and 60 s for Groq.

Run it locally

Prerequisites: Python 3.10+, and Ollama running with the model pulled (ollama pull llama3.2:3b), or a Groq API key.

bash
pip install -r requirements.txt

python ingest.py                      # build the vector store (once)
uvicorn api:app --reload --port 8000  # API at localhost:8000, docs at /docs
streamlit run app.py                  # UI at localhost:8501

To use Groq instead of Ollama:

bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=your_key_here     # on Windows PowerShell: $env:GROQ_API_KEY="..."

Things to try: "What are the pricing plans?", "Does CloudCRM support SSO?", "What's the status of TCK-1004?", then "any update on it?".

Testing
bash
python eval.py                         # evaluation; writes eval_report.json
python -m unittest test_guardrails -v  # guardrail tests, no LLM needed

test_guardrails.py has two parts. The first tests guardrails.py directly: attack strings that must be blocked, normal questions that must not be, length limits, redaction, history sanitising, ticket-ID validation, and output checks. The second imports agent.py with the LLM, ChromaDB and tools stubbed out, to confirm the guardrails are actually wired in: an injection never reaches the LLM, an invented ticket ID never reaches the tool, a leaked prompt is replaced, and the fallback routing still works.

Deployment
Frontend: Streamlit Community Cloud.
Backend: FastAPI on Render, with LLM_PROVIDER=groq and GROQ_API_KEY set as environment variables.
Vector store: chroma_db/ is generated by ingest.py, so it has to be built in the deployed environment as well.
Project structure
smartdesk-ai/
├── data/
│   ├── product_faq.md       knowledge base
│   └── tickets.json         mock ticket data
├── ingest.py                chunk and embed the FAQ into ChromaDB
├── tools.py                 ticket lookup tool
├── guardrails.py            input, history, routing and output checks
├── agent.py                 guard -> route -> act -> respond -> guard
├── api.py                   FastAPI server
├── app.py                   Streamlit UI
├── eval.py                  evaluation harness
├── test_guardrails.py       guardrail unit tests
└── requirements.txt
Troubleshooting
Symptom	Cause and fix
"Can't reach Ollama"	Start the Ollama app or run ollama serve, and make sure llama3.2:3b is pulled
"GROQ_API_KEY is not set"	LLM_PROVIDER is groq but the key is missing from the environment
Crash on startup about a missing collection	Run python ingest.py first to build chroma_db/
"The LLM took too long to respond"	Local models can be slow on first load; retry, or switch to Groq
Every message answered with a refusal	The input guardrail blocked it; check the guardrail_flags in the result
