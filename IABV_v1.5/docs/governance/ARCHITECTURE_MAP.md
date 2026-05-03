# IABV v1.5 — Mapa Real de Arquitectura

**Actualizado:** 2026-05-03  
**Fuente:** análisis directo del source tree (240 archivos Python, 110348 LOC)

---

## Diagrama por Capas

```
┌─────────────────────────────────────────────────────────────────┐
│  UI / Presentación (Qt/QML)                          20 archivos│
│  ControlCenterVM(7056L) CaptureStudioVM(2797L) DashVM          │
│  EvolutionCenterVM(1014L) KnowledgeBaseVM ProviderSettingsVM   │
│  RunHistoryVM  CentroVivoVM  SplashController                  │
│  NavigationController  ThemeController  MainWindowBridge        │
└──────────────────┬─────────────────────────────────────────────┘
                   │ signals/slots
┌──────────────────▼─────────────────────────────────────────────┐
│  Orquestación / Cerebro                              15 archivos│
│  AdaptiveTaskOrchestrator(3557L) — ÚNICO cerebro               │
│  AutonomyGovernancePolicy(928L) — gobernanza de rutas          │
│  CloudReasoningPlannerService — planes multi-paso cloud        │
│  IntentUnderstandingService(1802L) — clasificación de intent   │
│  LocalRoleRouter(866L) — decisión de ruta y proveedor local    │
│  TaskContextAssembler(1788L) — ensamblaje de contexto          │
│  GoalEngine  StrategyPackRegistry  ExecutionPlaybookService    │
│  ApprovalGateService  AssistantPreferenceResolver              │
│  AdaptiveModelSelector  AdaptivePlannerService                 │
│  ConsensusFusionService  CapabilityReadinessService            │
└──────────────────┬─────────────────────────────────────────────┘
                   │ delega
┌──────────────────▼─────────────────────────────────────────────┐
│  Percepción / Mundo                                  6 archivos │
│  WorldModelService(1447L) → WorldModelSnapshot                 │
│  EnvironmentSelfAwarenessService(1121L) → EnvironmentSelfModel │
│  UniversalPerceptionService → UniversalPerceptionSignal        │
│  PerceptionCrossValidator                                      │
│  RuntimeSignalCollector                                        │
│  PerceptionGroundTruthComparator                               │
└──────────────────┬─────────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────────┐
│  Aprendizaje / Evolución                            39 archivos │
│  ExperimentLab  StrategySelector  AdaptiveWeightLayer          │
│  TaskOutcomeRecorder  DecisionAuditTrail                       │
│  PortableContextService(2643L)  OSES(6485L)                    │
│  MetacognitionEvolutionMixin  PlatformPendingQueue             │
│  ControlMasterService  ControlMasterDigestBuilder              │
│  AutonomousEvolutionService(1809L)                             │
│  ApiKeyDiscoveryService  TokenRotationLedger                   │
│  DecisionSimplifierEngine  HiddenIncidentDetector              │
│  AutonomousValidationCycle(1963L)                              │
│  [AutonomyCycleService — PROPUESTO, NO EXISTE EN SOURCE]       │
└──────────────────┬─────────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────────┐
│  Gobernanza / Control Maestro                        4 archivos │
│  ControlMasterService → ControlMasterState                     │
│  ControlMasterRepository → JSON persistence                    │
│  ControlMasterDigestBuilder → compact digest (<2KB)            │
│  CLI: `python -m iabv_v15 cm export-digest --format markdown`  │
│  ObjectiveRepository  37 reglas sembradas desde AGENTS.md      │
└──────────────────┬─────────────────────────────────────────────┘
                   │ persiste
┌──────────────────▼─────────────────────────────────────────────┐
│  Herramientas / Tools                               14 archivos │
│  ToolTeachService(1892L) ToolRegistry ToolCard                 │
│  ToolAdapters(2655L) UIExecutionRunner(1361L)                  │
│  ToolValidator ToolMemory ToolVersionMonitor                   │
│  ToolApprovalPolicy ToolRollbackManager ToolSandbox            │
│  InteractionLearningService(860L)                              │
│  GithubRemoteService SiteExplorationService                    │
│  InteractionModeSelector                                       │
└──────────────────┬─────────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────────┐
│  Captura / Replay / Browser                         16 archivos │
│  BrowserTeachSessionService(1296L)                             │
│  BrowserActionService BrowserSessionController                 │
│  BrowserLearningAssembler DemoCaptureService                   │
│  ReplayAnnotationService ReplayConfidenceService               │
│  ReplayLearningFeedbackService ReplayVisualAssembler           │
│  SecretVault SensitiveFieldDetector SitePolicyRegistry         │
│  SiteSessionManager TrainingProfileManager                     │
│  UIScreenshotService                                           │
└──────────────────┬─────────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────────┐
│  Infraestructura                                    28 archivos │
│  bootstrap.py(3472L)  InfraStorage  SQLite  JSONL logs         │
│  MCP server(3139L) (127.0.0.1:8000) + Cloudflared tunnel      │
│  AccountResourceScanner(1998L)  QuotaTracker                   │
│  AutoCorrectionEngine(2246L) CommonSenseEngine(2233L)          │
│  21 repositorios de persistencia                               │
│  StartupTimeline  Config  Logging                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Contratos Soberanos (domain/models.py — 2942 líneas)

| Modelo | Línea | Propósito |
|---|---|---|
| WorldModelSnapshot | 619 | Panorama operativo vivo |
| EnvironmentSelfModel | 512 | Estado de hardware y runtime |
| PerceptionSnapshot | 1893 | Entrada unificada pre-decisión |
| PortableContextPackage | 1925 | Contexto comprimido portable |
| ControlMasterState | 2623 | Estado de gobernanza |
| ControlMasterDigest | 2642 | Digest compacto para IAs |
| ControlRule | 2588 | Regla de gobernanza |
| ControlDecision | 2608 | Decisión registrada |
| SelfAuditSnapshot | 2710 | Resultado de autoauditoría |

---

## Archivos Más Grandes (Top 15 por LOC)

| Archivo | LOC | Área |
|---|---|---|
| control_center_viewmodel.py | 7056 | UI |
| operational_self_examination_service.py | 6485 | Evolución |
| adaptive_task_orchestrator.py | 3557 | Orquestación |
| bootstrap.py | 3472 | Infra |
| server.py (MCP) | 3139 | Infra |
| domain/models.py | 2942 | Dominio |
| capture_studio_viewmodel.py | 2797 | UI |
| tool_adapters.py | 2655 | Tools |
| portable_context_service.py | 2643 | Evolución |
| auto_correction_engine.py | 2246 | Infra |
| common_sense_engine.py | 2233 | Infra |
| account_resource_scanner.py | 1998 | Infra |
| autonomous_validation_cycle.py | 1963 | Evolución |
| tool_teach_service.py | 1892 | Tools |
| autonomous_evolution_service.py | 1809 | Evolución |
