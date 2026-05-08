export type CommitMode = 'SAFE' | 'CONFIRM' | 'LIVE';

export type StepKind =
  | 'NAVIGATE'
  | 'CLICK'
  | 'INJECT_TEXT'
  | 'WAIT_FOR_DOM'
  | 'RUN_WORKFLOW';

export interface BaseStep {
  id: string;
  kind: StepKind;
}

export interface NavigateStep extends BaseStep {
  kind: 'NAVIGATE';
  url: string;
}

export interface ClickStep extends BaseStep {
  kind: 'CLICK';
  selectors: string[];
}

export interface InjectTextStep extends BaseStep {
  kind: 'INJECT_TEXT';
  selectors: string[];
  text: string;
}

export interface WaitForDomStep extends BaseStep {
  kind: 'WAIT_FOR_DOM';
  selector: string;
  timeoutMs: number;
  expect: 'appear' | 'disappear';
}

export interface RunWorkflowStep extends BaseStep {
  kind: 'RUN_WORKFLOW';
  workflowId: string;
}

export type Step =
  | NavigateStep
  | ClickStep
  | InjectTextStep
  | WaitForDomStep
  | RunWorkflowStep;

export interface Button {
  id: string;
  label: string;
  icon: string;
  color: string;
  hotkey?: string;
  action:
    | { kind: 'PRIMITIVE'; step: Step }
    | { kind: 'WORKFLOW'; workflowId: string };
}

export interface Page {
  id: string;
  name: string;
  buttons: Button[];
}

export interface Origin {
  origin: string;
  pages: Page[];
}

export interface Workflow {
  id: string;
  name: string;
  origin: string;
  steps: Step[];
  commitMode: CommitMode;
  liveEligible: boolean;
  successCount: number;
  liveRunCount: number;
  createdAt: number;
  updatedAt: number;
  lastRunAt?: number;
}

export interface AuditEntry {
  id: string;
  workflowId: string;
  timestamp: number;
  origin: string;
  mode: CommitMode;
  outcome: 'success' | 'aborted' | 'failed';
  steps: number;
  patientContext?: string;
  failedSelector?: string;
}

export interface Workspace {
  version: number;
  origins: Origin[];
  workflows: Workflow[];
  liveKillSwitch: boolean;
  killSwitchLocked: boolean;
  audit: AuditEntry[];
}

export const EMPTY_WORKSPACE: Workspace = {
  version: 1,
  origins: [],
  workflows: [],
  liveKillSwitch: false,
  killSwitchLocked: false,
  audit: [],
};
