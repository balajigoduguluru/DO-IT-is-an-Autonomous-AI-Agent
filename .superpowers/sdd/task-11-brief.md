### Task 11: Clean Up Old Files and Styles

**Files:**
- Delete: `frontend/src/api/client.ts` (replaced by api.ts)
- Delete: `frontend/src/hooks/useWebSocket.ts` (replaced by websocket.ts)
- Delete: `frontend/src/components/DAGView.tsx` (folded into DevModePanel)
- Delete: `frontend/src/components/ExecutionLedger.tsx` (folded into DevModePanel)
- Delete: `frontend/src/components/ApprovalGate.tsx` (replaced by ApprovalDialog)
- Delete: `frontend/src/components/RiskPanel.tsx` (folded into DevModePanel)
- Delete: `frontend/src/components/LiveTimeline.tsx` (replaced by ThinkingPanel + ProgressBar)
- Modify: `frontend/src/styles/globals.css` (strip old dev-oriented styles)
- Modify: `frontend/index.html` (update title and meta)

- [ ] **Step 1: Remove unused dependencies**

```bash
cd C:/Users/balaj/OneDrive/Documents/Projects/Agentic\ AI/frontend
npm uninstall reactflow
```

- [ ] **Step 2: Clean up globals.css**

Write `frontend/src/styles/globals.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: 'Inter', sans-serif;
  background: #F9FAFB;
  color: #1F2937;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  box-sizing: border-box;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: #f1f1f1;
}
::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
* {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #f1f1f1;
}
```

- [ ] **Step 3: Update index.html**

Write `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Agentic AI</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>" />
    <meta name="description" content="Agentic AI — Describe your goal, and AI handles the rest." />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Delete old files**

```bash
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/api/client.ts"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/hooks/useWebSocket.ts"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/DAGView.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/ExecutionLedger.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/ApprovalGate.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/RiskPanel.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/LiveTimeline.tsx"
```

---

