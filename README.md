# Coding Agent + Metasearch Engine + LLM

Goal:  
A local, privacy-respecting AI workflow for coding and planning using:

- Coding Agent (One of the following)
  - [Kilo](https://github.com/Kilo-Org/kilocode)
  - [Roo Code](https://github.com/RooCodeInc/Roo-Code)
  - [Cline](https://github.com/cline/cline)
- LLM (One of the following)
  - [Ollama](https://github.com/ollama/ollama)
  - [Qwen Code](https://github.com/QwenLM/qwen-code)
- Metasearch Engine
  - [SearxNG](https://github.com/searxng/searxng)

All fully local, no cloud APIs required.

![Workflow Diagram](/docs/assets/workflow.png)
---

## Repository Layout

```
kilo-local-ai/
├── scripts/
│   ├── start_agents.py
│   └── query_searxng.py
├── docker/
│   └── searxng/
│       ├── docker-compose.yml
│       └── settings.yml
├── .sample.env
├── .env                # not committed
├── README.md
```

---

## Prerequisites

- VS Code (latest)
- Python 3.11+
- Docker Desktop
- Ollama
- Internet connection (for first model pull)

Install Python dependencies:

    python -m pip install requests

---

## 1. SearxNG Setup

1. Copy `.sample.env` → `.env` and fill in a random 32-character secret:
    ```
    SEARX_SECRET_KEY=your_random_32_char_secret_here
    ```
---

## 2. LLM Setup (Local or Hosted)

You have **two options** for the coding agent LLM:

---

### 2a. Local LLM: Ollama

#### One-Time Setup

1. Pull the recommended model:

        ollama pull qwen3:4b

#### Setup (everytime)

1. Start Ollama & SearXNG (if not already running):

        python scripts/start_agents.py


- The script starts Ollama and SearxNG (Docker)  
- Health summary will indicate both are running  

**Notes:**

- Ollama is fully local, private, and no cloud API is needed  
- Memory usage scales with model size and context  
- Default context: 8192, can increase up to 32000 (adjust for RAM)

---

### 2b. Hosted LLM: Qwen Code (Free, OAuth)

GitHub: https://github.com/QwenLM/qwen-code

#### One-Time Setup

1. Install Qwen Code CLI globally:

        npm install -g @qwen-code/cli
2. Start the CLI interactively:

        qwen
3. Authenticate via OAuth inside the CLI session:
        
        /auth # start OAuth login

   - A browser will open  
   - Log in with your free **qwen.ai account**  
   - Credentials are cached locally  

✅ Only needs to be done **once**.

#### Setup (everytime)

1. Start SearXNG (if not already running):

        python .\scripts\start_searxng_agents.py

---

## 3. Coding Agent Setup

1. Open VS Code  
2. Install `Kilo` (or Other Coding Agent) extension
   1. `Cline`
   2. `Code Roo`
3. Command Palette (`Ctrl+Shift+P`) -> `Kilo: Select Provider`
   1. Ollama (local)
      - API Provider: Ollama  
      - Base URL: http://localhost:11434 
      - Model: qwen3:4b (or other model downloaded)
      - Context size: 32000 (adjust carefully for RAM)
   2. Qwen Code
      - API Provider: Qwen Code  
      - Base URL: NA
      - Model: `qwen3-coder-plus` (or `qwen3-coder-flash`)   
      - Context size: NA
      - Usage: Prompt Kilo normally — free tier ~2,000 requests/day, 60 requests/min.

---


## 4. Using SearXNG w/ Coding Agent - Context Prompt

### [searxng_script_prompt.md](/agent-prompts/searxng_script_prompt.md/)
- Search using SearXNG and use results in planning or coding
- `Copy/Paste` into Coding Agent's `Task/Prompt`
    - Provides context that should allow agent to search online for information
---

## 5. Planned Features

### 5.1 VS Code Extension (Auto-Start Agents)

Status: Planned / TODO

- Automatically run `start_agents.py` when VS Code starts  
- Use a lock file for safety  
- Optional auto-stop on exit  

### 5.2 MCP Server Support for SearxNG

Status: Planned / TODO

- Use an MCP (Model Context Protocol) server to expose SearxNG as a native tool in Kilo Code  
- Allows the agent to call the search tool directly, with structured JSON results  
- Will replace or augment the current `query_searxng.py` script for more robust tool integration  
- Configuration will live in `.kilocode/mcp.json` or global MCP settings

---

## 6. Kilo VS Code

> Did you know you can have Kilo Code on the right side of VS Code? Gives you easy access to Kilo Code and your file browser at the same time. 
>
>Just right click on the Kilo Code icon and say "Move to" --> "Secondary side bar"