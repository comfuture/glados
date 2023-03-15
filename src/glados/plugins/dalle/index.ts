import { App, DialogSubmitAction } from "@slack/bolt";
import sanitizeFilename from "sanitize-filename";
import { definePlugin } from "../..";
import { Context, Text } from "../../blocks";
import { drawImage, ImagePromptDialog } from "./handlers";

function isDialogSubmitAction(action: any): action is DialogSubmitAction {
  return action.type === "dialog_submission";
}

const setup = (app: App) => {
  app.message("그려줘", async ({ message, say, context }) => {});

  app.view("imagine-modal", async ({ ack, body, view, client, context }) => {
    await ack();
    console.log(body, view, client, context);
  });

  app.command("/imagine", async ({ command, ack, say, client }) => {
    await ack();
    if (!command.text) {
      await client.views.open({
        trigger_id: command.trigger_id,
        view: ImagePromptDialog(),
      });
      return;
    }

    const loading = await say({
      text: `/imagine ${command.text}`,
      username: command.user_name,
      icon_url: command.user_profile?.image_72,
      as_user: true,
    });

    await app.client.reactions.add({
      name: "hourglass",
      channel: command.channel_id,
      timestamp: loading.ts,
    });

    const buff = await drawImage(command.text);
    await client.filesUploadV2({
      channels: command.channel_id,
      thread_ts: command.thread_ts,
      file: buff,
      alt_text: command.text,
      filename: sanitizeFilename(`${command.text.substring(0, 50)}.png`),
    });

    await say({
      channel: command.channel_id,
      thread_ts: command.thread_ts,
      blocks: [Context([Text(command.text)])],
    });

    app.client.reactions.remove({
      name: "hourglass",
      channel: command.channel_id,
      timestamp: loading.ts,
    });
  });
};

export default definePlugin({
  name: "DALL E",
  setup,
});
