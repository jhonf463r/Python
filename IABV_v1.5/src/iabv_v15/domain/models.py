from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderKind(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class ProviderStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    OPTIONAL_INACTIVE = "optional_inactive"


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    DEEP = "deep"


class AmbiguityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReasoningMode(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    DEGRADED = "degraded"


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DossierScope(str, Enum):
    CHAT = "chat"
    TEACHING = "teaching"
    REPLAY = "replay"
    VISUAL = "visual"
    PROJECT_REVIEW = "project_review"
    MANUAL = "manual"


class EvidenceKind(str, Enum):
    RUN_RECORD = "run_record"
    EPISODE = "episode"
    ARTIFACT = "artifact"
    SCREENSHOT = "screenshot"
    LOG = "log"
    SELF_CHECK = "self_check"
    DOSSIER = "dossier"
    INCIDENT = "incident"
    USER_CLUE = "user_clue"


class IncidentStatus(str, Enum):
    OPEN = "open"
    OBSERVED = "observed"
    RECOVERED = "recovered"
    NEEDS_FIX = "needs_fix"
    RESOLVED_BY_RELEASE = "resolved_by_release"


class PersistStrategy(str, Enum):
    CLONED_PROFILE = "cloned_profile"
    STORAGE_STATE_ONLY = "storage_state_only"
    FRESH_PROFILE = "fresh_profile"


class VerificationStatus(str, Enum):
    """Epistemic verification status for test results."""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class LearningDecision(str, Enum):
    """Learning eligibility decision for verified results."""
    NOT_ELIGIBLE = "not_eligible"
    ELIGIBLE = "eligible"


class CaptureChannel(str, Enum):
    VISIBLE = "visible"
    BACKGROUND = "background"
    API = "api"


class ReplayAnnotationStatus(str, Enum):
    KNOWN = "known"
    UNCERTAIN = "uncertain"
    MISSING = "missing"
    USER_CORRECTED = "user_corrected"


class ReplayAnnotationSource(str, Enum):
    CAPTURED = "captured"
    INFERRED = "inferred"
    RECOVERED = "recovered"
    USER = "user"


class ExternalStateFlag(str, Enum):
    AWAITING_RESPONSE = "awaiting_response"
    ASSISTANT_LOGIN_REQUIRED = "assistant_login_required"
    MISSING_THREAD_TRACKING = "missing_thread_tracking"
    MISSING_PROGRAM_SESSION_PROFILE = "missing_program_session_profile"
    PREMATURE_MANUAL_FALLBACK = "premature_manual_fallback"
    FAMILY_MISMATCH = "family_mismatch"
    LEARNING_WITHOUT_CAPTURED_RESPONSE = "learning_without_captured_response"
    SESSION_EXPIRED = "session_expired"
    ACCOUNT_LIMITED = "account_limited"
    WRONG_THREAD = "wrong_thread"
    CAPTURE_UNVERIFIED = "capture_unverified"


_EXTERNAL_STATE_FLAG_ALIASES = {
    'awaiting_response': ExternalStateFlag.AWAITING_RESPONSE.value,
    'assistant_login_required': ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value,
    'login_required': ExternalStateFlag.ASSISTANT_LOGIN_REQUIRED.value,
    'missing_thread_tracking': ExternalStateFlag.MISSING_THREAD_TRACKING.value,
    'missing_program_session_profile': ExternalStateFlag.MISSING_PROGRAM_SESSION_PROFILE.value,
    'premature_manual_fallback': ExternalStateFlag.PREMATURE_MANUAL_FALLBACK.value,
    'family_mismatch': ExternalStateFlag.FAMILY_MISMATCH.value,
    'learning_without_captured_response': ExternalStateFlag.LEARNING_WITHOUT_CAPTURED_RESPONSE.value,
    'session_expired': ExternalStateFlag.SESSION_EXPIRED.value,
    'account_limited': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'credits_exhausted': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'credit_exhausted': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'quota_exhausted': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'quota_limited': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'rate_limited': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'rate_limit': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'plan_upgrade_required': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'upgrade_required': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'billing_required': ExternalStateFlag.ACCOUNT_LIMITED.value,
    'wrong_thread': ExternalStateFlag.WRONG_THREAD.value,
    'thread_mismatch': ExternalStateFlag.WRONG_THREAD.value,
    'capture_unverified': ExternalStateFlag.CAPTURE_UNVERIFIED.value,
}


def canonical_external_state_flag(value: Any) -> str:
    if isinstance(value, ExternalStateFlag):
        return value.value
    text = str(value or '').strip().lower()
    if not text:
        return ''
    base = text.split(':', 1)[0].strip()
    return _EXTERNAL_STATE_FLAG_ALIASES.get(base, '')


def canonical_external_state_flags(values: list[Any] | tuple[Any, ...] | set[Any] | None) -> list[str]:
    flags: list[str] = []
    for value in values or []:
        resolved = canonical_external_state_flag(value)
        if resolved and resolved not in flags:
            flags.append(resolved)
    return flags


class OverlayKind(str, Enum):
    CLICK_POINT = "click_point"
    RECT = "rect"
    PATH = "path"
    TEXT_SPAN = "text_span"
    SCROLL_BAND = "scroll_band"


class ToolType(str, Enum):
    BROWSER = "browser"
    CODE_EDITOR = "code_editor"
    LLM_LOCAL = "llm_local"
    LLM_WEB_UI = "llm_web_ui"
    MCP_CLIENT = "mcp_client"
    SHELL = "shell"
    FILE_SYSTEM = "file_system"
    CUSTOM = "custom"


class ToolValidationStatus(str, Enum):
    UNVALIDATED = "unvalidated"
    SANDBOX_PASS = "sandbox_pass"
    SANDBOX_FAIL = "sandbox_fail"
    APPROVED = "approved"
    BLOCKED = "blocked"


class ToolTaskStatus(str, Enum):
    PENDING = "pending"
    WAITING_SANDBOX = "waiting_sandbox"
    WAITING_APPROVAL = "waiting_approval"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    DEFERRED = "deferred"


class ToolActionType(str, Enum):
    OPEN_URL = "open_url"
    CLICK = "click"
    CLICK_POINT = "click_point"
    MOVE_MOUSE = "move_mouse"
    TYPE_TEXT = "type_text"
    SCROLL = "scroll"
    EXTRACT_TEXT = "extract_text"
    SCREENSHOT = "screenshot"
    LAUNCH_APP = "launch_app"
    FOCUS_WINDOW = "focus_window"
    WAIT_FOR_WINDOW = "wait_for_window"
    WAIT_FOR_CHANGE = "wait_for_change"
    RUN_COMMAND = "run_command"
    EDIT_CODE = "edit_code"
    MCP_CALL = "mcp_call"
    LLM_QUERY = "llm_query"
    VERIFY_STATE = "verify_state"


class InteractionChannel(str, Enum):
    UI = "ui"
    BACKGROUND = "background"
    API = "api"


class InteractionMode(str, Enum):
    UI = "ui"
    BACKGROUND = "background"
    API = "api"
    FALLBACK = "fallback"


class TaskRole(str, Enum):
    TRAINING = "training"
    KNOWLEDGE = "knowledge"
    ANALYTICS = "analytics"
    CUSTOMER_SUPPORT = "customer_support"
    PROJECT_EVOLUTION = "project_evolution"
    RESEARCH = "research"
    VISUAL = "visual"
    TOOL_USE = "tool_use"
    TOOL_SANDBOX = "tool_sandbox"


class ToolCapability(str, Enum):
    BROWSER_OBSERVATION = "browser_observation"
    KNOWLEDGE_SEARCH = "knowledge_search"
    EMBEDDINGS = "embeddings"
    SQL_READ_ONLY = "sql_read_only"
    ANALYTICS = "analytics"
    CODEX_PACKET = "codex_packet"
    CUSTOMER_TEMPLATE = "customer_template"
    PBT_TUNING = "pbt_tuning"
    VISUAL_REVIEW = "visual_review"
    TOOL_EXECUTION = "tool_execution"
    TOOL_SANDBOX = "tool_sandbox"
    LOCAL_LLM = "local_llm"
    CODE_EDIT = "code_edit"
    MCP = "mcp"
    SHELL_COMMAND = "shell_command"
    DESKTOP_AUTOMATION = "desktop_automation"


class ReportKind(str, Enum):
    CHAT = "chat"
    TRAINING_GUIDANCE = "training_guidance"
    KNOWLEDGE_BRIEF = "knowledge_brief"
    ANALYTICS_REPORT = "analytics_report"
    CUSTOMER_RESPONSE = "customer_response"
    ENGINEERING_REVIEW = "engineering_review"
    RESEARCH_BRIEF = "research_brief"
    VISUAL_ANALYSIS = "visual_analysis"
    TOOL_EXECUTION = "tool_execution"


class IntentDisposition(str, Enum):
    ANSWER_NOW = "answer_now"
    NEED_INFO = "need_info"
    PLAN_THEN_EXECUTE = "plan_then_execute"


class CapabilityStatus(str, Enum):
    INSUFFICIENT = "insufficient"
    PARTIAL = "partial"
    READY = "ready"
    READY_WITH_APPROVAL = "ready_with_approval"


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class AdaptiveSessionStatus(str, Enum):
    PLANNED = "planned"
    NEED_INFO = "need_info"
    WAITING_APPROVAL = "waiting_approval"
    READY_TO_EXECUTE = "ready_to_execute"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class ScenarioMode(str, Enum):
    REPLAY_ONLY = "replay_only"
    SIMULATE = "simulate"
    LIVE_GUIDED = "live_guided"


class DiagnosticCategory(str, Enum):
    NEED_TEACHING = "need_teaching"
    NEED_RUNTIME_TUNING = "need_runtime_tuning"
    NEED_ADAPTER = "need_adapter"
    NEED_CODEX_FIX = "need_codex_fix"
    READY_FOR_GUIDED_LIVE = "ready_for_guided_live"


class AppConfig(BaseModel):
    app_name: str = "IABV v1.5"
    workspace_root: str
    data_dir: str
    episodes_dir: str
    screenshots_dir: str
    replay_annotations_dir: str
    tool_teaching_dir: str
    browser_profiles_dir: str
    browser_states_dir: str
    browser_artifacts_dir: str
    site_policies_dir: str
    payloads_dir: str
    models_dir: str
    logs_dir: str
    evolution_dir: str
    sqlite_path: str
    chrome_default_user_data_dir: str | None = None
    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"
    lm_studio_model: str = "gemma3:4b"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_visual_model: str = "gemma3:4b"
    ollama_model: str = "qwen3:8b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    ollama_embedding_light_model: str = "embeddinggemma"
    provider_timeout_seconds: float = 45.0
    api_capture_mode: str = 'smart'
    periodic_screenshot_seconds: float = 3.0
    default_task_role: TaskRole = TaskRole.TRAINING
    autonomous_evolution_enabled: bool = True
    autonomous_external_launch: bool = True
    # Flag del ``SynapticRouter`` (PCS v1). Cuando queda en ``None`` el router
    # lee el env var ``SYNAPTIC_ROUTING`` / ``IABV_SYNAPTIC_ROUTING_ENABLED``
    # como antes. Cuando se setea explícitamente (``True``/``False``) tiene
    # precedencia sobre el env var. Default ``None`` preserva comportamiento
    # previo.
    synaptic_routing_enabled: bool | None = None


class ThemeConfig(BaseModel):
    primary_background: str = "#111417"
    secondary_background: str = "#1a2025"
    panel_background: str = "#20282e"
    frosted_overlay: str = "#2b343bcc"
    text_primary: str = "#fff7ef"
    text_secondary: str = "#d7d0c7"
    accent_cyan: str = "#76d9d6"
    accent_amber: str = "#d7a65a"
    border_soft: str = "#ffffff14"
    success_color: str = "#8ccf8b"
    warning_color: str = "#d7a65a"
    danger_color: str = "#d57c6c"
    title_font_family: str = "Bahnschrift"
    body_font_family: str = "Candara"


class ProviderConfig(BaseModel):
    name: str
    kind: ProviderKind
    base_url: str
    model: str
    enabled: bool = True
    requires_api_key: bool = False
    api_key: str | None = None
    supports_vision: bool = True
    supports_tools: bool = True
    optional: bool = False


class ModelProfile(BaseModel):
    profile_id: str
    label: str
    backend: str
    model_name: str
    summary: str
    supports_vision: bool = False
    supports_embeddings: bool = False
    quantization: str = "Q4"


class RoleProfile(BaseModel):
    role: TaskRole
    title: str
    summary: str
    preferred_model_profile_id: str
    default_tools: list[ToolCapability] = Field(default_factory=list)


class BrowserProfileConfig(BaseModel):
    profile_id: str
    site_id: str
    channel: str = "chrome"
    user_data_dir: str | None = None
    storage_state_path: str | None = None
    source_user_data_dir: str | None = None
    source_profile_dir: str | None = None
    login_check_selector: str | None = None
    logout_check_selector: str | None = None
    persist_strategy: PersistStrategy = PersistStrategy.CLONED_PROFILE
    headless: bool = False
    launch_args: list[str] = Field(default_factory=list)


class SitePolicy(BaseModel):
    site_id: str
    display_name: str
    domains: list[str] = Field(default_factory=list)
    login_url: str | None = None
    login_selector: str | None = None
    logout_selector: str | None = None
    username_selectors: list[str] = Field(default_factory=list)
    sensitive_selectors: list[str] = Field(default_factory=list)
    sensitive_names: list[str] = Field(default_factory=list)
    capture_network: bool = True
    capture_dom: bool = True
    capture_console: bool = True
    capture_storage: bool = True
    redact_emails: bool = True
    redact_tokens: bool = True
    notes: str = ""


class SecretReference(BaseModel):
    ref_id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str = "keyring"
    domain: str
    account: str
    field_role: str
    key: str
    created_at_utc: datetime = Field(default_factory=utc_now)
    available: bool = True


class SensitiveFieldMatch(BaseModel):
    sensitive: bool = False
    field_role: str = "generic"
    reasons: list[str] = Field(default_factory=list)
    value_length: int | None = None
    policy_source: str | None = None


class SiteSessionResult(BaseModel):
    site_id: str
    authenticated: bool
    requires_manual_login: bool = False
    storage_state_path: str | None = None
    reason: str = ""
    current_url: str | None = None


class ProviderHealth(BaseModel):
    provider_name: str
    status: ProviderStatus
    available: bool
    latency_ms: float | None = None
    detail: str = ""


class EnvironmentRiskSignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: str
    severity: IssueSeverity = IssueSeverity.LOW
    summary: str = ""
    metric_value: float | int | str | None = None
    threshold: float | int | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnvironmentCapability(BaseModel):
    capability_id: str
    title: str
    available: bool = False
    status: str = "missing"
    summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnvironmentSelfModel(BaseModel):
    environment_id: str = ""
    known_environment: bool = False
    scan_status: str = "bootstrapping"
    hardware_profile: dict[str, Any] = Field(default_factory=dict)
    runtime_profile: dict[str, Any] = Field(default_factory=dict)
    capability_graph: list[EnvironmentCapability] = Field(default_factory=list)
    available_tools: list[dict[str, Any]] = Field(default_factory=list)
    missing_tools: list[dict[str, Any]] = Field(default_factory=list)
    installable_tools: list[dict[str, Any]] = Field(default_factory=list)
    ai_capacity: dict[str, Any] = Field(default_factory=dict)
    risk_signals: list[EnvironmentRiskSignal] = Field(default_factory=list)
    notifications: list[str] = Field(default_factory=list)
    last_scan: datetime = Field(default_factory=utc_now)
    changed_since_last_scan: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WindowObservation(BaseModel):
    window_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    app_name: str = ""
    pid: int = 0
    focused: bool = False
    visible: bool = True
    tool_id: str = ""
    assistant_kind: str = ""
    state: str = ""
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolLiveStatus(BaseModel):
    tool_id: str
    title: str = ""
    assistant_kind: str = ""
    available: bool = False
    status: str = "no_disponible"
    detail: str = ""
    launch_mode: str = ""
    window_open: bool = False
    focused: bool = False
    thread_status: str = "no_disponible"
    messages_status: str = "no_disponible"
    session_status: str = "no_disponible"
    capture_status: str = "no_disponible"
    probe_status: str = "no_verificado"
    permission_state: str = "no_requerido"
    observed_via: list[str] = Field(default_factory=list)
    last_verified_at: datetime | None = None
    external_state_flags: list[str] = Field(default_factory=list)
    detected_blocks: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class NetworkStatusSnapshot(BaseModel):
    connected: bool = False
    status: str = "desconocido"
    quality: str = "desconocida"
    latency_ms: float | None = None
    detail: str = ""
    evidence: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BackgroundProcessSnapshot(BaseModel):
    process_name: str = ""
    pid: int = 0
    cpu_percent: float | None = None
    cpu_load_percent: float | None = None
    memory_mb: float | None = None
    gpu_percent: float | None = None
    responding: bool | None = None
    state: str = ""
    detail: str = ""
    interferes_with_capture: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalBlockRecord(BaseModel):
    block_id: str = Field(default_factory=lambda: str(uuid4()))
    block_type: str = ""
    target_scope: str = ""
    assistant_kind: str = ""
    title: str = ""
    detail: str = ""
    status: str = "active"
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObservationPermissionGate(BaseModel):
    scope: str = ""
    assistant_kind: str = ""
    title: str = ""
    detail: str = ""
    status: str = "no_requerido"
    required_for: list[str] = Field(default_factory=list)
    granted: bool = False
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorldModelSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    active_windows: list[WindowObservation] = Field(default_factory=list)
    focused_window: WindowObservation | None = None
    tool_live_status: list[ToolLiveStatus] = Field(default_factory=list)
    network_status: NetworkStatusSnapshot = Field(default_factory=NetworkStatusSnapshot)
    background_processes: list[BackgroundProcessSnapshot] = Field(default_factory=list)
    detected_blocks: list[str] = Field(default_factory=list)
    block_records: list[OperationalBlockRecord] = Field(default_factory=list)
    permission_gates: list[ObservationPermissionGate] = Field(default_factory=list)
    observation_sources: list[str] = Field(default_factory=list)
    inferred_state: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    freshness_ms: int = 0
    last_updated: datetime = Field(default_factory=utc_now)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    worker_pool_snapshot: dict[str, Any] = Field(default_factory=dict)


class RouteDecision(BaseModel):
    primary_provider: str
    primary_kind: ProviderKind
    fallback_provider: str | None = None
    reason: str
    fallback_enabled: bool = True


class RoleRoute(BaseModel):
    task_role: TaskRole
    role_title: str
    provider_name: str
    model_profile_id: str
    model_name: str
    tool_chain: list[ToolCapability] = Field(default_factory=list)
    reason: str
    fallback_provider_name: str | None = None
    used_fallback: bool = False


class IntentRouteDecision(BaseModel):
    detected_role: TaskRole
    planner_required: bool = False
    visual_required: bool = False
    tool_chain: list[ToolCapability] = Field(default_factory=list)
    reason: str = ""


class ObjectiveNodeKind(str, Enum):
    OBJECTIVE = "objective"
    PROJECT = "project"
    TASK = "task"
    SUBTASK = "subtask"


class ObjectiveStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    PAUSED = "paused"


class ObjectiveNode(BaseModel):
    objective_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: ObjectiveNodeKind = ObjectiveNodeKind.OBJECTIVE
    title: str
    summary: str = ""
    parent_id: str | None = None
    root_id: str = ""
    site_id: str | None = None
    priority: int = 50
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    progress: float = 0.0
    blocker: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)


class GoalContext(BaseModel):
    goal_context_id: str = Field(default_factory=lambda: str(uuid4()))
    objective: dict[str, Any] = Field(default_factory=dict)
    project: dict[str, Any] = Field(default_factory=dict)
    task: dict[str, Any] = Field(default_factory=dict)
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    active_node_id: str = ""
    active_title: str = ""
    priority: int = 50
    status: str = ObjectiveStatus.PENDING.value
    progress: float = 0.0
    blocker: str = ""
    confidence: float = 0.0
    trend: str = "sin base"
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionContext(BaseModel):
    decision_context_id: str = Field(default_factory=lambda: str(uuid4()))
    user_goal: str
    intent: TaskIntent
    route_decision: IntentRouteDecision
    chosen_pack_id: str = ""
    chosen_pack_title: str = ""
    site_id: str = ""
    site_display_name: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    capability_snapshot: list[CapabilityReadiness] = Field(default_factory=list)
    live_audit: dict[str, Any] = Field(default_factory=dict)
    assistant_guidance: dict[str, Any] = Field(default_factory=dict)
    goal_context: GoalContext = Field(default_factory=GoalContext)
    memory_snapshot: dict[str, Any] = Field(default_factory=dict)
    governance: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapturedStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    timestamp_utc: datetime = Field(default_factory=utc_now)
    action_type: str
    target: str | None = None
    text_value: str | None = None
    screenshot_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EpisodeManifest(BaseModel):
    episode_id: str
    title: str
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    step_count: int = 0
    source: str = "desktop"
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class SessionArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    kind: str
    path: str
    created_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DomSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    url: str
    title: str = ""
    frame_id: str | None = None
    html_excerpt: str = ""
    visible_text_excerpt: str = ""
    form_fields: list[dict[str, Any]] = Field(default_factory=list)
    storage_keys: dict[str, list[str]] = Field(default_factory=dict)
    cookies_summary: list[dict[str, Any]] = Field(default_factory=list)
    frame_count: int = 0
    frame_sources: list[dict[str, Any]] = Field(default_factory=list)
    captured_at_utc: datetime = Field(default_factory=utc_now)


class NetworkExchange(BaseModel):
    exchange_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    url: str
    method: str
    resource_type: str | None = None
    status_code: int | None = None
    request_headers: dict[str, str] = Field(default_factory=dict)
    response_headers: dict[str, str] = Field(default_factory=dict)
    request_body: str | None = None
    response_body: str | None = None
    graphql_operation: str | None = None
    started_at_utc: datetime = Field(default_factory=utc_now)
    finished_at_utc: datetime | None = None
    redacted: bool = False
    content_type: str | None = None


class BrowserObservationBundle(BaseModel):
    bundle_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    url: str
    capture_channels: list[CaptureChannel] = Field(default_factory=list)
    dom_snapshots: list[DomSnapshot] = Field(default_factory=list)
    network_exchanges: list[NetworkExchange] = Field(default_factory=list)
    console_messages: list[dict[str, Any]] = Field(default_factory=list)
    storage_summary: dict[str, Any] = Field(default_factory=dict)
    capture_stats: dict[str, Any] = Field(default_factory=dict)
    generated_at_utc: datetime = Field(default_factory=utc_now)


class RedactionSummary(BaseModel):
    redacted_steps: int = 0
    redacted_network_fields: int = 0
    stored_secrets: int = 0
    warnings: list[str] = Field(default_factory=list)


class ClarificationItem(BaseModel):
    clarification_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    options: list[str] = Field(default_factory=list)
    blocking: bool = False


class KnowledgeItem(BaseModel):
    knowledge_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    summary: str
    source_episode_id: str | None = None
    task_label: str | None = None
    confidence: float = 0.0
    tags: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)


class EvidenceRef(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: EvidenceKind
    label: str
    ref_id: str = ""
    path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IssueCandidate(BaseModel):
    issue_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    summary: str
    probable_cause: str = ""
    severity: IssueSeverity = IssueSeverity.MEDIUM
    issue_hint: str = ""
    repeated_count: int = 1
    evidence_ids: list[str] = Field(default_factory=list)


class ImprovementProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    rationale: str
    recommended_change: str
    suggested_tests: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    priority_score: int = 50


class SelfCheckResult(BaseModel):
    check_id: str = Field(default_factory=lambda: str(uuid4()))
    check_name: str
    status: RunStatus = RunStatus.SUCCESS
    detail: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class EvolutionSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    summary: str = ""
    status_cards: list[dict[str, Any]] = Field(default_factory=list)
    recent_failures: list[dict[str, Any]] = Field(default_factory=list)
    repeated_issues: list[dict[str, Any]] = Field(default_factory=list)
    backlog: list[ImprovementProposal] = Field(default_factory=list)
    latest_packet_preview: str = ""


class RuntimeSignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    episode_id: str | None = None
    run_id: str | None = None
    site_id: str = "generic_web"
    signal_kind: str
    summary: str
    severity: IssueSeverity = IssueSeverity.LOW
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionHealthSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    episode_id: str | None = None
    run_id: str | None = None
    site_id: str = "generic_web"
    health_label: str = "Sin incidencias"
    health_flags: list[str] = Field(default_factory=list)
    status: str = "idle"
    visible_step_count: int = 0
    screenshot_count: int = 0
    api_seen_count: int = 0
    api_saved_count: int = 0
    api_dropped_count: int = 0
    page_count: int = 0
    observed_page_count: int = 0
    queue_depth: int = 0
    frames_detected: int = 0
    heartbeat_count: int = 0
    last_active_url: str = ""
    recent_urls: list[str] = Field(default_factory=list)
    detail: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)


class HiddenIncident(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    episode_id: str | None = None
    run_id: str | None = None
    site_id: str = "generic_web"
    incident_kind: str
    severity: IssueSeverity = IssueSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    summary: str
    probable_cause: str = ""
    detail: str = ""
    affected_url: str = ""
    recent_urls: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    signal_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserClue(BaseModel):
    clue_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    text: str
    episode_id: str | None = None
    run_id: str | None = None
    linked_incident_id: str | None = None
    site_id: str = "generic_web"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayAnnotation(BaseModel):
    annotation_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    episode_id: str
    step_id: str | None = None
    screenshot_path: str = ""
    group_key: str = ""
    linked_screenshot_id: str = ""
    status: ReplayAnnotationStatus = ReplayAnnotationStatus.UNCERTAIN
    source: ReplayAnnotationSource = ReplayAnnotationSource.USER
    overlay_kind: OverlayKind = OverlayKind.RECT
    confidence_score: float = 0.0
    overlay_rect: dict[str, float] = Field(default_factory=dict)
    overlay_point: dict[str, float] = Field(default_factory=dict)
    overlay_label: str = ""
    overlay_notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayFrame(BaseModel):
    frame_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    group_key: str
    screenshot_path: str = ""
    screenshot_name: str = ""
    screenshot_url: str = ""
    step_ids: list[str] = Field(default_factory=list)
    overlay_count: int = 0
    annotation_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayFrameGroup(BaseModel):
    group_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    group_key: str
    title: str = ""
    frames: list[ReplayFrame] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayReviewDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    episode_id: str
    step_id: str | None = None
    annotation_id: str | None = None
    decision: str = "reviewed"
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayVisualSummary(BaseModel):
    summary_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str
    total_frames: int = 0
    useful_frames: int = 0
    contextual_frames: int = 0
    total_overlays: int = 0
    known_count: int = 0
    uncertain_count: int = 0
    missing_count: int = 0
    user_corrected_count: int = 0
    green_count: int = 0
    orange_count: int = 0
    red_count: int = 0
    manual_correction_count: int = 0
    learning_coverage_score: float = 0.0
    visual_alignment_score: float = 0.0
    critical_object_coverage: float = 0.0
    login_visual_completeness: float = 0.0
    critical_objects: list[str] = Field(default_factory=list)
    corrected_objects: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentSuggestion(BaseModel):
    suggestion_id: str = Field(default_factory=lambda: str(uuid4()))
    incident_kind: str
    title: str
    probable_cause: str = ""
    impact: str = ""
    frequency: int = 1
    recommended_change: str = ""
    suggested_tests: list[str] = Field(default_factory=list)
    priority_score: int = 50


class IncidentQuery(BaseModel):
    issue_hint: str = ""
    incident_id: str | None = None
    incident_kind: str = ""
    pending_issue_id: str | None = None
    episode_id: str | None = None
    run_id: str | None = None
    task_role: TaskRole | None = None
    status: RunStatus | None = None
    recent_hours: int | None = None
    limit: int = 10


class ScenarioDefinition(BaseModel):
    scenario_id: str
    title: str
    summary: str = ""
    site_id: str | None = None
    intent_keys: list[str] = Field(default_factory=list)
    mode: ScenarioMode = ScenarioMode.REPLAY_ONLY
    approval_required: bool = False
    expected_signals: list[str] = Field(default_factory=list)
    failure_signals: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObservedMismatch(BaseModel):
    mismatch_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    expected: str = ""
    observed: str = ""
    probable_cause: str = ""
    severity: IssueSeverity = IssueSeverity.MEDIUM
    category: DiagnosticCategory = DiagnosticCategory.NEED_CODEX_FIX
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProbeDiagnosis(BaseModel):
    diagnosis_id: str = Field(default_factory=lambda: str(uuid4()))
    scenario_id: str = ""
    category: DiagnosticCategory = DiagnosticCategory.NEED_TEACHING
    summary: str = ""
    probable_cause: str = ""
    confidence: float = 0.0
    mismatches: list[ObservedMismatch] = Field(default_factory=list)
    recommended_action: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeAdjustment(BaseModel):
    adjustment_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    target_key: str
    previous_value: Any | None = None
    new_value: Any | None = None
    reason: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    reversible: bool = True
    helped: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeTuningProfile(BaseModel):
    profile_id: str = Field(default_factory=lambda: str(uuid4()))
    scope_key: str = "global"
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    adjustments: list[RuntimeAdjustment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiagnosticEpisode(BaseModel):
    diagnostic_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    scenario_id: str
    goal: str
    expected_signals: list[str] = Field(default_factory=list)
    observed_signals: list[str] = Field(default_factory=list)
    interpretation: str = ""
    diagnosis: ProbeDiagnosis
    run_id: str | None = None
    session_id: str | None = None
    episode_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexPendingIssue(BaseModel):
    issue_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    status: IncidentStatus = IncidentStatus.NEEDS_FIX
    scenario_id: str = ""
    goal: str = ""
    category: DiagnosticCategory = DiagnosticCategory.NEED_CODEX_FIX
    summary: str
    probable_cause: str = ""
    unresolved_reason: str = ""
    run_id: str | None = None
    episode_id: str | None = None
    session_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    runtime_adjustments: list[RuntimeAdjustment] = Field(default_factory=list)
    recommended_change: str = ""
    suggested_tests: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioRun(BaseModel):
    scenario_run_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    scenario: ScenarioDefinition
    goal: str
    mode: ScenarioMode = ScenarioMode.REPLAY_ONLY
    status: RunStatus = RunStatus.PARTIAL
    summary: str = ""
    run_id: str | None = None
    session_id: str | None = None
    diagnosis: ProbeDiagnosis | None = None
    runtime_adjustments: list[RuntimeAdjustment] = Field(default_factory=list)
    diagnostic_episode: DiagnosticEpisode | None = None
    pending_issue_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GuidedImprovementFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: str
    severity: IssueSeverity = IssueSeverity.MEDIUM
    summary: str = ""
    repeated_count: int = 0
    source: str = ""
    safe_to_apply: bool = False
    external_state_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GuidedImprovementProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    action_key: str
    title: str
    summary: str = ""
    rationale: str = ""
    safe_to_apply: bool = False
    reversible: bool = True
    verifiable: bool = True
    requires_user_decision: bool = False
    applied: bool = False
    blocked_reason: str = ""
    verification_steps: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GuidedImprovementCycle(BaseModel):
    cycle_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    run_id: str = ""
    session_id: str = ""
    scenario_run_id: str = ""
    scenario_id: str = ""
    comparison_scope_key: str = ""
    trace_id: str = ""
    status: str = "observed"
    detected_blockages: list[GuidedImprovementFinding] = Field(default_factory=list)
    proposed_corrections: list[GuidedImprovementProposal] = Field(default_factory=list)
    notifications: list[str] = Field(default_factory=list)
    external_state_flags: list[str] = Field(default_factory=list)
    applied_count: int = 0
    requires_user_decision: bool = False
    lab_run_id: str = ""
    lab_recommendation_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionState(BaseModel):
    state: str = "planned"
    detail: str = ""
    executor_name: str = ""
    sandboxed: bool = False
    validated: bool = False
    approval_decision: ApprovalDecision = ApprovalDecision.PENDING
    destructive_blocked: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCard(BaseModel):
    tool_id: str
    title: str
    tool_type: ToolType
    description: str = ""
    adapter_key: str
    validation_status: ToolValidationStatus = ToolValidationStatus.UNVALIDATED
    local_first: bool = True
    available: bool = True
    supports_sandbox: bool = True
    supports_write: bool = False
    requires_human_approval: bool = False
    supports_rollback: bool = False
    capabilities: list[str] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    last_result_id: str | None = None
    last_validated_at_utc: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def dry_check(self) -> "ToolCheckResult":
        """Revisa sin side effects si la tool declara estar disponible.

        Hook extensible para overrides puntuales: por default refleja el
        estado declarativo actual (`available` + `validation_status`). No
        toca red ni sistema; el probe real vive en los adapters.
        """

        if self.available:
            status = "ready"
            reason: str | None = None
        else:
            status = "missing"
            reason = "adapter reported tool as not available"
        return ToolCheckResult(
            tool_id=self.tool_id,
            available=bool(self.available),
            status=status,
            reason=reason,
            evidence={
                "adapter_key": self.adapter_key,
                "validation_status": self.validation_status.value,
                "tool_type": self.tool_type.value,
            },
        )


class ToolAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: ToolActionType
    label: str
    target: str = ""
    value: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    expected_signal: str = ""
    destructive: bool = False
    requires_approval: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_id: str
    title: str
    objective: str
    requested_by_role: TaskRole = TaskRole.TOOL_USE
    status: ToolTaskStatus = ToolTaskStatus.PENDING
    actions: list[ToolAction] = Field(default_factory=list)
    rollback_actions: list[ToolAction] = Field(default_factory=list)
    execution_scope: str = "read_only"
    approval_decision: ApprovalDecision = ApprovalDecision.PENDING
    sandbox_first: bool = True
    site_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    pack_id: str = ""
    expected_outcome: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    tool_id: str
    tool_type: ToolType
    success: bool
    validation_status: ToolValidationStatus = ToolValidationStatus.UNVALIDATED
    execution_state: ExecutionState = Field(default_factory=ExecutionState)
    rollback_state: ExecutionState | None = None
    output_text: str = ""
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    error_message: str = ""
    execution_ms: int = 0
    created_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UniversalInteractionStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    channel: InteractionChannel
    operation: str
    target: str = ""
    value_hint: str = ""
    expected_signal: str = ""
    confidence: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionPattern(BaseModel):
    pattern_id: str = Field(default_factory=lambda: str(uuid4()))
    signature: str
    title: str
    channel: InteractionChannel
    tool_id: str
    tool_type: ToolType
    site_id: str | None = None
    operations: list[UniversalInteractionStep] = Field(default_factory=list)
    reusable: bool = True
    success_count: int = 0
    failure_count: int = 0
    last_task_id: str | None = None
    last_result_id: str | None = None
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid4()))
    pattern_id: str
    task_id: str
    result_id: str
    episode_id: str | None = None
    success: bool
    channel: InteractionChannel
    tool_id: str
    tool_type: ToolType
    site_id: str | None = None
    summary: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    created_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionAction(UniversalInteractionStep):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at_utc: datetime | None = None
    finished_at_utc: datetime | None = None
    destructive: bool = False
    requires_approval: bool = False


class InteractionEvidence(EvidenceRef):
    confidence: float = 0.0


class AnnotationConfidence(str, Enum):
    CONFIRMED = "confirmed"
    DOUBTFUL = "doubtful"
    INSUFFICIENT = "insufficient"


class VisualObjectAnnotation(BaseModel):
    annotation_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str = ""
    overlay_kind: OverlayKind = OverlayKind.RECT
    overlay_rect: dict[str, float] = Field(default_factory=dict)
    overlay_point: dict[str, float] = Field(default_factory=dict)
    detected_by: str = "runtime_hint"
    confidence_score: float = 0.0
    confidence: AnnotationConfidence = AnnotationConfidence.INSUFFICIENT
    screenshot_ref: str = ""
    matched_user_click: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserClickTrace(BaseModel):
    click_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str = ""
    target: str = ""
    screenshot_ref: str = ""
    x: int = 0
    y: int = 0
    normalized_x: float = 0.0
    normalized_y: float = 0.0
    derived_from_rect: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectIdentityLink(BaseModel):
    link_id: str = Field(default_factory=lambda: str(uuid4()))
    annotation_id: str = ""
    click_id: str = ""
    matched: bool = False
    distance_score: float = 0.0
    rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossCheckResult(BaseModel):
    cross_check_id: str = Field(default_factory=lambda: str(uuid4()))
    status: AnnotationConfidence = AnnotationConfidence.INSUFFICIENT
    matched: bool = False
    annotation_id: str = ""
    click_id: str = ""
    discrepancy: str = ""
    rationale: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningAdjustment(BaseModel):
    adjustment_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: str = ""
    reason: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualTeachingFrame(BaseModel):
    frame_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str = ""
    step_id: str = ""
    objective: str = ""
    mode_used: InteractionChannel = InteractionChannel.UI
    screenshot_ref: str = ""
    detected_objects: list[VisualObjectAnnotation] = Field(default_factory=list)
    user_click: UserClickTrace | None = None
    object_links: list[ObjectIdentityLink] = Field(default_factory=list)
    cross_check: CrossCheckResult | None = None
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TeachingEvidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str = ""
    frame_id: str = ""
    summary: str = ""
    screenshot_ref: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class TeachingEpisode(BaseModel):
    teaching_episode_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str = ""
    objective: str = ""
    mode_used: InteractionChannel = InteractionChannel.UI
    frames: list[VisualTeachingFrame] = Field(default_factory=list)
    evidence: list[TeachingEvidence] = Field(default_factory=list)
    cross_check_summary: dict[str, Any] = Field(default_factory=dict)
    learning_status: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionPolicyDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    requires_human_approval: bool = False
    approval_decision: ApprovalDecision = ApprovalDecision.SKIPPED
    blocked: bool = False
    rationale: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningSignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    channel: InteractionChannel
    signal_type: str = "interaction"
    confidence: float = 0.0
    source: str = "runtime"
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveAuditFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: str
    title: str
    summary: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveAuditDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    rationale: str = ""
    confidence: float = 0.0
    recommended_tool_id: str = ""
    approval_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveAuditSnapshot(BaseModel):
    audit_snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    objective: str
    session_or_episode_id: str = ""
    mode_used: str = ""
    evidence: list[str] = Field(default_factory=list)
    findings: list[LiveAuditFinding] = Field(default_factory=list)
    decision: LiveAuditDecision | None = None
    confidence: float = 0.0
    auto_safe_action: str = ""
    human_approval: bool = False
    reused_pattern: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditIssue(BaseModel):
    issue_id: str = Field(default_factory=lambda: str(uuid4()))
    step_id: str = ""
    severity: str = "info"
    description: str = ""
    algorithm_source: str = ""
    suggested_action: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BackgroundAuditResult(BaseModel):
    step_id: str
    field_type_detected: str = "UNKNOWN"
    confidence: float = 0.0
    intent_label: str = ""
    algorithms_used: list[str] = Field(default_factory=list)
    passed: bool = False
    discrepancies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualAnnotation(BaseModel):
    annotation_id: str = Field(default_factory=lambda: str(uuid4()))
    step_id: str = ""
    annotation_type: str = "warning"
    color: str = "#f59e0b"
    icon: str = "?"
    label: str = ""
    tooltip: str = ""
    confidence_bar: float = 0.0
    target_selector: str | None = None
    bounding_box: dict[str, Any] | None = None
    anchor_point: dict[str, Any] | None = None
    overlay_kind: OverlayKind = OverlayKind.RECT
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditReport(BaseModel):
    audit_report_id: str = Field(default_factory=lambda: str(uuid4()))
    episode_id: str = ""
    total_steps: int = 0
    steps_matching: int = 0
    steps_diverging: int = 0
    steps_uncertain: int = 0
    overall_confidence: float = 0.0
    audit_passed: bool = False
    issues: list[AuditIssue] = Field(default_factory=list)
    background_results: list[BackgroundAuditResult] = Field(default_factory=list)
    algorithm_agreement_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    suggested_improvements: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditedReplayResult(BaseModel):
    episode_id: str
    timeline_steps: list[dict[str, Any]] = Field(default_factory=list)
    frames: list[dict[str, Any]] = Field(default_factory=list)
    summary: ReplayVisualSummary | None = None
    audit_report: AuditReport | None = None
    cross_check_result: CrossCheckResult | None = None
    audit_annotations: list[VisualAnnotation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class CapabilityDescriptor(BaseModel):
    descriptor_id: str = Field(default_factory=lambda: str(uuid4()))
    capability_id: str
    title: str
    channel: InteractionChannel
    tool_ids: list[str] = Field(default_factory=list)
    primary_operations: list[str] = Field(default_factory=list)
    reusable_pattern_ids: list[str] = Field(default_factory=list)
    learning_signals: list[LearningSignal] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModeSelectionDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    selector_name: str = "universal_mode_selector"
    selected_mode: InteractionMode = InteractionMode.FALLBACK
    selected_tool_id: str = ""
    selected_tool_type: ToolType = ToolType.CUSTOM
    adapter_exists: bool = False
    available: bool = False
    fallback_used: bool = False
    already_resolved: bool = False
    equivalent_pattern_exists: bool = False
    improvement_already_implemented: bool = False
    reusable_pattern_id: str | None = None
    reusable_episode_id: str | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionResult(BaseModel):
    interaction_result_id: str = Field(default_factory=lambda: str(uuid4()))
    success: bool
    execution_state: ExecutionState = Field(default_factory=ExecutionState)
    summary: str = ""
    errors: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    execution_ms: int = 0
    rollback_state: ExecutionState | None = None
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionEpisode(BaseModel):
    interaction_episode_id: str = Field(default_factory=lambda: str(uuid4()))
    objective: str
    mode_used: InteractionChannel
    environment: dict[str, Any] = Field(default_factory=dict)
    captured_metadata: dict[str, Any] = Field(default_factory=dict)
    actions: list[InteractionAction] = Field(default_factory=list)
    result: InteractionResult | None = None
    errors: list[str] = Field(default_factory=list)
    evidence: list[InteractionEvidence] = Field(default_factory=list)
    learning_signals: list[LearningSignal] = Field(default_factory=list)
    confidence: float = 0.0
    human_approval: bool = False
    policy_decision: InteractionPolicyDecision | None = None
    selector_name: str = "universal_mode_selector"
    selector_reason: str = ""
    pattern_id: str | None = None
    reused_pattern: bool = False
    tool_id: str = ""
    tool_type: ToolType = ToolType.CUSTOM
    task_id: str | None = None
    result_id: str | None = None
    site_id: str | None = None
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexFileScope(BaseModel):
    path: str
    writable: bool = False
    reason: str = ""


class CodexAcceptanceCriteria(BaseModel):
    criterion_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexConstraints(BaseModel):
    read_only_paths: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CodexTestPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    commands: list[str] = Field(default_factory=list)
    expected_outcomes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexContextPack(BaseModel):
    context_pack_id: str = Field(default_factory=lambda: str(uuid4()))
    summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    interaction_episode_ids: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexTaskSpec(BaseModel):
    codex_task_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    goal: str
    file_scope: list[CodexFileScope] = Field(default_factory=list)
    constraints: CodexConstraints = Field(default_factory=CodexConstraints)
    acceptance_criteria: list[CodexAcceptanceCriteria] = Field(default_factory=list)
    test_plan: CodexTestPlan | None = None
    context_pack: CodexContextPack | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexRunResult(BaseModel):
    codex_run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: RunStatus = RunStatus.PARTIAL
    summary: str = ""
    changed_files: list[str] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    acceptance_results: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: str(uuid4()))
    disposition: IntentDisposition = IntentDisposition.ANSWER_NOW
    intent_key: str = "general.assistance"
    title: str = "Asistencia general"
    summary: str = ""
    detected_role: TaskRole = TaskRole.KNOWLEDGE
    site_hint: str | None = None
    domain_hint: str = "general"
    confidence: float = 0.5
    sensitive: bool = False
    monetary: bool = False
    multi_step: bool = False
    missing_requirements: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    hypotheses: list["IntentHypothesis"] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntentHypothesis(BaseModel):
    intent_key: str
    title: str
    confidence: float = 0.0
    rationale: str = ""


class IntentSchema(BaseModel):
    primary_intent: str = "general.assistance"
    sub_intents: list[str] = Field(default_factory=list)
    ambiguity_score: float = 0.0
    requires_clarification: bool = False
    clarification_prompt: str = ""
    risk_level: str = "low"
    confidence: float = 0.0
    semantic_source: str = "keywords"
    compound: bool = False
    constraints: list[str] = Field(default_factory=list)
    objective_summary: str = ""
    context_carried_from_history: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityReadiness(BaseModel):
    capability_id: str
    title: str
    status: CapabilityStatus = CapabilityStatus.INSUFFICIENT
    score: float = 0.0
    site_id: str | None = None
    evidence: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    last_episode_id: str | None = None
    suggested_next_step: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskContext(BaseModel):
    context_id: str = Field(default_factory=lambda: str(uuid4()))
    site_id: str | None = None
    site_display_name: str = ""
    recent_teachings: list[dict[str, Any]] = Field(default_factory=list)
    recent_runs: list[dict[str, Any]] = Field(default_factory=list)
    recent_incidents: list[dict[str, Any]] = Field(default_factory=list)
    recent_dossiers: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_hits: list[dict[str, Any]] = Field(default_factory=list)
    capability_snapshot: list[CapabilityReadiness] = Field(default_factory=list)
    interaction_patterns: list[dict[str, Any]] = Field(default_factory=list)
    experiment_insights: list[dict[str, Any]] = Field(default_factory=list)
    session_readiness: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: list[str] = Field(default_factory=list)
    live_audit: dict[str, Any] = Field(default_factory=dict)
    goal_context: GoalContext = Field(default_factory=GoalContext)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssistantConfigurationSnapshot(BaseModel):
    planning_mode: str = "without_plan"
    attachments_mode: str = "without_files"
    reasoning_level: str = "normal"
    context_mode: str = "short"
    tools_mode: str = "without_tools"
    browser_mode: str = "without_browser"
    assistant_mode: str = "general"
    origin_mode: str = "external"
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UniversalPerceptionSignal(BaseModel):
    source: str = ""
    source_app: str = ""
    capture_available: bool = False
    dom_available: bool = False
    latest_url: str = ""
    latest_title: str = ""
    visible_targets: list[str] = Field(default_factory=list)
    login_detected: bool = False
    learning_ready: bool = False
    cross_check_status: str = ""
    visual_evidence_refs: list[str] = Field(default_factory=list)
    visual_snapshot: dict[str, Any] = Field(default_factory=dict)
    dom_summary: dict[str, Any] = Field(default_factory=dict)
    available_actions: list[dict[str, Any]] = Field(default_factory=list)
    detected_blocks: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualSignalSnapshot(UniversalPerceptionSignal):
    pass


class IATraceEntry(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    assistant_kind: str = ""
    requested_assistant_kind: str = ""
    actual_assistant_kind: str = ""
    assistant_configuration: AssistantConfigurationSnapshot = Field(default_factory=AssistantConfigurationSnapshot)
    config_signature: str = ""
    comparison_scope_key: str = ""
    source_trace_ids: list[str] = Field(default_factory=list)
    route: str = ""
    tool_id: str = ""
    task_id: str = ""
    result_id: str = ""
    session_scope: str = ""
    thread_key: str = ""
    thread_title: str = ""
    capture_lane: str = ""
    state: str = ""
    detail: str = ""
    proposal_summary: str = ""
    outcome_summary: str = ""
    result_label: str = ""
    success: bool = False
    execution_ms: int = 0
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    reused_later: bool = False
    verdict: str = ""
    coherence_flags: list[str] = Field(default_factory=list)
    external_state_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerceptionSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    task_context: TaskContext
    decision_context: DecisionContext
    goal_context: GoalContext
    memory_snapshot: dict[str, Any] = Field(default_factory=dict)
    live_audit: dict[str, Any] = Field(default_factory=dict)
    runtime_signals: list[RuntimeSignal] = Field(default_factory=list)
    session_health: SessionHealthSnapshot | None = None
    ia_trace: list[IATraceEntry] = Field(default_factory=list)
    visual_signal: VisualSignalSnapshot = Field(default_factory=VisualSignalSnapshot)
    environment_self_model: EnvironmentSelfModel = Field(default_factory=EnvironmentSelfModel)
    world_model: WorldModelSnapshot = Field(default_factory=WorldModelSnapshot)
    external_state_flags: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PortableContextSection(BaseModel):
    section_id: str = ""
    title: str = ""
    summary: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
    source_kind: str = ""
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    last_updated: datetime = Field(default_factory=utc_now)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PortableContextPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    package_version: str = "portable_context.v1"
    project_id: str = "IABV_v1.5"
    summary: str = ""
    sections: list[PortableContextSection] = Field(default_factory=list)
    assistant_brief: str = ""
    package_path: str = ""
    markdown_path: str = ""
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SelfExaminationFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    category: str = ""
    title: str = ""
    summary: str = ""
    severity: IssueSeverity = IssueSeverity.MEDIUM
    confidence: float = 0.0
    recommendation: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    linked_run_ids: list[str] = Field(default_factory=list)
    status: str = "observed"
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SelfExaminationSnapshot(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    package_version: str = "self_examination.v1"
    summary: str = ""
    status: str = "idle"
    assistant_brief: str = ""
    findings: list[SelfExaminationFinding] = Field(default_factory=list)
    recurring_issues: list[dict[str, Any]] = Field(default_factory=list)
    recommended_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    validated_improvements: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    package_path: str = ""
    markdown_path: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentDomain(str, Enum):
    EQUATION = "equation"
    FORMULA = "formula"
    ALGORITHM = "algorithm"
    SYMBOLIC_LOGIC = "symbolic_logic"
    OCR = "ocr"
    OBJECT_DETECTION = "object_detection"
    LANGUAGE = "language"
    CODE = "code"
    INFERENCE_BENCHMARK = "inference_benchmark"
    CLOUD_REASONING = "cloud_reasoning"
    CODE_AUDIT = "code_audit"


class EvaluationRoute(str, Enum):
    UI = "ui"
    BACKGROUND = "background"
    API = "api"
    LOCAL = "local"
    CODE_AGENT = "code_agent"
    MATH_EVALUATION = "math_evaluation"
    OCR_VISION = "ocr_vision"
    LANGUAGE_UNDERSTANDING = "language_understanding"
    CLOUD = "cloud"
    FALLBACK = "fallback"
    CODE_AUDIT = "code_audit"


class ExperimentMetric(BaseModel):
    precision: float = 0.0
    execution_ms: int = 0
    operational_cost: float = 0.0
    robustness: float = 0.0
    reuse_score: float = 0.0
    user_progress: float = 0.0
    total_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    route: EvaluationRoute
    assistant_kind: str = ""
    assistant_configuration: AssistantConfigurationSnapshot = Field(default_factory=AssistantConfigurationSnapshot)
    config_signature: str = ""
    output_text: str = ""
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    execution_ms: int = 0
    operational_cost: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    domain: ExperimentDomain
    suite_name: str
    objective: str
    subject_key: str = "general"
    comparison_scope_key: str = ""
    route: EvaluationRoute
    assistant_kind: str = ""
    assistant_configuration: AssistantConfigurationSnapshot = Field(default_factory=AssistantConfigurationSnapshot)
    config_signature: str = ""
    candidate_id: str = ""
    candidate_label: str = ""
    success: bool = False
    expected_summary: str = ""
    observed_summary: str = ""
    metrics: ExperimentMetric = Field(default_factory=ExperimentMetric)
    evidence_refs: list[str] = Field(default_factory=list)
    reused_later: bool = False
    better_than_previous: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at_utc: datetime = Field(default_factory=utc_now)


class ExperimentRecommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    domain: ExperimentDomain
    subject_key: str = "general"
    recommended_route: EvaluationRoute = EvaluationRoute.FALLBACK
    recommended_assistant_kind: str = ""
    recommended_assistant_configuration: AssistantConfigurationSnapshot = Field(default_factory=AssistantConfigurationSnapshot)
    recommended_config_signature: str = ""
    score: float = 0.0
    confidence: float = 0.0
    rationale: str = ""
    supporting_run_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at_utc: datetime = Field(default_factory=utc_now)


class ToolPerformanceSnapshot(BaseModel):
    performance_id: str = Field(default_factory=lambda: str(uuid4()))
    domain: ExperimentDomain = ExperimentDomain.LANGUAGE
    subject_key: str = "general"
    route: EvaluationRoute = EvaluationRoute.FALLBACK
    assistant_kind: str = ""
    config_signature: str = ""
    sample_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    blocked_count: int = 0
    fallback_count: int = 0
    success_rate: float = 0.0
    blocked_rate: float = 0.0
    fallback_rate: float = 0.0
    average_score: float = 0.0
    average_latency_ms: int = 0
    adaptive_weight: float = 0.0
    weighted_score: float = 0.0
    trend_score: float = 0.0
    degraded: bool = False
    degradation_reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    comparison_scope_keys: list[str] = Field(default_factory=list)
    created_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalWorkerTelemetry(BaseModel):
    """Minimal contract for tracking external worker execution.

    Deposited by whoever dispatches work to an external tool/agent
    (orchestrator, tool adapter, or manual checkpoint) into
    ``session.metadata['worker_telemetry']``.  From there it flows
    automatically into ``ExperimentRun.metadata`` via
    ``TaskOutcomeRecorder``, into ``PortableContext`` summaries, and
    into OSES pattern detection.
    """

    worker_kind: str = ""
    assistant_kind: str = ""
    worker_id: str = ""
    task_packet_id: str = ""
    budget_state: str = "ok"
    continuation_state: str = "complete"
    handoff_required: bool = False
    resume_hint: str = ""
    human_intervention_required: bool = False
    result_status: str = "unknown"
    latency_ms: int = 0
    correction_rounds: int = 0
    merge_success: bool | None = None
    files_touched_scope: list[str] = Field(default_factory=list)

    # Scientific proxy variables (calculated by scientific_proxy_engine)
    compression_ratio: float | None = None
    description_length_proxy: int | None = None
    entropy_proxy: float | None = None
    inference_depth_proxy: int | None = None
    step_count_proxy: int | None = None
    multi_step_success_rate: float | None = None
    reuse_score: float | None = None
    stability_score: float | None = None

    # Metacognitive variables (populated by TaskOutcomeRecorder)
    predicted_outcome: str | None = None
    actual_outcome: str | None = None
    confidence: float | None = None
    calibration_error: float | None = None
    uncertainty_proxy: float | None = None

    # Decision
    recommended_action: str | None = None


class ToolEvolutionProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_key: str = ""
    domain: ExperimentDomain = ExperimentDomain.LANGUAGE
    subject_key: str = "general"
    status: str = "pending"
    proposal_kind: str = ""
    title: str = ""
    summary: str = ""
    rationale: str = ""
    current_route: EvaluationRoute = EvaluationRoute.FALLBACK
    current_assistant_kind: str = ""
    current_config_signature: str = ""
    candidate_route: EvaluationRoute = EvaluationRoute.FALLBACK
    candidate_assistant_kind: str = ""
    candidate_config_signature: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    comparison_scope_keys: list[str] = Field(default_factory=list)
    created_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolEvolutionStatus(BaseModel):
    status_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    summary: str = ""
    performance: list[ToolPerformanceSnapshot] = Field(default_factory=list)
    proposals: list[ToolEvolutionProposal] = Field(default_factory=list)
    degraded_subjects: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    package_path: str = ""
    markdown_path: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProposalValidationResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: str = ""
    proposal_key: str = ""
    domain: ExperimentDomain = ExperimentDomain.LANGUAGE
    subject_key: str = "general"
    proposal_kind: str = ""
    decision: str = "unresolved"
    winner: str = "unresolved"
    reason: str = ""
    current_route: EvaluationRoute = EvaluationRoute.FALLBACK
    current_assistant_kind: str = ""
    current_config_signature: str = ""
    candidate_route: EvaluationRoute = EvaluationRoute.FALLBACK
    candidate_assistant_kind: str = ""
    candidate_config_signature: str = ""
    sandbox_experiment_id: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    comparison_scope_keys: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    recorded_at_utc: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolEvolutionDecisionLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    updated_at_utc: datetime = Field(default_factory=utc_now)
    entries: list[ProposalValidationResult] = Field(default_factory=list)
    summary_by_tool: dict[str, str] = Field(default_factory=dict)
    summary_by_problem: dict[str, str] = Field(default_factory=dict)
    package_path: str = ""
    markdown_path: str = ""
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolDiscoverySignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_key: str = ""
    source: str = ""
    source_refs: list[str] = Field(default_factory=list)
    domain: ExperimentDomain = ExperimentDomain.LANGUAGE
    scope: str = "general"
    title: str = ""
    summary: str = ""
    tool_id: str = ""
    tool_title: str = ""
    assistant_kind: str = ""
    route: EvaluationRoute = EvaluationRoute.FALLBACK
    config_signature: str = ""
    status: str = "detected"
    confidence: float = 0.0
    compatibility_score: float = 0.0
    impact_score: float = 0.0
    cost_score: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolDiscoveryStatus(BaseModel):
    status_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    summary: str = ""
    signals: list[ToolDiscoverySignal] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    package_path: str = ""
    markdown_path: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SandboxExperimentVerdict(str, Enum):
    VALID = "valid"
    DOUBTFUL = "doubtful"
    FAILED = "failed"
    UNRESOLVED = "unresolved"


class SandboxExperiment(BaseModel):
    experiment_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    domain: ExperimentDomain = ExperimentDomain.LANGUAGE
    subject_key: str = "general"
    sandbox_subject_key: str = "sandbox:general"
    hypothesis: str = ""
    baseline_route: EvaluationRoute = EvaluationRoute.FALLBACK
    baseline_assistant_kind: str = ""
    baseline_config_signature: str = ""
    candidate_route: EvaluationRoute = EvaluationRoute.FALLBACK
    candidate_assistant_kind: str = ""
    candidate_config_signature: str = ""
    status: str = "observed"
    verdict: SandboxExperimentVerdict = SandboxExperimentVerdict.UNRESOLVED
    isolated: bool = True
    promote_to_primary: bool = False
    evidence_strength: float = 0.0
    supporting_run_ids: list[str] = Field(default_factory=list)
    observed_blockers: list[str] = Field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutonomousValidationSnapshot(BaseModel):
    cycle_id: str = Field(default_factory=lambda: str(uuid4()))
    last_checked_at_utc: datetime = Field(default_factory=utc_now)
    status: str = "idle"
    summary: str = ""
    paused_reason: str = ""
    pending_candidates: int = 0
    promoted_count: int = 0
    last_experiment_id: str = ""
    current_experiment: SandboxExperiment | None = None
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyParameter(BaseModel):
    parameter_id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    label: str
    description: str = ""
    value: Any | None = None
    default_value: Any | None = None
    kind: str = "text"
    editable: bool = True
    required: bool = False
    options: list[str] = Field(default_factory=list)


class StrategyAlgorithm(BaseModel):
    algorithm_id: str
    title: str
    summary: str
    parameter_keys: list[str] = Field(default_factory=list)
    success_signals: list[str] = Field(default_factory=list)
    fallback_signals: list[str] = Field(default_factory=list)
    notes: str = ""


class StrategyPack(BaseModel):
    pack_id: str
    title: str
    domain_kind: str
    supported_intents: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    available_algorithms: list[StrategyAlgorithm] = Field(default_factory=list)
    parameter_schema: list[StrategyParameter] = Field(default_factory=list)
    risk_level: IssueSeverity = IssueSeverity.LOW
    approval_policy: str = "phased"
    execution_templates: list[str] = Field(default_factory=list)
    success_signals: list[str] = Field(default_factory=list)
    fallback_signals: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    pack_id: str
    title: str
    rationale: str
    algorithm_id: str
    parameters: list[StrategyParameter] = Field(default_factory=list)
    readiness_status: CapabilityStatus = CapabilityStatus.INSUFFICIENT
    risk_level: IssueSeverity = IssueSeverity.LOW
    requires_approval: bool = False
    missing_requirements: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlaybookStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    phase_key: str
    title: str
    description: str
    status: RunStatus = RunStatus.SUCCESS
    requires_approval: bool = False
    capability_id: str | None = None
    pack_id: str | None = None
    executable: bool = False
    simulation_only: bool = False
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlaybook(BaseModel):
    playbook_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    pack_id: str
    summary: str = ""
    status: AdaptiveSessionStatus = AdaptiveSessionStatus.PLANNED
    steps: list[PlaybookStep] = Field(default_factory=list)
    next_phase: str = ""
    requires_approval: bool = False
    simulation_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str | None = None
    playbook_id: str | None = None
    title: str
    detail: str
    decision: ApprovalDecision = ApprovalDecision.PENDING
    phase_key: str = ""
    reason: str = ""
    risk_level: IssueSeverity = IssueSeverity.MEDIUM
    created_at_utc: datetime = Field(default_factory=utc_now)
    decided_at_utc: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskOutcome(BaseModel):
    outcome_id: str = Field(default_factory=lambda: str(uuid4()))
    status: RunStatus = RunStatus.SUCCESS
    summary: str = ""
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdaptiveSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    run_id: str | None = None
    user_goal: str
    intent: TaskIntent
    hypotheses: list[IntentHypothesis] = Field(default_factory=list)
    context: TaskContext = Field(default_factory=TaskContext)
    chosen_pack_id: str = ""
    chosen_pack_title: str = ""
    status: AdaptiveSessionStatus = AdaptiveSessionStatus.PLANNED
    capability_readiness: list[CapabilityReadiness] = Field(default_factory=list)
    strategy_candidates: list[StrategyCandidate] = Field(default_factory=list)
    playbook: ExecutionPlaybook | None = None
    approval_checkpoints: list[ApprovalCheckpoint] = Field(default_factory=list)
    outcome: TaskOutcome | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    scenario_id: str = ""
    scenario_mode: ScenarioMode | None = None
    probe_diagnosis: ProbeDiagnosis | None = None
    runtime_adjustments: list[RuntimeAdjustment] = Field(default_factory=list)
    pending_issue_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InferenceRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    user_goal: str
    prompt: str = ""
    screenshots: list[str] = Field(default_factory=list)
    steps: list[CapturedStep] = Field(default_factory=list)
    offline_only: bool = False
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    ambiguity: AmbiguityLevel = AmbiguityLevel.LOW
    requires_vision: bool = True
    deep_reasoning: bool = False
    task_role: TaskRole = TaskRole.TRAINING
    allowed_tools: list[ToolCapability] = Field(default_factory=list)
    knowledge_scope: list[str] = Field(default_factory=list)
    read_only_sql: bool = False
    requires_visual_reasoning: bool = False
    auto_route: bool = False
    role_hint: TaskRole | None = None
    enable_planning: bool = False
    conversation_context: list[dict[str, Any]] = Field(default_factory=list)
    site_hint: str | None = None
    approval_mode: str = "phased"
    execution_scope: str = "operational"
    goal_parameters: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InferenceResult(BaseModel):
    request_id: str
    provider_name: str
    reasoning_mode: ReasoningMode
    summary: str
    inferred_task: str
    confidence: float
    confidence_reduced: bool = False
    used_fallback: bool = False
    clarifications: list[ClarificationItem] = Field(default_factory=list)
    used_tools: list[ToolCapability] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    follow_up_teachings: list[str] = Field(default_factory=list)
    report_kind: ReportKind = ReportKind.CHAT
    detected_role: TaskRole | None = None
    planner_used: bool = False
    executor_model: str = ""
    diagnostic_flags: list[str] = Field(default_factory=list)
    improvement_hints: list[str] = Field(default_factory=list)
    incident_refs: list[str] = Field(default_factory=list)
    hidden_incident_refs: list[str] = Field(default_factory=list)
    health_flags: list[str] = Field(default_factory=list)
    recommended_next_checks: list[str] = Field(default_factory=list)
    scenario: dict[str, Any] | None = None
    probe_diagnosis: dict[str, Any] | None = None
    runtime_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    pending_issue_ref: str = ""
    intent: dict[str, Any] | None = None
    chosen_pack: dict[str, Any] | None = None
    strategy_candidates: list[dict[str, Any]] = Field(default_factory=list)
    playbook: dict[str, Any] | None = None
    approval_checkpoints: list[dict[str, Any]] = Field(default_factory=list)
    capability_readiness: list[dict[str, Any]] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    error_summary: str = ""
    raw_output: dict[str, Any] = Field(default_factory=dict)


class StepExecutionResult(BaseModel):
    step_id: str
    status: RunStatus
    detail: str = ""


class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    task_label: str
    episode_id: str | None = None
    steps: list[CapturedStep] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    expected_outcome: str = ""


class ExecutionResult(BaseModel):
    plan_id: str
    status: RunStatus
    detail: str = ""
    step_results: list[StepExecutionResult] = Field(default_factory=list)


class RunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    request: InferenceRequest
    result: InferenceResult
    route: RoleRoute | RouteDecision
    status: RunStatus = RunStatus.SUCCESS
    duration_ms: int | None = None
    error_summary: str = ""


class ExecutionDossier(BaseModel):
    dossier_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    scope: DossierScope = DossierScope.CHAT
    title: str
    summary: str
    run_id: str | None = None
    episode_id: str | None = None
    status: RunStatus = RunStatus.SUCCESS
    severity: IssueSeverity = IssueSeverity.LOW
    issue_hint_text: str = ""
    detected_role: TaskRole | None = None
    model_used: str = ""
    planner_used: bool = False
    tools_used: list[ToolCapability] = Field(default_factory=list)
    duration_ms: int | None = None
    error_summary: str = ""
    stack_health: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    issue_candidates: list[IssueCandidate] = Field(default_factory=list)
    improvement_proposals: list[ImprovementProposal] = Field(default_factory=list)
    self_checks: list[SelfCheckResult] = Field(default_factory=list)
    hidden_incidents: list[HiddenIncident] = Field(default_factory=list)
    session_health: SessionHealthSnapshot | None = None
    user_clues: list[UserClue] = Field(default_factory=list)
    incident_summary: str = ""
    scenario_run_id: str | None = None
    probe_diagnosis: ProbeDiagnosis | None = None
    runtime_adjustments: list[RuntimeAdjustment] = Field(default_factory=list)
    pending_issue_id: str | None = None
    next_action: str = ""
    codex_brief: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingPayloadV2(BaseModel):
    version: int = 2
    generated_at_utc: datetime = Field(default_factory=utc_now)
    workspace: str
    episodes: list[EpisodeManifest] = Field(default_factory=list)
    steps: list[CapturedStep] = Field(default_factory=list)
    artifacts: list[SessionArtifact] = Field(default_factory=list)
    knowledge_items: list[KnowledgeItem] = Field(default_factory=list)
    run_records: list[RunRecord] = Field(default_factory=list)
    capture_channels: list[CaptureChannel] = Field(default_factory=list)
    site_context: dict[str, Any] = Field(default_factory=dict)
    redaction_summary: RedactionSummary = Field(default_factory=RedactionSummary)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlRuleSeverity(str, Enum):
    INFO = "info"
    ADVISORY = "advisory"
    STRICT = "strict"
    IRREVOCABLE = "irrevocable"


class ControlRuleStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class ControlRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    severity: ControlRuleSeverity = ControlRuleSeverity.ADVISORY
    rationale: str = ""
    applies_to: list[str] = Field(default_factory=list)
    status: ControlRuleStatus = ControlRuleStatus.ACTIVE
    source_refs: list[str] = Field(default_factory=list)
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)


class ControlDecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IMPLEMENTED = "implemented"
    REVERTED = "reverted"


class ControlDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    summary: str
    reason: str = ""
    impact: str = ""
    affected_modules: list[str] = Field(default_factory=list)
    status: ControlDecisionStatus = ControlDecisionStatus.PROPOSED
    evidence: list[str] = Field(default_factory=list)
    linked_tests: list[str] = Field(default_factory=list)
    related_rule_ids: list[str] = Field(default_factory=list)
    related_objective_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)
    unresolved_notes: list[str] = Field(default_factory=list)


class ControlMasterState(BaseModel):
    state_id: str = Field(default_factory=lambda: str(uuid4()))
    version: str = "control_master.v1"
    current_vision: str = ""
    active_objective_ids: list[str] = Field(default_factory=list)
    completed_objective_ids: list[str] = Field(default_factory=list)
    paused_objective_ids: list[str] = Field(default_factory=list)
    discarded_objective_ids: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    global_rules: list[ControlRule] = Field(default_factory=list)
    technical_backlog: list[dict[str, Any]] = Field(default_factory=list)
    recent_decisions: list[ControlDecision] = Field(default_factory=list)
    current_risks: list[dict[str, Any]] = Field(default_factory=list)
    current_tests_state: dict[str, Any] = Field(default_factory=dict)
    evidence_links: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlMasterDigest(BaseModel):
    """Compact governance pack (<2 KB text) injected into IAs.

    Complementary to PortableContextPackage: narrower scope (vision +
    rules + objectives + risks + decisions), always truncated to fit
    safely inside a system prompt, and intentionally stateless about
    chat history.
    """

    digest_id: str = Field(default_factory=lambda: str(uuid4()))
    version: str = "control_master_digest.v1"
    current_vision: str = ""
    active_objectives_brief: list[str] = Field(default_factory=list)
    rules_brief: list[str] = Field(default_factory=list)
    top_backlog: list[str] = Field(default_factory=list)
    current_risks: list[str] = Field(default_factory=list)
    recent_decisions_brief: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    tests_state_brief: str = ""
    autonomy_metrics_brief: str = ""
    coordination_patterns_brief: str = ""
    work_queue_brief: list[str] = Field(default_factory=list)
    work_queue_counts: dict[str, int] = Field(default_factory=dict)
    generated_at_utc: datetime = Field(default_factory=utc_now)
    source_state_id: str = ""




# ---------------------------------------------------------------------------
# SelfAudit — resultados agregados de la revisión read-only del sistema vivo
# ---------------------------------------------------------------------------
#
# Estos tres contratos son puros (read-only, frozen). Los consume
# `SelfAuditService` para responder "auditate a vos mismo" desde UI/MCP sin
# cambiar estado del sistema vivo y sin duplicar PerceptionSnapshot.


@dataclass(frozen=True)
class ToolCheckResult:
    """Resultado de un dry-check de una tool del ToolRegistry.

    - `status` usa el vocabulario: `ready` | `degraded` | `missing` | `blocked`.
    - `evidence` es un diccionario abierto con pistas reproducibles
      (adapter_key, validation_status, tool_type, última observación, etc.).
    """

    tool_id: str
    available: bool
    status: str
    reason: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnvironmentMatchResult:
    """Contraste entre `EnvironmentSelfModel` y el `WorldModelSnapshot` vivo.

    - `matched=True` significa que los dos modelos son coherentes
      (mismas tools disponibles, sin risk signals que contradigan el
      world_model, etc.).
    - `mismatches` son descripciones concretas y humanas, no códigos.
    - Los digests permiten trazabilidad sin exponer los modelos completos.
    """

    matched: bool
    mismatches: list[str] = field(default_factory=list)
    environment_digest: str = ""
    world_model_digest: str = ""


@dataclass(frozen=True)
class SelfAuditSnapshot:
    """Snapshot agregado de la autoauditoría operativa.

    Emitido por `SelfAuditService.run(...)` y persistido en
    `data/evolution/self_audit/{latest.json, latest.md, history/<ISO>.json}`.
    Es la fuente única consumida por el botón "Auditarme ahora" del
    Control Center y por la tool MCP `run_self_audit`.
    """

    generated_at: datetime
    reason: str | None
    tool_checks: list[ToolCheckResult]
    environment_match: EnvironmentMatchResult
    pending_issues: list[str]
    world_model_digest: dict[str, Any]
    summary_markdown: str
    cross_source_truth: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PCS v1 — Embodiment Violation Records
# ---------------------------------------------------------------------------
#
# Contratos para `EmbodimentViolationDetector` (PR E de PCS v1). Una
# "violación" ocurre cuando la pregunta del usuario matchea un sensor
# propio de IABV (según el mapeo declarado por `embodiment_manifest`)
# pero el asistente externo no llamó a la tool del cuerpo correspondiente
# y usó rutas externas. En v1 el detector NO bloquea
# (`handshake_required=False` en el manifest); sólo reporta para
# alimentar `metadata['embodiment_violations']` del snapshot de
# autoexaminación y para consulta read-only vía MCP.


class EmbodimentViolationKind(str, Enum):
    SENSOR_BYPASS = 'sensor_bypass'
    TOOL_MISUSE = 'tool_misuse'
    MISSED_OBSERVATION = 'missed_observation'


class EmbodimentViolationRecord(BaseModel):
    violation_id: str = Field(default_factory=lambda: str(uuid4()))
    detected_at_utc: datetime = Field(default_factory=utc_now)
    session_id: str = ''
    assistant_kind: str = ''
    trace_id: str = ''
    question_text: str = ''
    matched_sensor: str = ''
    expected_tool_id: str = ''
    tool_ids_used: list[str] = Field(default_factory=list)
    violation_kind: EmbodimentViolationKind = EmbodimentViolationKind.SENSOR_BYPASS
    severity: IssueSeverity = IssueSeverity.LOW
    reasoning: str = ''
    evidence_refs: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# PCS v1 — Protocolo Cognitivo Sináptico Inter-IA
#
# Contratos declarativos que describen a cada IA externa (ChatGPT, Claude,
# Codex, Devin, Ollama local, etc.) como una "neurona especializada" con
# fortalezas, tools nativas y frame cognitivo óptimo. IABV usa estos
# perfiles para decidir a quién consultar y en qué formato presentarle el
# contexto, sin duplicar el cerebro ni el orquestador.


class AssistantStrength(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    LONG_CONTEXT_SYNTHESIS = "long_context_synthesis"
    SHELL_EXECUTION = "shell_execution"
    WEB_BROWSING = "web_browsing"
    MULTIMODAL_VISION = "multimodal_vision"
    STRUCTURED_REASONING = "structured_reasoning"
    CREATIVE_WRITING = "creative_writing"
    MATHEMATICAL_REASONING = "mathematical_reasoning"
    RETRIEVAL_AUGMENTED = "retrieval_augmented"


class AssistantFrameKind(str, Enum):
    """Frame cognitivo óptimo para presentar contexto a esta IA."""

    DIFF_AND_TESTS = "diff_and_tests"        # Codex / GPT-4o para código
    LONG_NARRATIVE = "long_narrative"        # Claude (contexto largo)
    TASK_LIST_AND_PR = "task_list_and_pr"    # Devin
    STRUCTURED_QA = "structured_qa"          # ChatGPT general
    JSON_TOOL_CALLS = "json_tool_calls"      # agentes con function calling


class AssistantCapabilityProfile(BaseModel):
    """Perfil declarativo de una IA externa consumible por PCS v1.

    Se usa para que `SynapticRouter` decida a quién consultar y para que
    `CognitiveFrameTranslator` elija el frame óptimo del contexto. Es
    puramente descriptivo: no dispara ninguna acción por sí mismo.
    """

    assistant_kind: str
    display_name: str = ""
    strengths: list[AssistantStrength] = Field(default_factory=list)
    native_tools: list[str] = Field(default_factory=list)
    optimal_frame: AssistantFrameKind = AssistantFrameKind.STRUCTURED_QA
    max_context_tokens: int = 0
    avg_latency_ms: int = 0
    cost_signal: str = "unknown"
    supports_function_calling: bool = False
    supports_vision: bool = False
    supports_browser: bool = False
    supports_shell: bool = False
    known_limitations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CognitiveFramePayload(BaseModel):
    """Renderización determinística de un `PerceptionSnapshot` para una IA.

    Producto del `CognitiveFrameTranslator`: dado un perception + un
    ``AssistantFrameKind``, devuelve un payload estructurado + texto plano
    listo para inyectar como system/context prompt. No hace inferencia:
    todo es format determinístico.
    """

    frame: AssistantFrameKind
    target_assistant_kind: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    plain_text_rendering: str = ""
    token_estimate: int = 0
    evidence_refs: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SynapticRoutingDecision(BaseModel):
    """Decisión del `SynapticRouter` (PCS v1 — Pieza 4).

    Producto puramente descriptivo de la decisión de routing inter-IA. No
    ejecuta la ruta, no modifica estado vivo; el orquestador actual sigue
    siendo `LocalRoleRouter`. Este adaptador sólo devuelve la preferencia
    calculada para que otra capa la consuma (tool MCP, UI, etc.).

    ``alternatives`` se serializa como ``list[dict[str, Any]]`` con claves
    ``{'assistant_kind': str, 'score': float}`` para mantener
    compatibilidad con JSON plano.
    """

    selected_assistant_kind: str = ""
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    fit_score: float = 0.0
    weight_score: float = 0.0
    availability_score: float = 0.0
    total_score: float = 0.0
    routing_enabled: bool = False
    reason: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConsensusResult(BaseModel):
    """Resultado de la fusión de consenso (PCS v1 — Pieza 5).

    Producto del `ConsensusFusionService`: dada una lista de
    ``IATraceEntry`` del mismo ``comparison_scope_key``, devuelve un
    ganador según la estrategia pedida (``weighted_vote``,
    ``highest_confidence`` o ``first_success``). No muta los traces de
    entrada; la decisión es puramente descriptiva.
    """

    comparison_scope_key: str = ""
    winning_trace_id: str = ""
    winning_assistant_kind: str = ""
    winning_label: str = ""
    strategy_used: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    considered_trace_ids: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingTaskStatus(str, Enum):
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    UNRESOLVED = "UNRESOLVED"
    READY_FOR_NEXT_SLICE = "READY_FOR_NEXT_SLICE"
    COMPLETED = "COMPLETED"


class PlatformPendingTask(BaseModel):
    """Tarea pendiente de integración con la plataforma nativa.

    Registra capacidades faltantes, tareas bloqueadas por limitación del
    entorno, o dependencias que aún no pueden resolverse.  La cola se
    persiste en ``data/evolution/platform_pending/`` y es legible por
    PortableContext, OSES y cualquier agente que retome la sesión.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    reason: str = ""
    dependency_missing: str = ""
    priority: str = "medium"
    next_action: str = ""
    status: PendingTaskStatus = PendingTaskStatus.PENDING
    category: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    resume_hint: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformResumeHint(BaseModel):
    """Checkpoint para reanudación de tareas incompletas.

    Cuando una tarea se interrumpe (corte, cuota, sesión, falta de
    permiso), se guarda un checkpoint con el estado útil más reciente.
    El siguiente agente o sesión puede leer el hint y continuar desde
    ese punto sin empezar de cero.
    """

    task_id: str = ""
    checkpoint_phase: str = ""
    last_successful_step: str = ""
    remaining_steps: list[str] = Field(default_factory=list)
    handoff_required: bool = False
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# Test Evidence — P0.29
# ──────────────────────────────────────────────────────────────


class TestEvidence(BaseModel):
    """Compact, canonical record of a pytest run.

    Persisted by ``audit_tools.run_pytest()`` when ``persist_evidence=True``
    to ``data/evolution/test_evidence/latest.json``.  Read by
    ``SelfAuditService`` (to flip ``tests_observed``), ``ControlMasterState``
    (``current_tests_state``), and ``PortableContextService`` (compact
    summary without logs or PII).

    No logs, no PII, no large output — only counts and metadata.
    """

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    command: str = ""
    suite: str = ""
    keyword: str = ""
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_s: float = 0.0
    returncode: int = 0
    timed_out: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
    linked_pending_task: str = ""
    changed_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# Account Inventory & Continuity Layer
# ──────────────────────────────────────────────────────────────


class AccountStatus(str, Enum):
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    EXPIRED = "expired"
    UNRESOLVED = "unresolved"


class AccountType(str, Enum):
    OWNER = "owner"
    TRIAL = "trial"
    UNKNOWN = "unknown"


class AccountInventoryEntry(BaseModel):
    """Single account+tool pair with session, quota and continuity data.

    This is the formal contract that replaces loose dicts produced by
    ``account_resource_scanner``.  Every field is explicit so that
    Control Master, PortableContext and the UI can consume it without
    guessing dict keys.
    """

    email: str
    browser: str = ""
    profile: str = ""
    tool: str = ""
    has_session: bool = False
    session_verified_at: datetime | None = None
    quota_remaining: int = 0
    quota_limit: int = 0
    quota_resets_at: datetime | None = None
    exhausted: bool = False
    account_type: AccountType = AccountType.UNKNOWN
    block_signals: list[str] = Field(default_factory=list)
    score: float = 0.0
    status: AccountStatus = AccountStatus.UNRESOLVED
    unresolved: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AccountInventorySnapshot(BaseModel):
    """Point-in-time snapshot of every known account across all browsers.

    Built by ``build_inventory_snapshot()`` in ``account_resource_scanner``.
    Consumed by Control Master (governance), PortableContext (continuity)
    and CentroVivo (UI).

    ``continuity_queue`` is the ranked list of non-exhausted entries
    sorted by score descending — the first entry is the recommended
    next account.  The user must approve before any account is used."""


# ---------------------------------------------------------------------------
# Cross-Agent Synchronization — Handoff Knowledge
# ---------------------------------------------------------------------------
#
# Contratos para el handoff entre IAs (Devin → Claude → Codex, etc.)
# Permiten reconstruir de forma verificable quién hizo qué, cómo fue auditado,
# y qué IA debe continuar el trabajo.


class EvidenceStatus(str, Enum):
    """Estado de evidencia en el conocimiento handoff.

    DECLARED: IA ejecutora declara un estado (no verificado)
    VERIFIED: IA auditora verificó que la declaración es correcta
    REPRODUCED: IA auditora reprodujo el resultado y coincidió
    INFERRED: Derivado de evidencia indirecta
    UNKNOWN: Estado desconocido o no verificable
    """
    DECLARED = "declared"
    VERIFIED = "verified"
    REPRODUCED = "reproduced"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class AuthorizationStatus(str, Enum):
    """Estado de autorización para next_agent/next_action.

    DECLARED: IA anterior declaró una preferencia (no autorizada)
    RECOMMENDED: Sistema recomienda basado en evidencia histórica
    AUTHORIZED: Sistema autoriza explícitamente la transición
    PENDING: Pendiente de autorización
    REVOKED: Autorización revocada
    """
    DECLARED = "declared"
    RECOMMENDED = "recommended"
    AUTHORIZED = "authorized"
    PENDING = "pending"
    REVOKED = "revoked"


class AgentHandoffRecord(BaseModel):
    """Registro completo de handoff entre IAs.

    Persistido en ``data/evolution/agent_handoff/handoffs.jsonl`` por
    ``AgentHandoffTrail``. Es la fuente única para reconstruir el estado
    de una tarea entre diferentes IAs y sesiones.

    Este registro NO es una autoridad de ejecución — es puramente
    observacional y verificativa. No dispara acciones por sí mismo.
    """
    handoff_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    task_name: str
    executor_agent: str
    auditor_agent: str
    session_id: str
    timestamp_utc: datetime = Field(default_factory=utc_now)

    # Git synchronization state
    repository: str
    baseline_sha: str
    local_branch: str
    public_branch: str
    head_sha: str
    task_commits: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    sync_verified: bool = False

    # Evidence states
    tests_executed: list[str] = Field(default_factory=list)
    tests_status: EvidenceStatus = EvidenceStatus.DECLARED
    inherited_failures: list[str] = Field(default_factory=list)
    new_failures: list[str] = Field(default_factory=list)

    # Authority
    authority: str = ""
    audit_verdict: str = ""
    audit_evidence: dict[str, Any] = Field(default_factory=dict)

    # Next steps
    next_agent: str = ""
    next_agent_authorization: AuthorizationStatus = AuthorizationStatus.DECLARED
    next_action: str = ""
    next_action_authorization: AuthorizationStatus = AuthorizationStatus.DECLARED

    # Learning signals
    learning_signals: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AccountInventorySnapshot(BaseModel):
    """Point-in-time snapshot of every known account across all browsers.

    Built by ``build_inventory_snapshot()`` in ``account_resource_scanner``.
    Consumed by Control Master (governance), PortableContext (continuity)
    and CentroVivo (UI).

    ``continuity_queue`` is the ranked list of non-exhausted entries
    sorted by score descending — the first entry is the recommended
    next account.  The user must approve before any account is used."""
    entries: list[AccountInventoryEntry] = Field(default_factory=list)
    continuity_queue: list[AccountInventoryEntry] = Field(default_factory=list)
    scanned_at: datetime = Field(default_factory=utc_now)
    active_count: int = 0
    exhausted_count: int = 0
    expired_count: int = 0
    unresolved_count: int = 0
    total_remaining_messages: int = 0
    tools_available: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetacognitiveDiscernmentFrame(BaseModel):
    """P0.69: evidence-based discernment frame for pre-action reasoning.

    This is NOT another cerebro — it is a shared evidence contract that
    existing services (OSES, PortableContext, TaskContextAssembler,
    UniversalPerceptionService, ControlCenterViewModel) read and write
    to build a causal picture before acting.

    Lifecycle phases: birth → observe → interpret → decide → act → learn → recover.
    """

    frame_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at_utc: datetime = Field(default_factory=utc_now)
    phase: str = 'birth'
    trigger_source: str = ''
    raw_inputs: list[str] = Field(default_factory=list)
    sensor_sources: list[str] = Field(default_factory=list)
    trusted_sources: list[str] = Field(default_factory=list)
    untrusted_sources: list[str] = Field(default_factory=list)
    missing_sources: list[str] = Field(default_factory=list)
    detected_concepts: list[str] = Field(default_factory=list)
    concept_weights: dict[str, float] = Field(default_factory=dict)
    active_attractors: list[dict[str, Any]] = Field(default_factory=list)
    failed_attractors: list[dict[str, Any]] = Field(default_factory=list)
    candidate_attractor: str = ''
    attractor_confidence: float = 0.0
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    bias_risks: list[dict[str, Any]] = Field(default_factory=list)
    grounding_status: str = 'unknown'
    confidence: float = 0.0
    action_candidates: list[dict[str, Any]] = Field(default_factory=list)
    selected_action: str = ''
    why_not_other_actions: list[str] = Field(default_factory=list)
    human_help_needed: bool = False
    unresolved_fields: list[str] = Field(default_factory=list)
    next_observation: str = ''
    learning_hook: str = ''
    metadata: dict[str, Any] = Field(default_factory=dict)


class AccountApproval(BaseModel):
    """User-approved account selection for a specific tool.

    Created when the user clicks "Aprobar cambio de cuenta" in the UI.
    Consumed by the worker health gate in ``LocalRoleRouter`` to
    override the automatic ranking for the specified tool.  Other tools
    are NOT affected — the selection is strictly per-tool.
    """

    tool: str
    email: str
    browser: str = ""
    profile: str = ""
    approved_at: datetime = Field(default_factory=utc_now)
    last_validated: datetime | None = None
    origin: str = "ui"
    reason: str = ""
    snapshot_id: str = ""
    valid: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
