/**
 * JupyterLab extension: WebSocket bridge + terminal copy-on-select + clipboard image + copy context.
 */
import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from '@jupyterlab/application';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { INotebookTracker } from '@jupyterlab/notebook';
import { ISettingRegistry } from '@jupyterlab/settingregistry';
import { ITerminalTracker } from '@jupyterlab/terminal';

import { activateBridge } from './bridge';
import { activateClipboardImage } from './clipboard-image';
import { activateCopyContext } from './copy-context';
import { activateCopyOnSelect } from './copy-on-select';

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyter-cli-frontend:plugin',
  autoStart: true,
  requires: [
    IDocumentManager,
    INotebookTracker,
    ISettingRegistry,
    ITerminalTracker,
  ],
  activate: (
    app: JupyterFrontEnd,
    docManager: IDocumentManager,
    notebookTracker: INotebookTracker,
    settingRegistry: ISettingRegistry,
    terminalTracker: ITerminalTracker
  ): void => {
    void activateBridge(app, docManager);
    void activateCopyOnSelect(settingRegistry, terminalTracker);
    void activateClipboardImage(settingRegistry, terminalTracker);
    activateCopyContext(notebookTracker);
  },
};

export default plugin;
