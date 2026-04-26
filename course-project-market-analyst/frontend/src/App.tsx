import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import mermaid from "mermaid";
import {
  Bot,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Maximize2,
  Play,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8012";

type CriticRole = {
  role_id: string;
  name: string;
  focus: string;
  criteria: string[];
  role_origin?: "standard" | "custom" | "suggested";
};

type RunEvent = {
  type: string;
  agent: string;
  message: string;
  payload: Record<string, unknown>;
  timestamp?: string;
};

type Diagram = {
  title: string;
  kind: string;
  mermaid: string;
};

type FinalReport = {
  title: string;
  markdown: string;
  diagrams: Diagram[];
  saved_path?: string;
};

type RunSnapshot = {
  run_id: string;
  status: string;
  trace_id?: string | null;
  history?: RunEvent[];
  final_report?: FinalReport | null;
  critic_roles?: CriticRole[];
  approved_roles?: CriticRole[];
  additional_criteria?: string[];
  pending_interrupt?: {
    selected_roles?: CriticRole[];
  } | null;
};

type PromptSuggestion = {
  prompt: string;
  rationale: string;
  tags: string[];
};

type CriticSuggestion = {
  role: CriticRole;
  rationale: string;
  tags: string[];
};

const defaultPrompt =
  "Analyze the market for agentic AI developer tools for a small AEC/manufacturing software team. Compare coding agents, IDE copilots, observability/evaluation platforms, and MCP-based integrations. Recommend an adoption roadmap.";

const STANDARD_ROLE_IDS = new Set(["financial", "risk"]);

type ExpandedView =
  | { type: "report" }
  | { type: "diagram"; diagram: Diagram; index: number }
  | null;

function eventKey(event: RunEvent) {
  return `${event.timestamp ?? ""}|${event.type}|${event.agent}|${event.message}|${JSON.stringify(event.payload)}`;
}

function roleOrigin(role: CriticRole): "standard" | "custom" | "suggested" {
  if (role.role_origin) return role.role_origin;
  if (STANDARD_ROLE_IDS.has(role.role_id)) return "standard";
  if (role.role_id.startsWith("custom") || role.role_id.startsWith("human_custom")) return "custom";
  return "suggested";
}

function normalizeRoleOrigins(roles: CriticRole[]): CriticRole[] {
  return roles.map((role) => ({ ...role, role_origin: roleOrigin(role) }));
}

function roleOriginLabel(role: CriticRole) {
  const origin = roleOrigin(role);
  if (origin === "standard") return "standard";
  if (origin === "custom") return "custom";
  return "AI suggested";
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="modalBackdrop" role="dialog" aria-modal="true">
      <section className="modalPanel">
        <header className="modalHeader">
          <h2>{title}</h2>
          <button className="secondaryButton" onClick={onClose}>
            <span className="buttonContent">
              <X size={16} />
              Close
            </span>
          </button>
        </header>
        <div className="modalBody">{children}</div>
      </section>
    </div>
  );
}

function MermaidDiagram({
  diagram,
  index,
  idPrefix = "inline",
  onExpand,
}: {
  diagram: Diagram;
  index: number;
  idPrefix?: string;
  onExpand?: () => void;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      themeVariables: {
        primaryColor: "#eef7f2",
        primaryTextColor: "#10201a",
        primaryBorderColor: "#2e7d59",
        lineColor: "#3e5f50",
        secondaryColor: "#fff4ec",
        tertiaryColor: "#f4f1ff",
        fontFamily: "Inter, Arial, sans-serif",
      },
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const target = ref.current;
    if (!target) return;

    mermaid
      .render(`diagram-${idPrefix}-${index}-${diagram.kind}`, diagram.mermaid)
      .then(({ svg }) => {
        if (!cancelled) {
          target.innerHTML = svg;
          setFailed(false);
        }
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [diagram, idPrefix, index]);

  return (
    <section className="diagramBlock">
      <div className="panelHeader compactHeader">
        <h3>{diagram.title}</h3>
        {onExpand && (
          <button className="smallButton" onClick={onExpand}>
            <span className="buttonContent">
              <Maximize2 size={14} />
              Fullscreen
            </span>
          </button>
        )}
      </div>
      {failed ? <pre className="mermaidRaw">{diagram.mermaid}</pre> : <div ref={ref} className="mermaidCanvas" />}
    </section>
  );
}

function CriteriaPanel({
  roles,
  onSubmit,
  onSuggestCritic,
  isExpanded,
  onToggle,
  hasReport,
  isWorking,
}: {
  roles: CriticRole[];
  onSubmit: (roles: CriticRole[], extra: string[]) => void;
  onSuggestCritic: (roles: CriticRole[]) => Promise<CriticSuggestion | null>;
  isExpanded: boolean;
  onToggle: () => void;
  hasReport: boolean;
  isWorking: boolean;
}) {
  const [editableRoles, setEditableRoles] = useState<CriticRole[]>(roles);
  const [extraCriteria, setExtraCriteria] = useState(
    "Check whether the adoption roadmap preserves human review for write actions.",
  );
  const [criticSuggestion, setCriticSuggestion] = useState<CriticSuggestion | null>(null);
  const [isSuggestingCritic, setIsSuggestingCritic] = useState(false);

  useEffect(() => {
    setEditableRoles(normalizeRoleOrigins(roles));
  }, [roles]);

  function defaultCustomRole(): CriticRole {
    return {
      role_id: `custom_relevance_${Date.now()}`,
      role_origin: "custom",
      name: "Relevance / Freshness Critic",
      focus:
        "Checks whether the analysis is current, relevant to the request, and separated from outdated market assumptions.",
      criteria: [
        "Does the report use current market signals for time-sensitive claims?",
        "Does the recommendation stay relevant to the target audience in the user's request?",
      ],
    };
  }

  function updateRoleField(roleIndex: number, field: "name" | "focus", value: string) {
    setEditableRoles((current) =>
      current.map((role, index) => (index === roleIndex ? { ...role, [field]: value } : role)),
    );
  }

  function updateCriterion(roleIndex: number, criterionIndex: number, value: string) {
    setEditableRoles((current) =>
      current.map((role, rIndex) =>
        rIndex === roleIndex
          ? {
              ...role,
              criteria: role.criteria.map((criterion, cIndex) =>
                cIndex === criterionIndex ? value : criterion,
              ),
            }
          : role,
      ),
    );
  }

  function addCriterion(roleIndex: number) {
    setEditableRoles((current) =>
      current.map((role, index) =>
        index === roleIndex ? { ...role, criteria: [...role.criteria, "New custom criterion."] } : role,
      ),
    );
  }

  function removeCriterion(roleIndex: number, criterionIndex: number) {
    setEditableRoles((current) =>
      current.map((role, rIndex) =>
        rIndex === roleIndex
          ? { ...role, criteria: role.criteria.filter((_, cIndex) => cIndex !== criterionIndex) }
          : role,
      ),
    );
  }

  function removeRole(roleIndex: number) {
    setEditableRoles((current) => current.filter((_, index) => index !== roleIndex));
  }

  async function suggestCritic() {
    setIsSuggestingCritic(true);
    try {
      const suggestion = await onSuggestCritic(editableRoles);
      if (!suggestion) return;
      setCriticSuggestion(suggestion);
      setEditableRoles((current) => {
        const existingIds = new Set(current.map((role) => role.role_id));
        const role = existingIds.has(suggestion.role.role_id)
          ? { ...suggestion.role, role_origin: "suggested" as const, role_id: `${suggestion.role.role_id}_${Date.now()}` }
          : { ...suggestion.role, role_origin: "suggested" as const };
        return [...current, role];
      });
    } finally {
      setIsSuggestingCritic(false);
    }
  }

  return (
    <div className={`hitlPanel ${isExpanded ? "" : "panelCollapsed"}`}>
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Human criteria gate</p>
          <h2>{hasReport ? "Expert critics ready" : "Approve expert critics"}</h2>
          <p>
            {hasReport
              ? "The report is ready. Expand this panel only when you want to add critics or regenerate the decision package."
              : "The analyst draft is ready. Adjust the critic criteria before the review panel decides whether the report needs another revision."}
          </p>
        </div>
        <button className="secondaryButton" onClick={onToggle}>
          <span className="buttonContent">
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {isExpanded ? "Collapse" : "Expand"}
          </span>
        </button>
      </div>

      {!isExpanded && (
        <div className="collapsedSummary">
          {editableRoles.map((role) => (
            <span className={`roleChip ${roleOrigin(role)}`} key={role.role_id}>
              {role.name}
            </span>
          ))}
        </div>
      )}

      {isExpanded && (
        <>
      <div className="roleList">
        {editableRoles.map((role, roleIndex) => (
          <article className={`roleCard ${roleOrigin(role)}`} key={role.role_id}>
            <div className="roleMetaRow">
              <span className={`roleBadge ${roleOrigin(role)}`}>{roleOriginLabel(role)}</span>
            </div>
            <label className="field compactField">
              Critic name
              <input
                value={role.name}
                onChange={(event) => updateRoleField(roleIndex, "name", event.target.value)}
              />
            </label>
            <label className="field compactField">
              Focus
              <textarea
                className="focusInput"
                value={role.focus}
                onChange={(event) => updateRoleField(roleIndex, "focus", event.target.value)}
              />
            </label>
            {role.criteria.map((criterion, criterionIndex) => (
              <div className="criterionRow" key={`${role.role_id}-${criterionIndex}`}>
                <textarea
                  value={criterion}
                  onChange={(event) => updateCriterion(roleIndex, criterionIndex, event.target.value)}
                />
                <button className="smallButton" onClick={() => removeCriterion(roleIndex, criterionIndex)}>
                  <span className="buttonContent">
                    <Trash2 size={14} />
                    Remove
                  </span>
                </button>
              </div>
            ))}
            <div className="roleActions">
              <button className="secondaryButton" onClick={() => addCriterion(roleIndex)}>
                <span className="buttonContent">
                  <Plus size={16} />
                  Add criterion
                </span>
              </button>
              <button className="secondaryButton" onClick={() => removeRole(roleIndex)}>
                <span className="buttonContent">
                  <Trash2 size={16} />
                  Remove critic
                </span>
              </button>
            </div>
          </article>
        ))}
      </div>

      <button
        className="secondaryButton"
        onClick={() => setEditableRoles((current) => [...current, defaultCustomRole()])}
      >
        <span className="buttonContent">
          <Plus size={16} />
          Add custom critic
        </span>
      </button>

      <button
        className="aiButton"
        disabled={isWorking || isSuggestingCritic}
        onClick={suggestCritic}
      >
        <span className="buttonContent">
          <Sparkles size={16} />
          {isSuggestingCritic ? "Suggesting critic..." : "Suggest AI critic"}
        </span>
      </button>

      {criticSuggestion && (
        <div className="promptSuggestion">
          <strong>Suggested critic:</strong>
          <p>
            {criticSuggestion.role.name}: {criticSuggestion.rationale}
          </p>
          {criticSuggestion.tags.length > 0 && (
            <div className="tagList">
              {criticSuggestion.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <label className="field">
        Additional criteria
        <textarea
          value={extraCriteria}
          onChange={(event) => setExtraCriteria(event.target.value)}
          placeholder="Optional semicolon-separated criteria"
        />
      </label>

      <button
        className="primaryButton"
        disabled={isWorking}
        onClick={() =>
          onSubmit(
            editableRoles,
            extraCriteria
              .split(";")
              .map((item) => item.trim())
              .filter(Boolean),
          )
        }
      >
        <span className="buttonContent">
          <Bot size={16} />
          {hasReport ? "Regenerate report with critics" : "Run expert critique"}
        </span>
      </button>
        </>
      )}
    </div>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState(defaultPrompt);
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [criticRoles, setCriticRoles] = useState<CriticRole[]>([]);
  const [finalReport, setFinalReport] = useState<FinalReport | null>(null);
  const [lastHeartbeat, setLastHeartbeat] = useState<string | null>(null);
  const [promptSuggestion, setPromptSuggestion] = useState<PromptSuggestion | null>(null);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [criteriaExpanded, setCriteriaExpanded] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [expandedView, setExpandedView] = useState<ExpandedView>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [clockTick, setClockTick] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  const groupedEvents = useMemo(() => events.slice().reverse(), [events]);
  const isWorking = ["starting", "created", "running"].includes(status);
  const hasReport = Boolean(finalReport);
  const elapsedSeconds = startedAt ? Math.max(0, Math.floor((clockTick - startedAt) / 1000)) : 0;

  function addEvent(event: RunEvent) {
    const key = eventKey(event);
    setEvents((current) => (current.some((item) => eventKey(item) === key) ? current : [...current, event]));
  }

  async function refreshRun(id: string) {
    const response = await fetch(`${API_BASE}/api/runs/${id}`);
    if (!response.ok) return;
    const snapshot = (await response.json()) as RunSnapshot;
    setStatus(snapshot.status);
    if (snapshot.history?.length) setEvents(snapshot.history);
    if (snapshot.final_report) {
      setFinalReport(snapshot.final_report);
      setCriteriaExpanded(false);
    }
    const persistedRoles = snapshot.critic_roles ?? snapshot.approved_roles;
    if (persistedRoles?.length) {
      setCriticRoles(normalizeRoleOrigins(persistedRoles));
    }
    if (snapshot.pending_interrupt?.selected_roles) {
      setCriticRoles(normalizeRoleOrigins(snapshot.pending_interrupt.selected_roles));
      setCriteriaExpanded(true);
    }
  }

  function connectEvents(id: string) {
    eventSourceRef.current?.close();
    const source = new EventSource(`${API_BASE}/api/runs/${id}/events`);
    eventSourceRef.current = source;

    source.onerror = () => {
      setLastHeartbeat("SSE reconnecting");
    };

    source.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as RunEvent;
      addEvent(parsed);
    };

    source.addEventListener("heartbeat", (event) => {
      const parsed = JSON.parse((event as MessageEvent).data) as RunEvent;
      const heartbeatStatus = parsed.payload.status as string | undefined;
      setLastHeartbeat(parsed.timestamp ?? new Date().toLocaleTimeString());
      if (heartbeatStatus && heartbeatStatus !== "created") setStatus(heartbeatStatus);
      if (heartbeatStatus === "completed" || heartbeatStatus === "failed") {
        source.close();
        if (eventSourceRef.current === source) eventSourceRef.current = null;
        if (heartbeatStatus === "completed") void refreshRun(id);
      }
    });

    ["run_started", "agent_update", "human_update", "hitl_required", "hitl_submitted", "completed", "run_completed", "run_failed"].forEach(
      (eventName) => {
        source.addEventListener(eventName, (event) => {
          const parsed = JSON.parse((event as MessageEvent).data) as RunEvent;
          addEvent(parsed);
          if (["run_started", "agent_update", "human_update", "hitl_submitted"].includes(parsed.type)) {
            setStatus("running");
          }
          if (parsed.type === "hitl_submitted") {
            const roles = parsed.payload.approved_roles as CriticRole[] | undefined;
            if (roles?.length) setCriticRoles(normalizeRoleOrigins(roles));
            setCriteriaExpanded(false);
          }
          if (parsed.type === "hitl_required") {
            const roles = parsed.payload.selected_roles as CriticRole[] | undefined;
            setCriticRoles(normalizeRoleOrigins(roles ?? []));
            setCriteriaExpanded(true);
            setStatus("awaiting_criteria");
          }
          if (parsed.type === "run_completed") {
            setStatus("completed");
            setCriteriaExpanded(false);
            source.close();
            if (eventSourceRef.current === source) eventSourceRef.current = null;
            void refreshRun(id);
          }
          if (parsed.type === "run_failed") {
            setStatus("failed");
            source.close();
            if (eventSourceRef.current === source) eventSourceRef.current = null;
          }
        });
      },
    );
  }

  async function startRun() {
    setEvents([]);
    setCriticRoles([]);
    setFinalReport(null);
    setLastHeartbeat(null);
    setCriteriaExpanded(false);
    const now = Date.now();
    setStartedAt(now);
    setClockTick(now);
    setStatus("starting");

    const response = await fetch(`${API_BASE}/api/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const created = (await response.json()) as { run_id: string; status: string };
    setRunId(created.run_id);
    setStatus(created.status);
    connectEvents(created.run_id);
  }

  async function generateRandomPrompt() {
    setIsGeneratingPrompt(true);
    try {
      const response = await fetch(`${API_BASE}/api/research-prompts/random`);
      if (!response.ok) throw new Error("Prompt generation failed");
      const suggestion = (await response.json()) as PromptSuggestion;
      setPrompt(suggestion.prompt);
      setPromptSuggestion(suggestion);
    } finally {
      setIsGeneratingPrompt(false);
    }
  }

  async function submitCriteria(roles: CriticRole[], extra: string[]) {
    if (!runId) return;
    setCriticRoles(normalizeRoleOrigins(roles));
    setStatus("running");
    setCriteriaExpanded(false);
    const response = await fetch(`${API_BASE}/api/runs/${runId}/critic-criteria`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved_roles: roles, additional_criteria: extra }),
    });
    if (response.ok) {
      setEvents([]);
      connectEvents(runId);
    } else {
      setStatus("failed");
    }
  }

  async function suggestCritic(roles: CriticRole[]) {
    if (!runId) return null;
    const response = await fetch(`${API_BASE}/api/runs/${runId}/critic-roles/suggest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ existing_roles: roles }),
    });
    if (!response.ok) return null;
    return (await response.json()) as CriticSuggestion;
  }

  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  useEffect(() => {
    if (!isWorking) return;
    const interval = window.setInterval(() => setClockTick(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [isWorking]);

  return (
    <main className="appShell">
      <section className={`workspace ${sidebarCollapsed ? "sidebarCollapsed" : ""}`}>
        <aside className={`controlPane ${sidebarCollapsed ? "collapsedControl" : ""}`}>
          <button
            className="sidebarToggle"
            onClick={() => setSidebarCollapsed((current) => !current)}
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
          {sidebarCollapsed ? (
            <div className="collapsedSidebarLabel">MA</div>
          ) : (
            <>
          <div className="brandRow">
            <div className="mark">MA</div>
            <div>
              <p className="eyebrow">Course project</p>
              <h1>Market Analyst</h1>
            </div>
          </div>

          <label className="field">
            Supervisor request
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          </label>

          <button
            className="aiButton"
            onClick={generateRandomPrompt}
            disabled={isGeneratingPrompt || isWorking}
          >
            <span className="buttonContent">
              <Sparkles size={16} />
              {isGeneratingPrompt ? "Generating prompt..." : "Generate random research prompt"}
            </span>
          </button>

          {promptSuggestion && (
            <div className="promptSuggestion">
              <strong>Why this topic:</strong>
              <p>{promptSuggestion.rationale}</p>
              {promptSuggestion.tags.length > 0 && (
                <div className="tagList">
                  {promptSuggestion.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          <button className="primaryButton" onClick={startRun} disabled={status === "running" || status === "starting"}>
            <span className="buttonContent">
              <Play size={16} />
              Start analysis
            </span>
          </button>

          <div className="statusBox">
            <span>Status</span>
            <strong>{status}</strong>
            {runId && <small>Run {runId}</small>}
            {isWorking && (
              <div className="activityIndicator">
                <span className="spinner" aria-hidden="true" />
                <span>
                  Working for {elapsedSeconds}s
                  {lastHeartbeat ? `, heartbeat ${lastHeartbeat}` : ""}
                </span>
              </div>
            )}
          </div>

          <section className="eventLog">
            <h2>Agent stream</h2>
            {groupedEvents.length === 0 ? (
              <p className="muted">No events yet.</p>
            ) : (
              groupedEvents.map((event, index) => (
                <article className="eventItem" key={`${event.timestamp}-${index}`}>
                  <span>{event.agent}</span>
                  <p>{event.message}</p>
                  <small>{event.type}</small>
                </article>
              ))
            )}
          </section>
            </>
          )}
        </aside>

        <section className="mainPane">
          {criticRoles.length > 0 && (
            <CriteriaPanel
              roles={criticRoles}
              onSubmit={submitCriteria}
              onSuggestCritic={suggestCritic}
              isExpanded={criteriaExpanded}
              onToggle={() => setCriteriaExpanded((current) => !current)}
              hasReport={hasReport}
              isWorking={isWorking}
            />
          )}

          <section className="reportPane">
            <div className="panelHeader">
              <div>
                <p className="eyebrow">Decision package</p>
                <h2>{finalReport?.title ?? "Waiting for final report"}</h2>
                {finalReport?.saved_path && <p className="savedPath">{finalReport.saved_path}</p>}
              </div>
              <button className="secondaryButton" onClick={() => setExpandedView({ type: "report" })}>
                <span className="buttonContent">
                  <Maximize2 size={16} />
                  Fullscreen
                </span>
              </button>
            </div>
            <pre className="reportPreview">
              {finalReport?.markdown ?? "The final sourced report will appear here after the compiler finishes."}
            </pre>
          </section>

          <section className="diagramPane">
            <div>
              <p className="eyebrow">Mermaid decision artifacts</p>
              <h2>Market decisions, payback and timing</h2>
            </div>
            {finalReport?.diagrams?.length ? (
              finalReport.diagrams.map((diagram, index) => (
                <MermaidDiagram
                  key={`${diagram.kind}-${index}`}
                  diagram={diagram}
                  index={index}
                  onExpand={() => setExpandedView({ type: "diagram", diagram, index })}
                />
              ))
            ) : (
              <p className="muted">Diagrams render here after report compilation.</p>
            )}
          </section>
        </section>
      </section>
      {expandedView?.type === "report" && (
        <Modal title={finalReport?.title ?? "Decision package"} onClose={() => setExpandedView(null)}>
          <pre className="reportPreview expandedReport">
            {finalReport?.markdown ?? "The final sourced report will appear here after the compiler finishes."}
          </pre>
        </Modal>
      )}
      {expandedView?.type === "diagram" && (
        <Modal title={expandedView.diagram.title} onClose={() => setExpandedView(null)}>
          <MermaidDiagram diagram={expandedView.diagram} index={expandedView.index} idPrefix="modal" />
        </Modal>
      )}
    </main>
  );
}
