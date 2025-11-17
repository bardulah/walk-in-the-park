# Google ADK Research Findings

## Installation Success ✓

```bash
pip install google-adk
```

**Status:** Successfully installed version 1.18.0

## API Discovery

### Correct Imports

```python
from google.adk import Runner  # Not google.adk.runner
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types
```

### Key Findings

1. **Async-First API**
   - `SessionService.create_session()` is async (must await)
   - `SessionService.get_session()` is async
   - Need async/await throughout

2. **LlmAgent Parameters** (from docs)
   - `name`: Required string identifier
   - `model`: Required (e.g., "gemini-2.0-flash-exp")
   - `description`: Optional summary for routing
   - `instruction`: Guidance text defining behavior
   - `tools`: Optional list of callable functions
   - `output_key`: Stores result in session state
   - `sub_agents`: List of child agents

3. **ParallelAgent Usage** (from docs)
   ```python
   parallel_agent = ParallelAgent(
       name="ParallelAnalysts",
       sub_agents=[agent1, agent2, agent3],
       description="Runs agents in parallel"
   )
   ```
   - Executes all sub-agents concurrently
   - Each has independent execution branch
   - Results stored in session state via `output_key`

4. **Session Management**
   - Create session with initial state
   - Session has `id`, `state`, `events`, `app_name`, `user_id`
   - Agents read/write to `session.state`

5. **Runner Execution**
   ```python
   runner = Runner(
       agent=root_agent,
       app_name="my_app",
       session_service=session_service
   )

   events = runner.run(
       user_id="user_id",
       session_id="session_id",
       new_message=content
   )
   ```

## Implementation Challenges

### Challenge 1: Async Methods
**Problem:** Session methods are async but we have sync API
**Solution:** Make `run_analysis()` async and provide sync wrapper with `asyncio.run()`

### Challenge 2: Content Format
**Problem:** Need to create proper `types.Content` objects
**Solution:**
```python
from google.genai import types

user_message = types.Content(
    role='user',
    parts=[types.Part(text="query text")]
)
```

### Challenge 3: Event Streaming
**Problem:** Runner returns generator of events, need to collect results
**Solution:** Iterate through events and extract final state from session

## Architecture Pattern

Based on research, the proper ADK pattern for our trading system:

```
┌─────────────────────────────────────┐
│  TradingCoordinator (LlmAgent)      │
│  - Model: gemini-2.0-flash-exp      │
│  - output_key: "final_recs"         │
│                                     │
│  Sub-agents:                        │
│  ┌─────────────────────────────┐   │
│  │ ParallelAnalysts            │   │
│  │ (ParallelAgent)             │   │
│  │                             │   │
│  │  Sub-agents (run in ||):    │   │
│  │  ├─ PortfolioAnalyst        │   │
│  │  │  output_key: "portfolio"  │   │
│  │  ├─ MarketAnalyst           │   │
│  │  │  output_key: "market"     │   │
│  │  └─ NewsMonitor             │   │
│  │     output_key: "news"       │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Execution Flow

1. **Initialize session** with portfolio/market/news data in state
2. **Create user message** asking for analysis
3. **Run coordinator via Runner**
   - Coordinator delegates to ParallelAnalysts
   - ParallelAnalysts runs 3 agents concurrently
   - Each writes results to session state
4. **Coordinator synthesizes** results from state into recommendations
5. **Extract final result** from session state

## Code Status

### What Works ✓
- Google ADK package installed
- Imports successful
- Agent creation patterns identified
- Parallel execution pattern understood

### What Needs Fixing
- [x] Async handling for session methods
- [x] Event streaming and result extraction
- [ ] Test with real Gemini API calls
- [ ] Verify parallel execution actually works
- [ ] Error handling for API failures

## Next Steps

1. Fix async/await handling
2. Test end-to-end with mock data
3. Test with real Gemini API (if enabled)
4. Compare performance with orchestrator_v2.py
5. Document parallel vs sequential timing

## References

- Official docs: https://google.github.io/adk-docs/
- GitHub repo: https://github.com/google/adk-python
- Samples: https://github.com/google/adk-samples
- Package: https://pypi.org/project/google-adk/
