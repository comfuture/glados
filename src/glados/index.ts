import { App } from "@slack/bolt";
import { GladosPlugin } from "./types";

export class Bot extends App {
  /** plugin을 등록합니다. */
  public registerPlugin(plugin: GladosPlugin) {
    plugin.setup(this);
    console.info(`[GLaDOS] ${plugin.name} plugin is loaded.`);
  }
}

/** plugin을 define합니다. */
export function definePlugin(plugin: GladosPlugin) {
  return plugin;
}
