# HW10 Evaluation Mermaid Diagrams

## 1. Evaluation Architecture

```mermaid
flowchart TD
    User["User / Reviewer"] --> Tests["DeepEval test suite<br/>tests/*.py"]
    Tests --> Golden["golden_dataset.json<br/>15 reviewed examples"]
    Tests --> Baseline["baseline_outputs.json<br/>reviewed baseline outputs"]
    Tests --> Metrics["DeepEval metrics<br/>GEval, AnswerRelevancy,<br/>ToolCorrectness"]

    Metrics --> Judge["Judge model<br/>EVAL_MODEL=gpt-5.4-mini<br/>OpenAI API"]

    subgraph Target["Target system copied from HW8"]
        Supervisor["Supervisor<br/>Plan -> Research -> Critique -> save_report"]
        Planner["Planner Agent"]
        Researcher["Research Agent"]
        Critic["Critic Agent"]
        Tools["web_search<br/>read_url<br/>knowledge_search<br/>save_report"]
    end

    Tests -.evaluates.-> Target
    Supervisor --> Planner
    Supervisor --> Researcher
    Supervisor --> Critic
    Supervisor --> Tools
```

## 2. Golden Dataset Coverage

```mermaid
pie title Golden dataset categories
    "happy_path" : 5
    "edge_case" : 5
    "failure_case" : 5
```

## 3. Component-Level Evaluation

```mermaid
flowchart LR
    PlannerCase["Planner sample output"] --> PlanSchema["ResearchPlan schema check"]
    PlannerCase --> PlanMetric["GEval<br/>Plan Quality 0.7"]

    ResearchCase["Researcher findings<br/>+ retrieval_context"] --> Groundedness["GEval<br/>Research Groundedness 0.7"]

    CriticCase["Critic sample output"] --> CriticSchema["CritiqueResult schema check"]
    CriticCase --> CriticMetric["GEval<br/>Critique Quality 0.7"]
```

## 4. Tool Correctness

```mermaid
flowchart TD
    PlannerTrace["Planner trace"] --> PlannerTools["Expected:<br/>knowledge_search + web_search"]
    ResearchTrace["Researcher trace"] --> ResearchTools["Expected:<br/>knowledge_search + web_search + read_url"]
    SupervisorTrace["Supervisor trace after APPROVE"] --> SupervisorTools["Expected:<br/>plan + research + critique + save_report"]

    PlannerTools --> ToolMetric["ToolCorrectnessMetric<br/>exact match"]
    ResearchTools --> ToolMetric
    SupervisorTools --> ToolMetric
```

## 5. End-to-End Baseline Evaluation

```mermaid
sequenceDiagram
    autonumber
    participant D as DeepEval
    participant G as golden_dataset.json
    participant B as baseline_outputs.json
    participant M as Metrics
    participant J as OpenAI Judge

    D->>G: load input + expected_output
    D->>B: load actual_output
    D->>M: build LLMTestCase
    alt happy_path or edge_case
        M->>J: AnswerRelevancyMetric
    else failure_case
        M->>J: GEval Failure Case Safety
    end
    M->>J: GEval Correctness
    M->>J: Custom GEval Policy Fit
    J-->>D: scores + reasons
```

## 6. Endpoint Separation

```mermaid
flowchart TD
    Env["Root .env"] --> TargetBase["OPENAI_BASE_URL<br/>LM Studio local endpoint"]
    Env --> EvalModel["EVAL_MODEL<br/>gpt-5.4-mini"]
    Env --> ApiKey["OPENAI_API_KEY<br/>OpenAI key"]

    TargetBase --> Agents["Homework agents<br/>target system"]
    EvalModel --> DeepEval["DeepEval judge"]
    ApiKey --> DeepEval
    DeepEval --> Official["https://api.openai.com/v1"]

    Conftest["tests/conftest.py"] --> DeepEval
    Conftest -.preserves.-> TargetBase
    Conftest -.overrides judge base url.-> Official
```
