import { App } from "@slack/bolt";
import { Block, KnownBlock } from "@slack/types";

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

const setup = (app: App) => {
  console.info("Chat module loaded");
  app.message(async ({ message, body, say, context }) => {
    // 봇에게 직접 메시지를 보낸 경우
    console.info("Message received: ", message);

    const isDirectMessage =
      message.channel_type === "im" || message.channel_type === "mpim";

    // 채널에서 봇을 언급한 경우
    const isMentioned = body.text.includes(`<@${context.botUserId}>`);

    if ((isDirectMessage || isMentioned) && message.subtype === undefined) {
      const content: string = body.text
        .replace(`<@${context.botUserId}>`, "")
        .trim();

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

      saveHistory(message.user, content);
      const result = await openai.createChatCompletion({
        model: "gpt-3.5-turbo",
        messages: [BOT_CHARACTER, { role: "user", content }],
        max_tokens: 1024,
        temperature: 0.6,
        frequency_penalty: 0.4,
      });

      const aiSays = result.data.choices[0].message?.content!.trim()!;
      saveHistory(message.user, aiSays, "assistant");
      if (/\`\`\`/.test(aiSays)) {
        // 코드블럭이 포함된 경우
        // 코드 블럭을 기준으로 나누어 일반 블럭은 텍스트로, 코드블럭은 마크다운 블럭으로 만듬
        const blocks: Block[] | KnownBlock[] = aiSays
          .split(/\`\`\`/)
          .map((v, i) => {
            if (i % 2 === 0) {
              return Text(v);
            } else {
              return Section({ text: Markdown(v) });
            }
          });

        await say({
          blocks,
        });
      } else {
        await say(aiSays);
      }
    }
  });
};

export default {
  setup,
};
