# Triska — Plan

A user-configurable Chrome extension delivering a Stream Deck style shortcut
panel and recordable workflows for clinical web applications, with an opt-in
arming mechanism for end-to-end execution.

Working name: **Triska**. Named for the developer; coincidentally means
*thirteen* in Czech, which informs the safety catch motif. This plan is
written for an autonomous coding agent (Claude Code) to scaffold and iterate.

## One line goal

Give a clinician a floating button grid in any browser tab that triggers
single-click navigations, single-click DOM macros, and longer recorded
workflows, with a recording mode that lets the user demonstrate a workflow
once and replay it forever, and an arming mechanism that lets a chosen
workflow execute end-to-end including the final commit step.

## Why this exists

Modern clinical web applications hide common tasks behind multiple clicks
across nested menus. A daily user repeats the same click chains hundreds of
times. Existing browser shortcut tools assume static URLs and a co-operative
DOM; clinical apps have neither. This extension solves three problems:

1. Instant deep links to the tasks a user opens twenty times a day.
2. Instant DOM macros for common in-task operations.
3. User-authored multi-step workflows captured by demonstration rather than
   coding, with the option to run them all the way to completion when the
   user is confident enough to take responsibility for that.

## Primary users

GP partners, salaried GPs, ANPs, pharmacists, and reception staff using
Medicus, Accurx, EMIS Web, SystmOne, ICE, or any other clinical web app.
Initial launch target is Medicus.

## Primary use cases

A user lands on the Medicus homepage and taps a button to jump straight to
their Triage Doctor Medical Requests list. From there they tap a button to
open a specific patient task. Inside the task, they tap a button to switch
the right hand record viewer to Medication History without using the
dropdown. They tap another to focus the Codes and actions field and inject a
slash. They tap another to inject `.urinary tract infection`.

They record a longer workflow once: "open this task, switch to Communication,
load the standard UTI safety-net template, set Status to Awaiting recipient
response, Submit". On a quiet morning they replay it in SAFE mode, watch
what it does, and tap Submit themselves. Once they trust it, they flip the
workflow to LIVE-eligible. Now on every routine UTI presentation they tap
ARM, tap RUN, and the request is gone in two taps.

## Core features

**Floating action panel.** A draggable, resizable panel rendered by a content
script, present on every allowed origin. Default closed, opens on a hotkey or
extension icon click. Grid of buttons, each with an icon, a short label, and
a colour. Multiple pages of buttons, swipeable or tabbed. Per-origin button
sets so Medicus shows Medicus buttons only.

**Button types.** Five primitives. `NAVIGATE` pushes the active tab to a URL.
`INJECT_TEXT` focuses a target field by selector or aria-label and types a
string; supports literal and templated text. `CLICK` targets an element by
selector, aria-label, or visible text and fires a click. `WAIT_FOR_DOM`
holds for a CSS selector to appear or disappear, with timeout.
`RUN_WORKFLOW` chains a saved multi-step workflow.

**Workflow recorder.** A button-press starts recording. The content script
attaches listeners to the page and logs each user action: clicks, key
presses, focus changes, navigations, DOM mutations following each user
action. The user demonstrates a workflow then presses stop. The extension
converts the captured trace into the smallest sequence of primitives that
reproduces it, and offers an inline editor where the user names the
workflow, deletes redundant steps, adds waits, sets the commit mode, and
assigns it to a button.

**Workflow replay.** A run button executes the workflow with each step
displayed as a visible toast in the corner. The user can pause, step
forward, or abort. A safety mode runs a dry preview that highlights what
each step would interact with before any action fires.

**Workflow library.** Local-first storage of all buttons, pages, and
workflows. Optional export to JSON for sharing between users. Optional
import. No cloud sync in the MVP; rely on Chrome's `chrome.storage.sync` if
cross-device sync is requested.

**Editor.** A full-page extension UI accessed via the extension icon's
right-click menu and from a settings cog inside the floating panel. Layouts
of pages, buttons, icons, colours, and key bindings are edited here.
Workflows are inspectable and editable step by step.

**Hotkeys.** The user can bind any button to a keyboard shortcut via
Chrome's `commands` API or via a content-script `keydown` listener within
the active tab. Stream Deck hardware support is out of scope for v1 but the
architecture should not preclude it.

## The safety catch

This is the headline new feature. Every workflow declares one of three
commit modes. The mode is set by the user when they save the workflow and
can be changed later in the editor. Default is **SAFE**.

**SAFE mode.** Submit-class buttons (a curated list per origin plus
heuristics: `type=submit`, role=button with text matching *Send*, *Save and
Close*, *Sign and Send*, *Confirm Prescription*, *Submit*, *Issue*) trigger
an automatic `STOP_FOR_USER`. The workflow halts, surfaces a toast, and the
user clicks the final button manually. This is the safest mode and is
sufficient for the majority of workflows.

**CONFIRM mode.** The workflow runs through to the Submit-class step, then
pauses with a prominent toast asking *Fire? Continue or Abort*. User taps
Continue and the Submit fires. User taps Abort and the workflow rolls back
any draft text it injected, then exits. Useful when the workflow is reliable
but the user wants eyes on every commit.

**LIVE mode.** The workflow runs end-to-end including the Submit-class step.
No pause. This is the fast lane.

LIVE mode requires arming. Two layers of safety apply.

First, **eligibility**. A workflow cannot run in LIVE mode unless it has
been explicitly marked LIVE-eligible in the editor. This is a per-workflow
checkbox, off by default, and changing it is logged. Marking a workflow
LIVE-eligible without first running it successfully in SAFE or CONFIRM mode
at least three times prompts a warning.

Second, **per-execution arming**. Even on a LIVE-eligible workflow, the run
button defaults to running in CONFIRM mode. To execute LIVE, the user taps
ARM. The button border turns red. The user has five seconds to tap RUN. If
they do not, the button auto-disarms and reverts. After a successful LIVE
execution, the button auto-disarms. Arm state is per-session and per-button:
closing the tab clears all arms. There is no global "always armed" setting.

**Visual language during LIVE execution.** The replay toast is red bordered.
The header text is `LIVE FIRE: {workflow name}`. Each step toast shows a red
dot. The final commit toast is full-width at the top of the viewport for two
seconds before clearing. Anyone watching the screen can see immediately that
an irreversible action just happened.

**Failure handling.** LIVE mode never overrides selector failure. If any
step misses its target, the workflow aborts immediately, draft text is
rolled back where possible, and the abort is logged with the failed
selector. No best-guess clicking, no retry-with-fuzzy-matching, no
auto-Submit on a degraded run.

**Audit log.** Every LIVE execution writes a distinct audit entry with a red
flag, the workflow ID, the timestamp, the origin, the patient context if
extractable from the URL, the steps fired, and the outcome. The editor
surfaces a separate count of LIVE runs per workflow so the user knows how
often each one is being trusted.

**Disabling LIVE entirely.** The editor has a top-level kill switch that
disables all LIVE-eligible flagging across the workspace. A practice manager
or CSO who installs Triska across a team can ship the workspace with LIVE
disabled and the kill switch locked behind an admin password. Use this for
shared devices.

## Other safety design

**Autosave awareness.** Some clinical apps auto-persist drafts on every
keystroke. The recorder annotates workflows that include `INJECT_TEXT` steps
with a note that draft data may be left if the workflow is aborted partway.
Replay records the prior content of the target field before injection and
offers a one-click rollback on abort.

**Action log.** Every replay (SAFE, CONFIRM, or LIVE) writes a local audit
log of timestamp, origin, mode, workflow ID, steps fired, and outcome.
Browseable from the editor. Never leaves the device.

**Information governance.** The recorder redacts text content from logged
steps unless the field is identified as a clinical search box. Storage is
local and never transmitted, but the export format is a JSON file the user
controls; warn the user before export. Free-text search injections such as
SNOMED queries are stored verbatim because they are required for replay;
this is documented in the editor.

## Technical stack

Manifest V3. TypeScript. React for the editor and panel, with Vite. Tailwind
for styling. No frameworks beyond that.

**Component layout.** A background service worker handles cross-tab
messaging and `chrome.commands` hotkeys. A content script is injected into
all matched origins; it owns the floating panel, the action executor, the
recorder, and the arming state machine. An options page is the editor.
Storage is `chrome.storage.local` for everything, with optional
`chrome.storage.sync` mirroring for cross-device.

**Element targeting.** The recorder builds three candidate selectors per
element in priority order: a CSS path anchored on stable attributes, a role
plus accessible name selector, and a text-content fallback. At replay time
the executor tries each in turn. If none match, replay halts.

**DOM stability.** After every action the executor waits for either a
configured target selector to appear or for a quiet period where
`MutationObserver` reports no changes for n milliseconds. Fixed sleeps are a
fallback only.

**Permissions.** The MVP requests host permissions only for origins the
user explicitly enables. Default install ships with no host permissions; the
user enables Medicus or whichever app from the editor and Chrome prompts
for the matching origin.

**Origin-scoped storage.** Buttons, pages, and workflows are tagged with the
origin they were authored on. Switching tabs to a different origin shows a
different deck or no deck at all.

## Data model

A `Workspace` is the top-level user configuration. It contains many
`Origin`s, each of which contains many `Page`s of buttons, and many
`Workflow`s.

A `Button` has an ID, a label, an icon, a colour, an optional hotkey, and
either a single primitive action or a `workflowId`.

A `Workflow` has an ID, a name, an origin, a list of `Step`s, a `commitMode`
(`SAFE`, `CONFIRM`, `LIVE`), a `liveEligible` boolean, a `successCount`, a
`liveRunCount`, and metadata: created timestamp, last-edited, last-run.

A `Step` is one of the five primitives, with target selectors, parameters,
and optional pre and post-condition selectors.

An `ArmingState` is held in memory only and lives in the content script. It
maps `buttonId` to `{ armed: bool, armedAt: timestamp }`. It clears on tab
close, on disarm, on successful LIVE execution, and on the five-second
timeout.

All persistent entities serialise to JSON. The export format is the
workspace JSON.

## UI design notes

The floating panel should feel light, draggable, and unobtrusive. Default
position bottom-right. Rounded corners. Six buttons per row in a grid that
adapts to panel width. Each button shows icon and label, with a hover
tooltip showing the action's destination, first step, or workflow commit
mode.

**Button visual states.** SAFE workflows render in default colour. CONFIRM
workflows render with an amber border. LIVE-eligible workflows render with
a thin red border at rest. When ARMED, the border becomes a thick red glow
with a five-second countdown ring. Post-execution, the button briefly
flashes green for success or red for abort.

Two visual modes: compact (icon only) and expanded (icon plus label). User
toggles with a button in the panel header.

The recorder UI is a separate small overlay during recording, with a red
dot, an action counter, an undo last action button, and a stop button.
After stop, a modal shows the captured steps with the option to delete,
reorder, or insert a wait between any two steps. Save attaches to a button
and prompts for commit mode.

The editor is a two-column layout: left is the page tree (origins, pages
within origins), right is the page being edited with drag-and-drop button
arrangement. A separate Workflows tab lists all workflows with their
associated buttons, commit mode, LIVE-eligible flag, run counts, and an
inline run-now control.

## Build sequence

- **Phase 0 — scaffolding.** Project setup with Vite, TypeScript, React,
  Manifest V3 boilerplate. A trivial extension that injects a hello-world
  floating panel into a single test origin. **(Current phase.)**
- **Phase 1 — primitive actions.** Implement `NAVIGATE`, `CLICK`,
  `WAIT_FOR_DOM`. Hard-code two test buttons. Prove the executor works on
  Medicus by reproducing a known click chain.
- **Phase 2 — `INJECT_TEXT` and the editor.** Add the typing primitive with
  selector targeting. Build the editor as an options page. Wire it to
  `chrome.storage.local`. The user can author buttons by hand without the
  recorder.
- **Phase 3 — the recorder.** Capture clicks, key presses, navigations.
  Convert the trace to primitives. Show the captured steps in a modal. Save
  to storage. Expect to iterate on selector generation.
- **Phase 4 — replay with SAFE mode.** Toasts, pause, step, abort. Audit
  logging. Submit-class detection. Draft rollback on abort. SAFE is the
  only commit mode in this phase.
- **Phase 5 — CONFIRM mode.** Add the pause-before-Submit toast and the
  continue or abort handling. Small extension of phase 4.
- **Phase 6 — LIVE mode and arming.** The arming state machine. Visual
  states. Five-second timeout. Auto-disarm on execution. The kill switch.
  The LIVE audit log. This is the highest-stakes code in the project;
  reserve generous time.
- **Phase 7 — polish.** Hotkey binding. Per-origin permissions. Export and
  import. Icon library. Colour pickers. First-run onboarding.
- **Phase 8 — Medicus pre-loaded pack.** Ship a default origin pack for
  `england.medicus.health` with the most useful buttons baked in: jump to
  each task list, switch right panel to each of the seventeen views, focus
  Codes and actions and inject slash, focus and inject dot, set Status
  radios. All ship as SAFE by default.

## Known-good Medicus shortcuts to bake in

Validated against the live UI as of investigation. URLs and selectors should
be stored as constants and revalidated periodically.

Task list deep links use the pattern
`/{tenant}/tasks/{task_type}/task-list?statuses[]=…&masterAssignee={role_uuid}&viewContext=homepage`.
Task types observed: `medical_patient_request_task`, `general_task`,
`prescription_request_task_non_routine`, `prescription_request_task_routine`.
Status values observed: `new-request`, `awaiting-recipient-response`,
`reply-received`, `pending-review`, `incomplete`.

Inside a task, the right panel switcher is a combobox with role search.
Switch by setting its value to one of: Care Record, Clinical Summary,
Journal, Medication Regimen, Medication History, Immunisations, Results and
Observations, Problems, Appointments, Personal Details, Registration, Data
Sharing, Tasks, Online Access, Booking Links, Internal Conversations,
Yellow Cards.

Inside the Codes and actions editor, the slash menu accepts substring
filtering. Useful one-tap mappings: Prescription via `/pres` + Enter,
Referral via `/ref` + Enter, Investigation via `/inv` + Enter, Fit note via
`/fit` + Enter, Procedure via `/proc` + Enter, Communication via `/com` +
Enter, Document via `/doc` + Enter, Future action via `/fut` + Enter,
QRisk via `/qri` + Enter, Immunisation via `/imm` + Enter. The dot prefix is
a literal SNOMED description search; abbreviations such as UTI do not work,
only full clinical terms.

## Open questions

- **Selector strategy for Medicus.** The page uses dynamic identifiers
  heavily. The recorder needs a robust fallback ordering. Lean on
  aria-label and accessible name first.
- **Sync vs local-only.** Decide whether to mirror to
  `chrome.storage.sync`. A simple compromise is to sync workspace metadata
  only and keep workflow blobs local.
- **Sharing.** Workflows shareable as files in v1. Anything more is
  post-launch.
- **Submit-class detection.** Detection by visible text is fragile. Decide
  whether to ship a curated list per origin or rely on heuristics.
  Recommend curated lists for Medicus, EMIS Web, Accurx, ICE, with a
  user-extendable denylist per workspace.
- **Audit log retention.** Local-only is fine for v1. Practice-wide audit is
  a v2 conversation.
- **LIVE mode adoption guardrails.** Decide whether to require a tutorial or
  knowledge check before a user can flag any workflow as LIVE-eligible for
  the first time. Recommend a one-time modal explaining the model.

## Risks

- **DOM churn.** Mitigated by aria-name selectors and clear failure modes
  when selectors miss.
- **Inadvertent commits in SAFE or CONFIRM mode.** Mitigated by Submit-class
  detection.
- **Inadvertent commits in LIVE mode.** Mitigated by per-execution arming,
  five-second timeout, auto-disarm, and selector-miss abort.
- **Draft contamination.** Mitigated by autosave-aware rollback on abort.
- **Clinician error from over-trust.** The biggest risk. The extension makes
  things faster, which means errors propagate faster. Mitigation is the
  deliberately visible LIVE FIRE replay UI, the audit log, and the kill
  switch for shared-device deployments.
- **Information governance.** The recorder may capture patient text
  fragments. Mitigation is field-type-aware redaction in step logs and a
  pre-export warning.
- **Regulatory framing.** If this extension is deployed beyond the
  developer's own use, consider DCB0129 manufacturer responsibilities. The
  author of this plan holds CSO credentials; the extension should ship with
  a hazard log from day one. This is not optional for clinical adoption.

## Definition of done for v1

A user can install the extension, grant host permission for Medicus, and
find a default deck of working SAFE shortcuts on first load. They can
record a new workflow, save it to a button with a chosen commit mode, and
replay it on demand. They can mark a workflow LIVE-eligible, arm a button,
and execute end-to-end. They can edit any button's properties from the
editor. They can export their workspace and import it elsewhere. Every
replay is captured in the audit log; LIVE runs are flagged distinctly. The
kill switch disables LIVE workspace-wide. A hazard log document ships
alongside the codebase.

## Stretch goals beyond v1

- A natural-language workflow generator: the user types "open this
  patient's medication history and copy the list" and an LLM generates the
  steps using the captured selector library.
- A Stream Deck hardware bridge: a small companion app that maps physical
  Stream Deck buttons to extension button IDs.
- Practice-wide deployment via a managed Chrome policy that pre-installs
  the extension and pre-loads a curated workspace with LIVE disabled and
  the kill switch locked.
- A workflow marketplace, gated by a clinical safety review process, where
  vetted workflows are published and signed.
- Two-person rule for high-risk LIVE workflows: certain workflows can be
  flagged as requiring a second clinician's tap on a paired device before
  they fire. Useful for controlled drug prescriptions and other
  high-stakes operations.
