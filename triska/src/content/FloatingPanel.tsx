import { useEffect, useState } from 'react';

const TOGGLE_EVENT = 'triska:toggle';

export function FloatingPanel() {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    const onToggle = () => setOpen((v) => !v);
    window.addEventListener(TOGGLE_EVENT, onToggle);
    return () => window.removeEventListener(TOGGLE_EVENT, onToggle);
  }, []);

  if (!open) {
    return (
      <button
        className="triska-launcher"
        onClick={() => setOpen(true)}
        title="Open Triska"
      >
        T
      </button>
    );
  }

  return (
    <div className="triska-panel" role="dialog" aria-label="Triska panel">
      <header className="triska-header">
        <span className="triska-title">Triska</span>
        <span className="triska-tag">Phase 0 · hello world</span>
        <button
          className="triska-close"
          aria-label="Close panel"
          onClick={() => setOpen(false)}
        >
          ×
        </button>
      </header>
      <div className="triska-grid">
        <button className="triska-btn" disabled>Stub 1</button>
        <button className="triska-btn" disabled>Stub 2</button>
        <button className="triska-btn" disabled>Stub 3</button>
      </div>
      <footer className="triska-footer">
        Buttons are placeholders until Phase 1.
      </footer>
    </div>
  );
}
