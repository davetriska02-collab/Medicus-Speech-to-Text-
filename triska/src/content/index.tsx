import { createRoot } from 'react-dom/client';
import { FloatingPanel } from './FloatingPanel';
import panelCss from './styles.css?inline';
import type { Message } from '../lib/messaging';

const HOST_ID = 'triska-host-root';
const TOGGLE_EVENT = 'triska:toggle';

function mount(): { toggle: () => void } {
  const existing = document.getElementById(HOST_ID);
  if (existing) {
    return { toggle: () => window.dispatchEvent(new CustomEvent(TOGGLE_EVENT)) };
  }

  const host = document.createElement('div');
  host.id = HOST_ID;
  host.style.all = 'initial';
  document.documentElement.appendChild(host);

  const shadow = host.attachShadow({ mode: 'open' });
  const styleEl = document.createElement('style');
  styleEl.textContent = panelCss;
  shadow.appendChild(styleEl);
  const reactRoot = document.createElement('div');
  shadow.appendChild(reactRoot);

  createRoot(reactRoot).render(<FloatingPanel />);
  return { toggle: () => window.dispatchEvent(new CustomEvent(TOGGLE_EVENT)) };
}

const handle = mount();

chrome.runtime.onMessage.addListener((msg: Message) => {
  if (msg.type === 'TOGGLE_PANEL') handle.toggle();
});
