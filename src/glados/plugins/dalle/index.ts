import { Section, Image, Text, Context, Button, Modal } from "../../blocks";
import openai from "../../utils/openai";
import { App } from "@slack/bolt";
import { definePlugin } from "../..";
import { drawImage } from "./handlers";

const setup = (app: App) => {
  app.message("그려줘", async ({ message, say, context }) => {});

  app.command("/imagine", async ({ command, ack, say, client }) => {
    await ack();
    // if (!command.text) {
    //   client.views.open({
    //     trigger_id: body.trigger_id,
    //     view: Modal({
    //       title: "그림 그리기",
    //       blocks: [Section({})],
    //     }),
    //   });
    // }

    const loading = await say(`그리는 중...`);
    const buff = await drawImage(command.text);

    await client.chat.delete({ ts: loading.ts!, channel: command.channel_id });

    const uploadResult = client.files.upload({
      channels: command.channel_id,
      thread_ts: command.thread_ts,
      file: buff,
      alt_text: command.text,
    });
    await say({
      blocks: [Section({ text: Text(command.text) })],
    });
  });
};

export default definePlugin({
  name: "DALL E",
  setup,
});
