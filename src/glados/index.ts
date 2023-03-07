import { App, AppOptions } from "@slack/bolt";
import { GladosPlugin } from "./types";

/** plugin을 define합니다. */
export function definePlugin(plugin: GladosPlugin) {
  return plugin;
}

const corePlugin = definePlugin({
  name: "glados",
  description: "GLaDOS core plugin",
  setup(app) {
    app.command("/glados", async ({ command, ack, say, client }) => {
      await ack();
      await say(command.text);
      await say(JSON.stringify(command.text.split(" ")));
    });
  },
});

export class Bot extends App {
  private plugins: GladosPlugin[] = [];

  constructor(options: AppOptions) {
    super(options);
    this.registerPlugin(corePlugin);
  }

  /** plugin을 등록합니다. */
  public registerPlugin(plugin: GladosPlugin) {
    try {
      plugin.setup(this);
      this.plugins.push(plugin);
      console.info(`[GLaDOS] ${plugin.name} plugin is loaded.`);
    } catch (e) {
      console.error(`[GLaDOS] ${plugin.name} plugin is failed to load.`);
    }
  }
}
