# Triska Hazard Log

Initial hazard log per DCB0129 framing. Owner: David Triska (CSO).
Living document — every new hazard, control, or residual risk gets a row.
Severity / likelihood scale is informal at this stage; promote to a formal
DCB0129-aligned matrix before any clinical deployment beyond the author's
own use.

## Status
Pre-development at Phase 0. **No clinical deployment.** No LIVE-mode code
exists yet.

## Hazards

| ID  | Hazard | Cause | Effect | Severity | Likelihood | Initial risk | Controls | Residual risk | Status |
| --- | ------ | ----- | ------ | -------- | ---------- | ------------ | -------- | ------------- | ------ |
| H001 | Unintended commit of clinical action | Workflow replays end-to-end and clicks Submit | Wrong prescription / referral / safety-net sent | Major | Possible | High | (1) SAFE-mode default halts before Submit. (2) Submit-class detection per origin. (3) LIVE-mode requires per-execution arming with 5s timeout and auto-disarm. (4) Selector-miss aborts immediately, no fuzzy retry. | Medium — depends on Submit-class detection accuracy | Open |
| H002 | Wrong patient context | Workflow runs on the wrong open task | Action taken against wrong patient record | Major | Possible | High | (1) Audit log captures patient context from URL. (2) LIVE replay shows full-width "LIVE FIRE" banner with workflow name. (3) Origin-scoped buttons. | Medium | Open |
| H003 | Draft contamination from aborted workflow | INJECT_TEXT writes to autosaving field, then abort | Stale draft persists in chart | Minor | Likely | Medium | (1) Recorder annotates INJECT_TEXT-bearing workflows. (2) Replay snapshots prior field contents and offers one-click rollback on abort. | Low–Medium | Open |
| H004 | Selector drift after host app update | Vendor changes DOM, recorded workflow targets wrong element | Wrong field clicked / wrong text injected | Major | Likely | High | (1) Three-tier selector strategy (CSS, role+name, text). (2) Selector-miss aborts. (3) No best-guess clicking. | Medium — periodic revalidation required | Open |
| H005 | Patient text leakage via export | User exports workspace JSON containing recorded SNOMED queries / free-text injections | PII / patient-identifiable text leaves device | Minor | Possible | Medium | (1) Recorder redacts non-clinical-search field text from step logs. (2) Pre-export warning modal. (3) Local-only storage by default. | Low–Medium | Open |
| H006 | Clinician over-trust → fast errors | LIVE-mode adoption makes errors propagate faster than they can be caught | Bulk error in same workflow before user notices | Major | Possible | High | (1) LIVE-eligible flag off by default. (2) Three-success precondition warning. (3) High-visibility LIVE FIRE replay UI. (4) Audit log with LIVE run counts surfaced in editor. | Medium | Open |
| H007 | Shared-device misuse | Reception PC, locum logged in, inherits LIVE-eligible workflows | Clinician without context fires a LIVE workflow | Major | Possible | High | (1) Workspace-level LIVE kill switch. (2) Kill-switch lock behind admin password for managed deployments. | Low when locked | Open |
| H008 | Hotkey collision with host app | Bound hotkey fires Triska while user expected host-app behaviour | Unintended panel open / unintended action | Minor | Likely | Medium | (1) Default hotkey chosen to avoid common app bindings. (2) User can change or unbind. | Low | Open |
| H009 | Service worker / message channel failure mid-execution | Background SW restarted during replay, state lost | Replay halts in inconsistent state | Minor | Possible | Low–Medium | (1) Arming state held in content script (not background). (2) Replay execution runs in content script. | Low | Open |

## Change history
- v0.0.1 (Phase 0): Initial hazard log seeded.
