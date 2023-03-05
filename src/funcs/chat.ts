import { App, GenericMessageEvent } from "@slack/bolt";
import { Block, KnownBlock } from "@slack/types";
import { ClientRequest } from "http";

import type {
  ChatCompletionRequestMessage,
  ChatCompletionRequestMessageRoleEnum,
} from "openai";
import openai from "../assistant";

import { Markdown, Section, Text } from "../blocks";

// 캐릭터 셋업
const BOT_CHARACTER: ChatCompletionRequestMessage = {
  role: "system",
  content:
    "The assistant is a chatbot that can talk to humans. Try to be nice.",
};

const HISTORY: { [x: string]: ChatCompletionRequestMessage[] } = {};

/** 발화/응답 히스토리를 유저별로 저장 */
const saveHistory = (
  owner: string,
  content: string,
  role: ChatCompletionRequestMessageRoleEnum = "user"
) => {
  if (HISTORY[owner] === undefined) {
    HISTORY[owner] = [];
  }
  HISTORY[owner].push({ role, content });
};

/** 특정 사용자의 히스토리를 제거 */
const clearHistory = (owner: string) => {
  HISTORY[owner] = [];
};

const setup = (app: App) => {
  console.info("Chat module loaded");
  app.message(async ({ message: _message, say, context }) => {
    const message: GenericMessageEvent = _message as GenericMessageEvent;
    // 봇에게 직접 메시지를 보낸 경우
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

    const content: string | undefined = message.text
      ?.replace(`<@${context.botUserId}>`, "")
      .trim();

    // 내용이 없는 경우 무시
    if (!content) {
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

    saveHistory(message.user, content);
    const result = await openai.createChatCompletion({
      model: "gpt-3.5-turbo",
      messages: [BOT_CHARACTER, { role: "user", content }],
      max_tokens: 1024,
      temperature: 0.6,
      frequency_penalty: 0.4,
    });

    const response = result.data.choices[0].message?.content!.trim()!;
    saveHistory(message.user, response, "assistant");
    if (/\`\`\`/.test(response)) {
      // 코드블럭이 포함된 경우
      // 코드 블럭을 기준으로 나누어 일반 블럭은 텍스트로, 코드블럭은 마크다운 블럭으로 만듬
      const blocks: Block[] | KnownBlock[] = response
        .split(/\`\`\`\s+/)
        .map((v, i) => {
          if (i % 2 === 0) {
            return Section({ text: Text(v) });
          } else {
            return Section({ text: Markdown("```" + v + "```") });
          }
        });

      await say({
        blocks,
      });
    } else {
      await say(response);
    }
  });
};

export default {
  setup,
};
