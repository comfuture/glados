import "./glados/utils/ensure_env";
import { Bot } from "./glados";
import dalle from "./glados/plugins/dalle";
import chatgpt from "./glados/plugins/chatgpt";

export const app = new Bot({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  appToken: process.env.SLACK_APP_TOKEN,
  socketMode: true,
});

app.use(async ({ next }) => {
  await next();
});

(async () => {
  // load modules
  app.registerPlugin(chatgpt);
  app.registerPlugin(dalle);

  // Start your app
  await app.start(process.env.PORT || 6014).then(() => {
    console.info("⚡️ Bolt app is running!");
  });
})();
