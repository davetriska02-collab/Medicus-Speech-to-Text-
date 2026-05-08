import type { Message } from '../lib/messaging';

chrome.action.onClicked.addListener(() => {
  chrome.runtime.openOptionsPage();
});

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== 'toggle-panel') return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  const msg: Message = { type: 'TOGGLE_PANEL' };
  await chrome.tabs.sendMessage(tab.id, msg).catch(() => {
    // no content script on this tab; ignore.
  });
});
