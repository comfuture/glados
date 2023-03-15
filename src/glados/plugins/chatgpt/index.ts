import {
  App,
  GenericMessageEvent,
  FileShareMessageEvent,
  SayArguments,
} from "@slack/bolt";
import { Block, KnownBlock } from "@slack/types";
import { definePlugin } from "../..";

import type { ChatCompletionRequestMessage } from "openai";
import openai from "../../utils/openai";

import { Actions, Button, Markdown, Section, Text } from "../../blocks";
import { SessionManager } from "./session";
import { chatCompletion, formatResponse } from "./handlers";
import { ClientRequest } from "http";

/** test if message is a direct message or a channel message */
function isGenericMessageEvent(message: any): message is GenericMessageEvent {
  const isDirectMessage =
    message.channel_type === "im" || message.channel_type === "mpim";
  const isChannelMessage = message.channel_type === "channel";
  return isDirectMessage || isChannelMessage;
}

/** test if message has audio files */
function isAudioMessageEvent(message: any): message is FileShareMessageEvent {
  return (
    message.subtype === "file_share" &&
    message.files.length > 0 &&
    message.files[0]?.media_display_type === "audio"
  );
}

// 채팅 초기화 블록
const sessionManageToolbar: KnownBlock[] = [
  Section({
    text: Markdown("대화를 종료하려면 눌러주세요"),
    accessory: Button("대화세션 종료", {
      id: "chatgpt:clearSession",
      value: "chatgpt:clearSession",
    }),
  }),
];

const setup = (app: App) => {
  app.message(async ({ message, say, client, context }) => {
    if (!isGenericMessageEvent(message)) {
      return;
    }
    // debug print
    console.info("Message received: ", message);

    // DM 또는 멀티채널에서 봇을 언급한 경우
    const isDirectMessage =
      message.channel_type === "im" || message.channel_type === "mpim";

    // 채널에서 봇을 언급한 경우
    const isMentioned = message.text?.includes(`<@${context.botUserId}>`);

    // 봇에게 직접 메시지를 보낸 경우 또는 채널에서 봇을 언급한 경우 또는 세션이 활성화된 경우가 아니면 무시
    if (
      !(
        isDirectMessage ||
        isMentioned ||
        SessionManager.hasSession(message.user)
      )
    ) {
      return;
    }

    let content: string =
      message.text?.replace(`<@${context.botUserId}>`, "").trim() ?? "";

    // 내용이 없는 경우 무시
    if (!content) {
      // 오디오 첨부파일이 있는 경우
      if (isAudioMessageEvent(message)) {
        // TODO: whisper로 stt 한다음 content에 넣는다.
      }
      return;
    }

    // 나쁜말 체크?
    const moderationResult = await openai.createModeration({
      input: content,
    });

    for (const check of moderationResult.data.results) {
      if (Object.values(check.categories).some((v) => v)) {
        await say("나쁜말 하지마세요");
        return;
      }
    }

    // 메시지에 모래시계 이모티콘 붙이기
    app.client.reactions.add({
      name: "hourglass",
      channel: message.channel,
      timestamp: message.ts,
    });

    const session = SessionManager.getSession(message.user);
    const response = await chatCompletion(content, session);

    // 메시지에서 모래시계 이모티콘 제거
    app.client.reactions.remove({
      name: "hourglass",
      channel: message.channel,
      timestamp: message.ts,
    });

    const blocks = formatResponse(response);

    await say({
      text: response,
      blocks,
      thread_ts: message.thread_ts,
    });
    const ret = await client.chat.postEphemeral({
      blocks: sessionManageToolbar,
      thread_ts: message.thread_ts,
      user: message.user,
      channel: message.channel,
    });
    session.setActionsBlockTs(ret.message_ts!);
  });

  // TODO: 채팅을 초기화하는 액션
  app.action(
    "chatgpt:clearSession",
    async ({ ack, say, body, client, context }) => {
      await ack();
      const sayGoodbye = body.channel
        ? `<@${body.user.id}> 대화를 종료합니다.`
        : "대화를 종료합니다.";

      client.chat.postEphemeral({
        text: `${sayGoodbye} 다시 대화하시려면 DM으로 말씀하시거나 채널에서 <@${context.botUserId}>를 언급해주세요.`,
        channel: body.channel?.id!,
        user: body.user.id,
      });
      SessionManager.clearSession(body.user.id);
    }
  );

  app.event("app_mention", async ({ event, say, client }) => {
    if (event.thread_ts) {
      // TODO: 스레드에서 언급한 경우, 스레드의 첫 메시지를 가져와 응답
      const thread = await client.conversations.replies({
        channel: event.channel,
        ts: event.thread_ts,
        limit: 1,
      });
      if (thread.messages?.length ?? 0 > 0) {
        SessionManager.clearSession(event.user!); // 컨텍스트 전환을 위해 세션을 초기화함
        const session = SessionManager.getSession(event.user!);

        app.client.reactions.add({
          name: "ok_hand",
          channel: event.channel,
          timestamp: event.ts,
        });

        // 스레드의 첫 글을 사용자가 발화한 것으로 간주하여 대화 시작
        // 언급에 추가 메시지가 있는 경우에는 그 메시지도 사용자 발화로 간주
        let prompt = thread.messages![0].text!;
        if (event.text.length > 0) {
          prompt += `\n${event.text}`;
        }
        const response = await chatCompletion(prompt, session);

        app.client.reactions.remove({
          name: "ok_hand",
          channel: event.channel,
          timestamp: event.ts,
        });

        const blocks = formatResponse(response);
        await say({
          text: response,
          blocks,
          thread_ts: thread.messages![0].thread_ts,
        });
      }
    } else {
      // TODO: 유저의 최근 대화를 n개 가져와 응답
      const history = await client.conversations.history({
        channel: event.channel,
        user: event.user,
        latest: event.ts,
        inclusive: false,
      });
      history.messages;
      console.log("-----");
      for (const message of history.messages ?? []) {
        console.log(message);
      }
    }
  });
};

export default definePlugin({
  name: "ChatGPT",
  setup,
});
