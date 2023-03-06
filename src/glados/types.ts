import { App } from "@slack/bolt";

export interface GladosPlugin {
  name: string;
  description?: string;
  setup: (app: App) => void;
}
