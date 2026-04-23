# UML / Mermaid діаграми MCP + ACP системи (homework lesson 9)

## 1. Загальна архітектура

```mermaid
flowchart LR
    User["User<br/>main.py REPL"] --> Supervisor["Local Supervisor<br/>LangChain create_agent"]

    Supervisor -->|"delegate_to_planner"| ACP["ACP Server<br/>acp_server.py :8903"]
    Supervisor -->|"delegate_to_researcher"| ACP
    Supervisor -->|"delegate_to_critic"| ACP
    Supervisor -->|"local save_report tool"| HITL["HumanInTheLoopMiddleware<br/>approve / edit / reject"]
    HITL -->|"approve only"| ReportMCP["ReportMCP<br/>FastMCP :8902"]

    ACP --> Planner["Planner Agent<br/>ResearchPlan"]
    ACP --> Researcher["Research Agent<br/>findings"]
    ACP --> Critic["Critic Agent<br/>CritiqueResult"]

    Planner -->|"MCP client"| SearchMCP["SearchMCP<br/>FastMCP :8901"]
    Researcher -->|"MCP client"| SearchMCP
    Critic -->|"MCP client"| SearchMCP

    SearchMCP --> Web["web_search<br/>read_url"]
    SearchMCP --> RAG["knowledge_search<br/>Qdrant + BM25 + rerank"]
    ReportMCP --> Output["output/*.md"]
```

## 2. MCP Tools And Resources

```mermaid
classDiagram
    class SearchMCP {
        +web_search(query)
        +read_url(url)
        +knowledge_search(query)
        +resource knowledge-base-stats
    }

    class ReportMCP {
        +save_report(filename, content)
        +resource output-dir
    }

    class SharedTools {
        +web_search_impl(query)
        +read_url_impl(url)
        +knowledge_search_impl(query)
        +save_report_impl(filename, content)
        +safe_report_filename(filename)
    }

    class QdrantRetriever {
        +search(query)
        +homework_lesson_9_knowledge
    }

    SearchMCP --> SharedTools
    ReportMCP --> SharedTools
    SharedTools --> QdrantRetriever
```

## 3. ACP Agent Delegation

```mermaid
sequenceDiagram
    autonumber
    participant S as Local Supervisor
    participant A as ACP Server
    participant P as Planner Agent
    participant R as Research Agent
    participant C as Critic Agent
    participant M as SearchMCP

    S->>A: run_sync(agent="planner", input=user_request)
    A->>P: planner_handler(input)
    P->>M: list_tools()
    M-->>P: web_search, knowledge_search
    P->>M: call_tool("knowledge_search", ...)
    M-->>P: evidence
    P-->>S: ResearchPlan JSON

    S->>A: run_sync(agent="researcher", input=plan)
    A->>R: researcher_handler(input)
    R->>M: call_tool("knowledge_search" / "web_search" / "read_url")
    M-->>R: source-backed findings
    R-->>S: findings

    S->>A: run_sync(agent="critic", input=findings)
    A->>C: critic_handler(input)
    C->>M: spot-check claims
    M-->>C: verification evidence
    C-->>S: CritiqueResult JSON
```

## 4. End-To-End Workflow

```mermaid
stateDiagram-v2
    [*] --> Plan
    Plan --> Research: ResearchPlan
    Research --> Critique: findings
    Critique --> Research: verdict=REVISE and rounds < 2
    Critique --> SaveReport: verdict=APPROVE
    Critique --> SaveReport: revision limit reached
    SaveReport --> HITL: local save_report called
    HITL --> SaveReport: edit feedback
    HITL --> Saved: approve
    HITL --> Cancelled: reject
    Saved --> [*]
    Cancelled --> [*]
```

## 5. HITL Save Through ReportMCP

```mermaid
flowchart TD
    Draft["Supervisor composes final Markdown report"] --> LocalTool["Local save_report(filename, content)<br/>supervisor.py"]
    LocalTool --> Middleware["HumanInTheLoopMiddleware<br/>interrupt_on save_report"]
    Middleware --> Preview["main.py prints filename and preview"]
    Preview --> Decision{"User decision"}

    Decision -->|"approve"| ResumeApprove["Command resume approve"]
    ResumeApprove --> Wrapper["save_report wrapper resumes"]
    Wrapper --> ReportMCP["ReportMCP.call_tool save_report"]
    ReportMCP --> File["output/*.md"]

    Decision -->|"edit + feedback"| ResumeEdit["Command resume reject with feedback"]
    ResumeEdit --> Revise["Supervisor revises report"]
    Revise --> LocalTool

    Decision -->|"reject"| ResumeReject["Command resume reject cancellation"]
    ResumeReject --> Stop["Saving cancelled<br/>save_cancelled guard"]
```

## 6. Startup And Runtime Map

```mermaid
flowchart TD
    Start["Clean/local environment"] --> Docker["Docker Qdrant<br/>localhost:6333"]
    Docker --> Ingest["uv run python ingest.py<br/>collection homework_lesson_9_knowledge"]
    Ingest --> Search["uv run python mcp_servers/search_mcp.py<br/>:8901/mcp"]
    Ingest --> Report["uv run python mcp_servers/report_mcp.py<br/>:8902/mcp"]
    Search --> ACP["uv run python acp_server.py<br/>:8903"]
    Report --> ACP
    ACP --> Main["uv run python main.py"]

    Helper["scripts/start_hw9_servers.ps1"] --> Search
    Helper --> Report
    Helper --> ACP
```

## 7. Reviewer Evidence Map

```mermaid
flowchart LR
    Reviewer["Reviewer"] --> Notes["SUBMISSION_NOTES.md"]
    Reviewer --> Diagrams["uml_diagrams/MCP_ACP_MERMAID.md"]
    Reviewer --> Trace["output/hw9_protocol_trace_summary.md"]
    Reviewer --> MainReport["output/hw9_rag_comparison_report.md"]
    Reviewer --> DinoReport["output/dinosaurs_among_us_report.md"]
    Reviewer --> ModelReport["output/ai_model_claims_report.md"]

    Notes --> Requirements["Requirement -> Code map"]
    Notes --> Intent["Намір - Дія - Висновок"]
    Diagrams --> Architecture["MCP + ACP + HITL architecture"]
    Trace --> Runtime["Protocol discovery<br/>agent smoke<br/>HITL paths"]
    MainReport --> Artifact["Canonical RAG report<br/>saved through ReportMCP"]
    DinoReport --> WebFirst["Web-first research<br/>optional RAG"]
    ModelReport --> CurrentNews["Current-news research<br/>external verification"]
```
