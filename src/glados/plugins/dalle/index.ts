import { App } from "@slack/bolt";
import { definePlugin } from "../..";
import { Context, Text } from "../../blocks";
import { drawImage, ImagePromptDialog } from "./handlers";

const setup = (app: App) => {
  app.message("그려줘", async ({ message, say, context }) => {});

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
      filename: command.text,
    });

    app.client.reactions.remove({
      name: "hourglass",
      channel: command.channel_id,
      timestamp: loading.ts,
    });

    await client.chat.postMessage({
      channel: command.channel_id,
      thread_ts: command.thread_ts,
      blocks: [Context([Text(command.text)])],
    });
  });
};

export default definePlugin({
  name: "DALL E",
  setup,
});
