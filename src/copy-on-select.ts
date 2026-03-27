import { ISettingRegistry } from '@jupyterlab/settingregistry';
import type { ITerminalTracker } from '@jupyterlab/terminal';

const PLUGIN_ID = 'jupyter-cli-frontend:copy-on-select';

export async function activateCopyOnSelect(
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
    /* use default */
  }

  terminalTracker.widgetAdded.connect((_, widget) => {
    const term = widget.content;
    term.node.addEventListener('mouseup', () => {
      if (!enabled) {
        return;
      }
      const sel =
        typeof (term as unknown as { getSelection?: () => string }).getSelection === 'function'
          ? (term as unknown as { getSelection: () => string }).getSelection()
          : '';
      if (sel) {
        void navigator.clipboard.writeText(sel);
      }
    });
  });
}
