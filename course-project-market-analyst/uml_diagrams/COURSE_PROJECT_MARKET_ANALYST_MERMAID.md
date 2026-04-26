# Mermaid Діаграми: Course Project Market Analyst

Ці діаграми описують фактичну реалізацію фінального проєкту для перевірки source-level архітектури. У live report `Report Compiler` генерує інші Mermaid artifacts: market entry flow, payback gate, validation timeline, saturation map і pie chart з розподілом оцінок expert critics.

## 1. Загальна Архітектура

```mermaid
flowchart LR
    User["User / Reviewer"] --> UI["React Decision Dashboard"]
    User --> CLI["CLI Fallback"]
    UI --> API["FastAPI Backend"]
    API --> SSE["SSE Event Stream"]
    API --> Graph["LangGraph StateGraph"]
    CLI --> Graph
    Graph --> Analyst["Research Analyst"]
    Graph --> Selector["Critic Role Selector"]
    Graph --> Gate["Human Criteria Gate"]
    Graph --> Critics["Expert Critic Panel"]
    Graph --> Aggregator["Critic Aggregator"]
    Graph --> Compiler["Report Compiler"]
    Analyst --> Tools["SearchTools Facade"]
    Tools --> Direct["Direct Web/RAG Tools"]
    Tools --> MCP["Optional SearchMCP"]
    Compiler --> Output["output/*.md"]
    Graph --> Langfuse["Langfuse Trace / Metadata"]
```

## 2. LangGraph Workflow

```mermaid
stateDiagram-v2
    [*] --> Analyst
    Analyst --> CriticRoleSelector: first draft
    CriticRoleSelector --> HumanCriteriaGate: selected roles
    HumanCriteriaGate --> ExpertCriticPanel: approved, edited, or ad-hoc criteria
    Analyst --> ExpertCriticPanel: revision with approved roles
    ExpertCriticPanel --> CriticAggregator
    CriticAggregator --> Analyst: NEEDS_REVISION and rounds < 3
    CriticAggregator --> ReportCompiler: APPROVED or revision limit reached
    ReportCompiler --> [*]
```

## 3. Expert Critic Panel

```mermaid
flowchart TD
    Draft["DraftReport"] --> Selector["CriticRoleSelector"]
    Registry["Base Critic Registry"] --> Selector
    Selector --> Roles["Default Financial + Risk Roles"]
    Roles --> Human["Human Criteria Gate"]
    Human -. "human adds role" .-> Custom["Ad-hoc Critic"]
    Human -. "AI suggests role" .-> Suggested["AI-Suggested Critic"]
    Human --> Financial["Financial Critic"]
    Human --> Risk["Risk Manager"]
    Human -. "if relevant" .-> Security["Security Critic"]
    Human -. "if relevant" .-> Architecture["Technical Architecture Critic"]
    Human -. "if relevant" .-> Change["Change Management Critic"]
    Financial --> Aggregate["Critic Aggregator"]
    Risk --> Aggregate
    Suggested --> Aggregate
    Security --> Aggregate
    Architecture --> Aggregate
    Change --> Aggregate
    Custom --> Aggregate
    Aggregate --> Verdict{"APPROVED?"}
    Verdict -- "no" --> Revision["Analyst Revision"]
    Verdict -- "yes" --> Compiler["Report Compiler"]
```

## 4. Optional MCP Boundary

```mermaid
flowchart LR
    Analyst["Research Analyst"] --> Facade["SearchTools Facade"]
    Facade --> Mode{"COURSE_PROJECT_TOOL_BACKEND"}
    Mode -- "direct" --> Direct["Direct tools.py / tool_impl.py"]
    Mode -- "mcp_auto" --> TryMCP["Try SearchMCP"]
    Mode -- "mcp_required" --> Required["Require SearchMCP"]
    TryMCP --> Healthy{"MCP reachable?"}
    Healthy -- "yes" --> MCP["FastMCP Server :8911"]
    Healthy -- "no" --> Direct
    Required --> MCP
    MCP --> Web["web_search"]
    MCP --> Url["read_url"]
    MCP --> KB["knowledge_search"]
    MCP --> Stats["resource://market-knowledge-stats"]
```

## 5. SPA And SSE Runtime

```mermaid
sequenceDiagram
    participant User
    participant SPA as React SPA
    participant API as FastAPI
    participant Graph as LangGraph
    participant Human as Human Criteria Gate

    User->>SPA: Start analysis
    SPA->>API: POST /api/runs
    API->>Graph: stream workflow
    API-->>SPA: SSE run_started
    Graph-->>API: Analyst / selector events
    API-->>SPA: SSE agent_update
    Graph-->>Human: interrupt(selected roles)
    API-->>SPA: SSE hitl_required
    User->>SPA: approve or edit criteria
    SPA->>API: POST /api/runs/{run_id}/critic-criteria
    API->>Graph: Command(resume=criteria)
    Graph-->>API: critics, aggregator, compiler events
    API-->>SPA: SSE completed + run_completed
    SPA->>API: GET /api/runs/{run_id}
    API-->>SPA: final report + Mermaid diagrams
```

## 6. Reviewer Evidence Flow

```mermaid
flowchart TD
    Code["Code: graph.py, api.py, frontend"] --> Static["Static checks"]
    Static --> Build["Python compileall + npm build"]
    Build --> Docs["README + SUBMISSION_NOTES"]
    Docs --> Diagrams["Mermaid architecture notes"]
    Runtime["Runtime demo"] --> Trace["Langfuse trace id"]
    Runtime --> Report["Generated output/*.md"]
    Runtime --> Screens["SPA / Langfuse screenshots"]
    Trace --> Reviewer["Reviewer"]
    Report --> Reviewer
    Screens --> Reviewer
    Diagrams --> Reviewer
```
