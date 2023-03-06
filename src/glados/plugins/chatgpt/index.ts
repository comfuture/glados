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

// 캐릭터 셋업
const BOT_CHARACTER: ChatCompletionRequestMessage = {
  role: "system",
  content: "Use Korean as possible. Try to be nice.",
};

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
  Actions([
    Button("대화세션 종료", {
      id: "chatgpt:clearSession",
      value: "chatgpt:clearSession",
      style: "danger",
    }),
  ]),
];

const setup = (app: App) => {
  app.message(async ({ message, say, context }) => {
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

    // 봇에게 직접 메시지를 보낸 경우 또는 채널에서 봇을 언급한 경우가 아니면 무시
    if (!(isDirectMessage || isMentioned)) {
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

    // 메시지에 이모티콘 붙이기
    app.client.reactions.add({
      name: "white_check_mark",
      channel: message.channel,
      timestamp: message.ts,
    });

    const session = SessionManager.getSession(message.user);
    session.addHistory(content);

    const result = await openai.createChatCompletion({
      model: "gpt-3.5-turbo",
      messages: [BOT_CHARACTER, ...session.getHistory()],
      max_tokens: 1024,
      temperature: 0.6,
      frequency_penalty: 0.4,
    });

    const response = result.data.choices[0].message?.content!.trim()!;
    session.addHistory(response, "assistant");
    if (/\`\`\`/.test(response)) {
      // 코드블럭이 포함된 경우
      // 코드 블럭을 기준으로 나누어 일반 블럭은 텍스트로, 코드블럭은 마크다운 블럭으로 만듬
      // 코드 스니펫으로 만들어서 보내면 더 좋을 것 같은데... BlockKit처럼 여러번 반복 등장할 수 없다.
      const blocks: Block[] | KnownBlock[] = response
        .split(/\`\`\`/)
        .map((v, i) => {
          if (i % 2 === 0) {
            return Section({ text: Markdown(v) });
          } else {
            const langaugeMatch = /^\s*(\S+)/.exec(v);
            if (langaugeMatch) {
              langaugeMatch[1];
              v = v.replace(new RegExp("^(\\s*)" + langaugeMatch[1]), "$1");
            }
            return Section({
              text: Markdown("```" + v + "```"),
            });
          }
        });

      await say({
        text: response,
        thread_ts: message.thread_ts,
        blocks: [...blocks, ...sessionManageToolbar],
      });
    } else {
      await say(response);
    }
  });

  // TODO: 채팅을 초기화하는 액션
  app.action("chatgpt:clearSession", async ({ ack, say, body, client }) => {
    await ack();
    say(`<@${body.user.id}> 더이상 대화가 없어 채팅을 종료합니다`);
    SessionManager.clearSession(body.user.id);
  });

  app.event("app_mention", async ({ event, say, client }) => {
    if (event.thread_ts) {
      // TODO: 스레드에서 언급한 경우, 스레드의 첫 메시지를 가져와 응답
      // const thread = await client.conversations.replies({
      //   channel: event.channel,
      //   ts: event.thread_ts,
      //   limit: 1,
      // });
      // thread.messages;
    } else {
      // TODO: 유저의 최근 대화를 n개 가져와 응답
      // const history = await client.conversations.history({
      //   channel: event.channel,
      //   user: event.user,
      //   latest: event.ts,
      //   inclusive: false,
      // });
      // history.messages;
    }
  });
};

export default definePlugin({
  name: "ChatGPT",
  setup,
});
