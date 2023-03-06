import { Section, Image, Text, Context, Button, Modal } from "../../blocks";
import openai from "../../utils/openai";
import { App } from "@slack/bolt";
import { definePlugin } from "../..";

const setup = (app: App) => {
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
    const response = await openai.createImage({
      prompt: command.text,
      n: 1,
      size: "1024x1024",
    });
    const imageUrls = response.data.data as { url: string }[];
    await client.chat.delete({ ts: loading.ts!, channel: command.channel_id });
    await client.files.uploadV2({
      channels: command.channel_id,
      file: imageUrls[0].url,
      alt_text: command.text,
    });
    await say({
      blocks: [
        Image(imageUrls[0].url, command.text, { title: Text(command.text) }),
      ],
    });
  });
};

export default definePlugin({
  name: "DALL E",
  setup,
});
