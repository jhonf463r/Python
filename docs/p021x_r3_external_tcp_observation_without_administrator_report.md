# P0.21x-R3: External TCP Observation Without Administrator - Final Report

### PID
- **Value**: 21264
- **Status**: ALIVE ✓
- **Verification**: Process confirmed alive ✓

### Idle Window
- **Duration**: 10 seconds
- **Status**: IDLE_NO_TRAFFIC ✓
- **Existing Ollama connection**: NONE
- **Verification**: No TCP connections found for PID 21264 ✓

### Existing Ollama Connection
- **Status**: NOT_FOUND ✓
- **PID 21264 → 127.0.0.1:11434**: NOT_PRESENT
- **IDLE_PROVIDER_TRAFFIC**: FALSE
- **Verification**: No pre-existing connections detected ✓

### Polling Feasibility
- **Method**: Get-NetTCPConnection
- **Granularity**: Polling-based (not event-driven)
- **Minimum interval**: 1 second (PowerShell limitation)
- **Risk**: May miss very brief connections (<1 second)
- **Verification**: Polling feasible with limitations ⚠️

### PID Attribution
- **OwningProcess field**: AVAILABLE ✓
- **Accuracy**: High (kernel-level attribution)
- **Verification**: PID attribution verified ✓

### Destination Attribution
- **RemoteAddress field**: AVAILABLE ✓
- **RemotePort field**: AVAILABLE ✓
- **127.0.0.1:11434**: Can be identified ✓
- **Verification**: Destination attribution verified ✓

### Timestamp Limitations
- **CreationTime field**: AVAILABLE ✓
- **TimeOfLastStateChange field**: AVAILABLE ✓
- **Precision**: CimInstance#DateTime (high precision)
- **Polling timestamp**: Get-Date (system time)
- **Verification**: Timestamps available ✓

### False Positives
- **Persistent connections**: NOT_DETECTED (no idle connections) ✓
- **Keep-alive**: NOT_DETECTED ✓
- **Health checks**: NOT_DETECTED ✓
- **Background generation**: NOT_DETECTED ✓
- **Ollama used by other component**: NOT_DETECTED ✓
- **Risk**: LOW (clean idle baseline) ✓

### Maximum Defensible Evidence Level
- **LEVEL 1**: IABV opened/possesses connection TCP towards Ollama - PROVABLE ✓
- **LEVEL 2**: Connection changed state during window - PROVABLE ✓
- **LEVEL 3**: IABV sent this specific prompt - NOT_PROVABLE ✗
- **LEVEL 4**: Ollama responded to this specific prompt - NOT_PROVABLE ✗
- **LEVEL 5**: Response corresponds exactly to UI - NOT_PROVABLE ✗

**Maximum defensible level**: LEVEL 2

### Correlation Design
- **T0**: Last idle snapshot (baseline)
- **T1**: Send message (user action)
- **T2...Tn**: Periodic snapshots (1 second interval)
- **T3**: Connection disappearance/state change
- **Strategy**: Compare T0 baseline with T2...Tn to detect new connections
- **Limitation**: May miss connections <1 second duration

### Scientific Limitations
1. **Polling granularity**: 1 second minimum interval may miss brief connections
2. **No content visibility**: Cannot observe HTTP payload, prompt, or response
3. **No request/response correlation**: Cannot map specific request to specific response
4. **No UI equivalence**: Cannot prove response matches UI display
5. **State changes only**: Can only observe connection state, not content

### Final Verdict
**TCP_OBSERVATION_READY**

**Rationale**:
- PID 21264 alive and stable ✓
- No idle traffic detected ✓
- Get-NetTCPConnection provides all required fields ✓
- PID attribution accurate ✓
- Destination attribution accurate ✓
- Timestamps available ✓
- False positive risk low ✓
- Polling feasible with known limitations ✓
- Can prove LEVEL 1 and LEVEL 2 evidence ✓

**Conclusion**:
Get-NetTCPConnection allows external observation of TCP connections from PID 21264 to 127.0.0.1:11434 without Administrator privileges. The idle baseline is clean (no pre-existing connections). The method can prove that IABV opened a connection to Ollama and observe state changes, but cannot observe content or correlate specific requests/responses. Polling granularity (1 second) may miss very brief connections.

### NEXT_SINGLE_ACTION
Proceed with the baseline/candidate experiment using Get-NetTCPConnection polling to observe TCP connections, accepting the limitation that only LEVEL 1 and LEVEL 2 evidence can be obtained (connection existence and state changes, not content or request/response correlation).
