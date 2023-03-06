import type { Block, KnownBlock } from "@slack/types";
import type { ChatCompletionRequestMessage } from "openai";
import { Markdown, Section } from "../../blocks";
import openai from "../../utils/openai";
import { ChatSession } from "./session";

const BOT_CHARACTER: ChatCompletionRequestMessage = {
  role: "system",
  content: "Use Korean as possible. Try to be nice.",
};

/** 주어진 프롬프트에 대한 chatgpt 응답을 얻는다.
 * 세션이 주어진 경우 이전 대화내용을 문맥으로 삼으며, 프롬프트 질문과 응답을 세션에 추가한다.
 */
export async function chatCompletion(
  prompt: string,
  session?: ChatSession
): Promise<string> {
  let messages: ChatCompletionRequestMessage[] = [BOT_CHARACTER];

  if (session) {
    // 세션이 주어진 경우 이전 세션의 대화 내용을 가져옴
    messages.push.apply(messages, session.getHistory());

    // 프롬프트를 세션 이력에 추가
    session.addHistory(prompt, "user");
  }
  messages.push({ content: prompt, role: "user" });

  const result = await openai.createChatCompletion({
    model: "gpt-3.5-turbo",
    messages,
    max_tokens: 1024,
    temperature: 0.6,
    frequency_penalty: 0.4,
    user: session?.user,
  });

  const response = result.data.choices[0].message?.content!.trim()!;
  session?.addHistory(response, "assistant");
  return response;
}

/** 응답을 슬랙 BlockKit 으로 포메팅한다. */
export function formatResponse(response: string): Block[] | KnownBlock[] {
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
          const langaugeMatch = /^(#?\S+)/.exec(v);
          if (langaugeMatch) {
            langaugeMatch[1];
            v = v.replace(/^(#?\S+)/, "");
          }
          return Section({
            text: Markdown("```" + v + "```"),
          });
        }
      });
    return blocks;
  } else {
    return [Section({ text: Markdown(response) })];
  }
}
