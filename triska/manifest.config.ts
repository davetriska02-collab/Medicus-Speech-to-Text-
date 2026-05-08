import { defineManifest } from '@crxjs/vite-plugin';
import pkg from './package.json';

export default defineManifest({
  manifest_version: 3,
  name: 'Triska',
  version: pkg.version,
  description: pkg.description,
  action: {
    default_title: 'Open Triska editor',
  },
  background: {
    service_worker: 'src/background/service-worker.ts',
    type: 'module',
  },
  options_page: 'src/options/index.html',
  permissions: ['storage', 'activeTab'],
  content_scripts: [
    {
      matches: ['https://*.medicus.health/*', 'http://localhost/*'],
      js: ['src/content/index.tsx'],
      run_at: 'document_idle',
    },
  ],
  commands: {
    'toggle-panel': {
      suggested_key: {
        default: 'Ctrl+Shift+T',
        mac: 'Command+Shift+T',
      },
      description: 'Toggle Triska floating panel',
    },
  },
});
