import { INotebookTracker } from '@jupyterlab/notebook';

export function activateCopyContext(notebookTracker: INotebookTracker): void {
  const btn = document.createElement('button');
  btn.textContent = 'Copy Context';
  btn.style.cssText =
    'position:fixed;z-index:10000;bottom:24px;right:24px;padding:8px 12px;border-radius:6px;border:none;background:#333;color:#fff;cursor:pointer;display:none;font-size:13px;';
  document.body.appendChild(btn);

  const hide = (): void => {
    btn.style.display = 'none';
  };

  document.addEventListener('selectionchange', () => {
    const sel = window.getSelection()?.toString() ?? '';
    if (!sel || sel.length < 2) {
      hide();
      return;
    }
    const nbPanel = notebookTracker.currentWidget;
    if (nbPanel?.content?.activeCell) {
      btn.style.display = 'block';
      btn.onclick = async () => {
        const cell = nbPanel.content.activeCell;
        const idx = nbPanel.content.activeCellIndex;
        const path = nbPanel.context.path;
        const payload = {
          type: 'notebook_cell',
          content: sel,
          filePath: path,
          language: cell.model.mimeType?.includes('python') ? 'python' : 'unknown',
          cellIndex: idx,
          startLine: 1,
          endLine: sel.split('\n').length,
        };
        await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
        hide();
      };
      return;
    }
    hide();
  });
}
