# UML / Mermaid діаграми мультиагентної системи (homework lesson 8)

## 1. Загальна архітектура: Plan → Research → Critique → Report

```mermaid
flowchart LR
    User["Користувач<br/>main.py REPL"] --> Supervisor["supervisor.py<br/>Supervisor Agent"]

    Supervisor -->|"tool: plan"| Planner["agents/planner.py<br/>Planner Agent"]
    Supervisor -->|"tool: research"| Researcher["agents/research.py<br/>Research Agent"]
    Supervisor -->|"tool: critique"| Critic["agents/critic.py<br/>Critic Agent"]
    Supervisor -->|"tool: save_report<br/>HITL interrupt"| SaveReport["save_report<br/>(tools.py)"]

    Planner -->|"web_search<br/>knowledge_search"| Tools["tools.py"]
    Researcher -->|"web_search<br/>read_url<br/>knowledge_search"| Tools
    Critic -->|"web_search<br/>read_url<br/>knowledge_search"| Tools

    Planner -.structured.-> Plan["ResearchPlan<br/>(schemas.py)"]
    Critic -.structured.-> Critique["CritiqueResult<br/>(schemas.py)"]

    Tools --> Retriever["retriever.py<br/>HybridRerankRetriever"]
    Retriever --> Qdrant["Qdrant<br/>semantic search"]
    Retriever --> BM25["BM25<br/>lexical search"]
    Retriever --> Reranker["BAAI/bge-reranker-base<br/>cross-encoder"]

    SaveReport --> Output["output/*.md"]

    subgraph HITL["Human-in-the-Loop Middleware"]
        Interrupt["interrupt_on save_report"] --> Decision{"approve<br/>edit<br/>reject"}
    end

    Supervisor --- Interrupt
    Decision -->|approve| SaveReport
    Decision -->|edit| Supervisor
    Decision -->|reject| Cancel["Short cancellation<br/>message"]
```

## 2. Evaluator–Optimizer loop (research ↔ critic)

```mermaid
stateDiagram-v2
    [*] --> Plan
    Plan --> Research : ResearchPlan
    Research --> Critique : findings
    Critique --> Research : verdict=REVISE<br/>revision_requests
    Critique --> SaveReport : verdict=APPROVE
    Critique --> SaveReport : revision_limit_reached<br/>(max_revision_rounds=2)
    SaveReport --> HITL
    HITL --> SaveReport : edit + feedback
    HITL --> [*] : approve (saved)
    HITL --> [*] : reject (cancel)
```

## 3. Повний sequence-flow одного запиту

```mermaid
sequenceDiagram
    autonumber
    participant U as User (REPL)
    participant S as Supervisor
    participant P as Planner Agent
    participant R as Research Agent
    participant C as Critic Agent
    participant T as RAG + Web tools
    participant H as HITL Middleware
    participant FS as output/*.md

    U->>S: "Порівняй підходи RAG. Збережи звіт."
    S->>P: plan(request)
    P->>T: knowledge_search / web_search
    T-->>P: domain snippets
    P-->>S: ResearchPlan (JSON)

    S->>R: research(plan + request)
    R->>T: knowledge_search / web_search / read_url
    T-->>R: evidence
    R-->>S: findings

    S->>C: critique(findings)
    C->>T: spot-check freshness / gaps
    T-->>C: verification data
    C-->>S: CritiqueResult {verdict, gaps, revision_requests}

    alt verdict = REVISE (and < max_revision_rounds)
        S->>R: research(revision_requests + prev findings)
        R-->>S: updated findings
        S->>C: critique(updated findings)
        C-->>S: CritiqueResult
    end

    S->>S: compose Markdown report
    S->>H: save_report(filename, content)
    H-->>U: ⏸ pending approval (show filename + preview)

    alt user: approve
        H->>FS: write report
        FS-->>S: path saved
        S-->>U: "Report saved to output/..."
    else user: edit + feedback
        H-->>S: Command(resume reject + feedback)
        S->>S: revise report from feedback
        S->>H: save_report(..., new content)
        Note over H,S: loop until approve or reject
    else user: reject
        H-->>S: Command(resume reject)
        S-->>U: "Saving cancelled."
    end
```

## 4. Agent-as-tool композиція

```mermaid
classDiagram
    class Supervisor {
        +create_agent(model, tools, prompt)
        +middleware HumanInTheLoopMiddleware
        +middleware ToolCallLimitMiddleware
        +middleware ModelCallLimitMiddleware
        +checkpointer InMemorySaver
    }

    class PlannerAgent {
        +system_prompt PLANNER_PROMPT
        +tools [web_search, knowledge_search]
        +response_format ToolStrategy(ResearchPlan)
    }

    class ResearchAgent {
        +system_prompt RESEARCH_PROMPT
        +tools [web_search, read_url, knowledge_search]
    }

    class CriticAgent {
        +system_prompt CRITIC_PROMPT
        +tools [web_search, read_url, knowledge_search]
        +response_format ToolStrategy(CritiqueResult)
    }

    class ResearchPlan {
        +goal str
        +search_queries list~str~
        +sources_to_check list~str~
        +output_format str
    }

    class CritiqueResult {
        +verdict Literal APPROVE REVISE
        +is_fresh bool
        +is_complete bool
        +is_well_structured bool
        +strengths list~str~
        +gaps list~str~
        +revision_requests list~str~
    }

    class Tools {
        +web_search(query)
        +read_url(url)
        +knowledge_search(query)
        +save_report(filename, content)
    }

    Supervisor --> PlannerAgent : @tool plan(request)
    Supervisor --> ResearchAgent : @tool research(request)
    Supervisor --> CriticAgent : @tool critique(findings)
    Supervisor --> Tools : @tool save_report (HITL)

    PlannerAgent --> ResearchPlan : structured_response
    CriticAgent --> CritiqueResult : structured_response

    PlannerAgent --> Tools
    ResearchAgent --> Tools
    CriticAgent --> Tools
```

## 5. HITL резюмування рішень користувача

```mermaid
flowchart TD
    Tool["Supervisor: save_report(filename, content)"] --> MW["HumanInTheLoopMiddleware<br/>interrupt_on save_report"]
    MW --> UI["main.py REPL:<br/>print filename + content preview"]
    UI --> Input{"approve / edit / reject"}

    Input -->|approve| Approve["Command(resume decisions type=approve)"]
    Input -->|edit| Edit["Command(resume decisions type=reject,<br/>message=feedback for revision)"]
    Input -->|reject| Reject["Command(resume decisions type=reject,<br/>message=stop saving)"]

    Approve --> Execute["Execute save_report<br/>write output/*.md"]
    Edit --> Resume["Supervisor revises report<br/>calls save_report again"]
    Reject --> Stop["Supervisor prints<br/>cancellation message"]

    Resume --> MW
```

Ця діаграма показує canonical path ДЗ: запис проходить через `save_report` і HITL-рішення користувача. Прямий fallback-запис з `main.py` навмисно не включено в основну діаграму, бо це last-resort виняток для слабких локальних моделей або середовища без бюджету на сильнішу модель, а не штатна оркестрація Supervisor.

## 6. Що комітиться в Git і що треба відтворити локально

Мапа для перевіряючого: ліва гілка — все, що приходить з клоном репо і достатньо для ревʼю; права гілка — локальні артефакти, які перевіряючому треба згенерувати самостійно (і як саме). Відповідає фактичному стану `git ls-files` + `git check-ignore` проти кореневого `.gitignore`.

```mermaid
flowchart TD
    Git["Git repository"] --> Code["Python код<br/>config.py, supervisor.py, agents/*, tools.py,<br/>retriever.py, ingest.py, schemas.py, main.py"]
    Git --> Docs["Документація<br/>README.md, SUBMISSION_NOTES.md,<br/>uml_diagrams/MULTI_AGENT_MERMAID.md"]
    Git --> Deps["requirements.txt"]
    Git --> DataPdfs["data/*.pdf<br/>вхідні PDF для RAG"]
    Git --> SampleReports["tracked output/*.md<br/>4 reviewer sample reports"]

    NotGit["Не комітиться"] --> Env[".env / .env.*<br/>API keys, MODEL_NAME, REQUEST_TIMEOUT"]
    NotGit --> QdrantVolume["Docker volume qdrant_storage<br/>вектори Qdrant (живе поза repo)"]
    NotGit --> LocalIndex["homework-lesson-8/index/<br/>chunks.json, manifest.json<br/>правило: homework-lesson-*/index/"]
    NotGit --> OutputDir["нові homework-lesson-8/output/*.md<br/>локальні згенеровані звіти<br/>правило: homework-lesson-*/output/"]
    NotGit --> Resources["homework-lesson-8/resources/<br/>лекційний notebook, посилання<br/>правило: resources"]
    NotGit --> Cache["__pycache__/ + HF/transformers cache<br/>(cross-encoder)"]
    NotGit --> Venv[".venv/"]
    NotGit --> IDE[".idea/, .vscode/"]

    LocalIndex --> Recreate["Відтворюється через<br/>uv run python ingest.py"]
    QdrantVolume --> Recreate
    OutputDir --> Recreate2["Відтворюється через<br/>uv run python main.py<br/>(і HITL approve)"]
```



