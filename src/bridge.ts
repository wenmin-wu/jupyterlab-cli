import { JupyterFrontEnd } from '@jupyterlab/application';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { PageConfig } from '@jupyterlab/coreutils';

/**
 * Connect to /jupyterlab-cli/ws and reload notebooks when the server broadcasts updates.
 */
export function activateBridge(
  app: JupyterFrontEnd,
  docManager: IDocumentManager
): void {
  const token = PageConfig.getToken();
  const base = PageConfig.getBaseUrl();
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${proto}//${window.location.host}${base}jupyterlab-cli/ws?token=${encodeURIComponent(
    token || ''
  )}`;

  let ws: WebSocket | null = null;
  try {
    ws = new WebSocket(url);
  } catch (e) {
    console.warn('jupyterlab-cli bridge: WebSocket failed', e);
    return;
  }

  ws.onmessage = (ev: MessageEvent) => {
    try {
      const msg = JSON.parse(ev.data as string);
      if (msg.type === 'notebook_updated' && msg.path) {
        const m = docManager.findWidget(msg.path);
        if (m?.context) {
          void m.context.revert();
        }
      }
    } catch {
      /* ignore */
    }
  };
}
