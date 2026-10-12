# SmartDesk AI — Setup (do this before anything else)

## 1. Install Python (if not already installed)
Check: open terminal/command prompt and run:
    python --version
Need 3.10 or higher. If not installed, get it from https://www.python.org/downloads/

## 2. Install Ollama (runs the free AI model locally — no API key, no cost)
Download from: https://ollama.com/download
Pick your OS (Windows/Mac/Linux), install it like a normal app.

## 3. Pull the model (this downloads it once, ~2GB, needs internet)
Open terminal and run:
    ollama pull llama3.2:3b

This model is small enough to run smoothly on 8GB RAM. (If it feels slow/laggy,
close Chrome tabs and other heavy apps while running the demo.)

## 4. Keep Ollama running
Ollama runs a background server automatically after install. Verify with:
    ollama list
You should see llama3.2:3b listed.

## 5. Install Python packages
Navigate into the smartdesk-ai folder in terminal, then run:
    pip install -r requirements.txt

That's it — once this is done, message me and we'll run the project.
