import { EMPTY_WORKSPACE, type Workspace } from '../types';

const KEY = 'triska.workspace';

export async function loadWorkspace(): Promise<Workspace> {
  const raw = await chrome.storage.local.get(KEY);
  return (raw[KEY] as Workspace) ?? EMPTY_WORKSPACE;
}

export async function saveWorkspace(ws: Workspace): Promise<void> {
  await chrome.storage.local.set({ [KEY]: ws });
}

export function subscribe(cb: (ws: Workspace) => void): () => void {
  const handler = (
    changes: Record<string, chrome.storage.StorageChange>,
    area: string,
  ) => {
    if (area !== 'local') return;
    if (!changes[KEY]) return;
    cb((changes[KEY].newValue as Workspace) ?? EMPTY_WORKSPACE);
  };
  chrome.storage.onChanged.addListener(handler);
  return () => chrome.storage.onChanged.removeListener(handler);
}
