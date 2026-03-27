import { PageConfig } from '@jupyterlab/coreutils';
import { ISettingRegistry } from '@jupyterlab/settingregistry';
import type { ITerminalTracker } from '@jupyterlab/terminal';

const PLUGIN_ID = 'jupyterlab-cli-frontend:clipboard-image';

export async function activateClipboardImage(
  settingRegistry: ISettingRegistry,
  terminalTracker: ITerminalTracker
): Promise<void> {
  let enabled = true;
  try {
    const s = await settingRegistry.load(PLUGIN_ID);
    enabled = (s.get('enabled').composite as boolean) ?? true;
    s.changed.connect(() => {
      enabled = (s.get('enabled').composite as boolean) ?? true;
    });
  } catch {
    /* default */
  }

  const base = PageConfig.getBaseUrl();
  const token = PageConfig.getToken();

  terminalTracker.widgetAdded.connect((_, widget) => {
    const term = widget.content;
    term.node.addEventListener('paste', async (ev: ClipboardEvent) => {
      if (!enabled) {
        return;
      }
      const items = ev.clipboardData?.items;
      if (!items) {
        return;
      }
      for (let i = 0; i < items.length; i++) {
        const it = items[i];
        if (it.type.startsWith('image/')) {
          ev.preventDefault();
          const blob = it.getAsFile();
          if (!blob) {
            continue;
          }
          const buf = await blob.arrayBuffer();
          const r = await fetch(`${base}jupyterlab-cli/clipboard/image?token=${encodeURIComponent(token || '')}`, {
            method: 'POST',
            body: buf,
            headers: { 'Content-Type': 'application/octet-stream' },
          });
          if (r.ok) {
            const j = (await r.json()) as { path?: string };
            if (j.path) {
              await navigator.clipboard.writeText(j.path);
            }
          }
          break;
        }
      }
    });
  });
}
