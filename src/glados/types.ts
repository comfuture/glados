import { App } from "@slack/bolt";
import { Bot } from ".";

export interface GladosPlugin {
  name: string;
  description?: string;
  setup: (app: Bot) => void;
  [key: string]: ((...args: any[]) => any) | string | undefined;
}
