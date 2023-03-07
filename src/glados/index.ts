import * as shellQuote from "shell-quote";
import { App, AppOptions } from "@slack/bolt";
import { GladosPlugin } from "./types";

/** plugin을 define합니다. */
export function definePlugin(plugin: GladosPlugin) {
  return plugin;
}

const corePlugin = definePlugin({
  name: "GLaDOS",
  description: "GLaDOS core plugin",
  setup(app) {
    app.command("/glados", async ({ command: _command, ack, say, client }) => {
      await ack();
      const [command, ...remain] = _command.text.split(" ");
      const args = shellQuote.parse(remain.join(" ") ?? "");
      await say(`you called ${command} with ${JSON.stringify(args)}`);
    });
  },
});

export class Bot extends App {
  private _plugins: GladosPlugin[] = [];

  constructor(options: AppOptions) {
    super(options);
    this.registerPlugin(corePlugin);
  }

  get plugins() {
    return this._plugins;
  }

  /** plugin을 등록합니다. */
  public registerPlugin(plugin: GladosPlugin) {
    try {
      plugin.setup(this);
      this._plugins.push(plugin);
      console.info(`[GLaDOS] ${plugin.name} plugin is loaded.`);
    } catch (e) {
      console.error(`[GLaDOS] ${plugin.name} plugin is failed to load.`);
    }
  }
}
