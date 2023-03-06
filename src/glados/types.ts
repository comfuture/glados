import { App } from "@slack/bolt";

export interface GladosPlugin {
  setup: (app: App) => void;
}
