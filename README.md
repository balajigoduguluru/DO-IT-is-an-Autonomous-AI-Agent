<div align="center">
  
  <h1>DO IT : Agentic AI Framework</h1>
  <p>
    <strong>A next-generation, autonomous, multi-agent execution platform.</strong>
  </p>
  
  <p>
    <a href="#vision">The Vision</a> • 
    <a href="#features">Features</a> • 
    <a href="#architecture">Architecture</a> • 
    <a href="#getting-started">Getting Started</a> • 
    <a href="#innovations">Core Innovations</a>
  </p>
</div>

---

## ⚡ The Vision: Beyond Chatbots

Traditional LLMs act as passive conversational chatbots that require constant prompting and cannot execute multi-step goals autonomously. **DO IT** is an autonomous AI agent platform designed to execute complex, multi-step missions from a single user prompt. 

It features an **adaptive execution graph** that mutates at runtime, learns from failures, and never wastes an API call. Coupled with a premium, dynamic React frontend, it brings true agentic autonomy to your browser.

![Dashboard Preview](./frontend/public/screenshots/dashboard.png)
*(Placeholder: Add your actual dashboard screenshot here)*

---

## 🚀 Key Features & The User Experience

*   **Premium Personalization:** The platform greets the user by name upon entry, storing credentials securely in local storage.
*   **Interactive Workspaces:** Features a responsive layout with a Sidebar, Dashboard, live Terminal, and an extensible Goal Input bar supporting attachments.
*   **Bento-Grid Templates:** Quick-start templates allow users to kick off complex workflows (e.g., "Analyze Document", "Optimize Code") with a single click.
*   **🧠 LangGraph State Machine:** Orchestrates autonomous agents through an adaptive execution pipeline—from goal interpretation to parallel task execution.
*   **✨ Premium UI/UX:** Built with React, Vite, and Framer Motion, featuring glassmorphism, dynamic bento-grid templates, and a live reasoning panel that unboxes the AI's "black box."

![Reasoning Panel Preview](./frontend/public/screenshots/terminal.png)
*(Placeholder: Add your actual live terminal/reasoning panel screenshot here)*

---

## 🏗️ System Architecture

The system is split into a robust Python backend and a modern React frontend.

### The Backend Pipeline
The backend utilizes a **four-agent architecture** orchestrated by LangGraph:
1. **Understand Goal:** Parses the user's natural language input and extracts constraints.
2. **Build DAG:** Constructs a Directed Acyclic Graph (DAG) of the tasks required to solve the goal.
3. **Schedule Tasks:** Determines the optimal execution order and parallelizes independent tasks.
4. **Execute & Evaluate:** Executes tools, evaluates the output, and mutates the graph at runtime if a replan is needed.

### The Stack
*   **Frontend:** React 18, TypeScript, Vite, TailwindCSS, Framer Motion, GSAP-inspired templates.
*   **Backend:** Python 3.11+, FastAPI, LangGraph, Uvicorn.
*   **Communication:** REST APIs + Bi-directional WebSockets for live streaming.

---

## 🔬 Core Innovations

The DO IT framework is built on several key innovations that separate it from standard AI applications:

### 1. Extensible Tool Registry
*   **Plug-and-Play Tools:** The agent is connected to a dynamic tool registry, allowing it to search the web, manage budgets, book flights, and analyze files.
*   **Multimodal Capabilities:** Users can upload documents directly into the UI. The backend persists these files and passes them into the agent's execution context for processing.
*   **Dynamic Tool Selection:** The LangGraph state machine dynamically selects the right tools based on the current step of the mission.

### 2. Human-in-the-Loop (HITL) & Risk Prediction
*   **The Risk Predictor:** Before the AI executes a tool, the system analyzes the action for security risks, financial cost, and historical failure rates.
*   **Granular Permissions (RBAC):** Safe, exploratory actions (e.g., Web Search, Lookups) are auto-approved for speed.
*   **Approval Gate:** Destructive or financial actions (e.g., executing code, making payments) pause the execution graph and prompt the user via the UI for explicit approval before proceeding.

### 3. Execution Transparency & Resilience
*   **Live Reasoning Panel:** Users watch the AI "think" in real-time, translated into human-readable phases.
*   **Session Resilience:** WebSocket connections are backed by local storage. If a user refreshes the browser mid-mission, the connection instantly restores without losing data.
*   **Dynamic Execution Graph:** A visual node-edge graph renders the AI's decision tree live.

---

## 🏁 Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python (3.11+)

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/agentic-ai.git
cd agentic-ai

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn src.api.server:app --reload --port 8000
```

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

Visit `http://localhost:5173` in your browser to start your first mission!

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---
<div align="center">
  <b>© DO IT is an Autonomous AI Agent.</b>
</div>
