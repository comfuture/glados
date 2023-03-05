import dotenv from "dotenv";
import { App } from "@slack/bolt";
import image from "./funcs/image";
import chat from "./funcs/chat";

dotenv.config();

export const app = new App({
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
  image.setup(app);
  chat.setup(app);

  // Start your app
  await app.start(process.env.PORT || 6014).then(() => {
    console.info("⚡️ Bolt app is running!");
  });
})();
