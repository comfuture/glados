import { ModalView } from "@slack/types";
import {
  ChatCompletionRequestMessage,
  CreateImageRequestSizeEnum,
} from "openai";
import openai from "../../utils/openai";
import { Modal, Section, TextInput } from "../../blocks";

/** 주어진 프롬프트에 대한 이미지를 그려줍니다. */
export async function drawImage(
  prompt: string,
  size: CreateImageRequestSizeEnum = "1024x1024"
): Promise<Buffer> {
  const response = await openai.createImage({
    prompt,
    size,
    n: 1,
    response_format: "b64_json",
  });

  if (response.data.data.length !== 0) {
    return Buffer.from(response.data.data[0].b64_json!, "base64");
  }
  throw new Error("Image generation failed");
}

/** 주어진 묘사에 대한 적절한 프롬프트를 작성해줍니다. */
export async function makePrompt(
  description: string,
  user?: string
): Promise<string> {
  const messages: ChatCompletionRequestMessage[] = [
    {
      role: "system",
      content:
        "You are a good painter. Provide imagination to describe the given prompt in detail.",
    },
  ];

  const messageContent = `Describe an image of the following description:\nDescription: ${description}\nWrite in English`;
  messages.push({ role: "user", content: messageContent });

  const response = await openai.createChatCompletion({
    model: "gpt-3.5-turbo",
    messages,
    max_tokens: 256,
    temperature: 0.8,
    frequency_penalty: 0.2,
    user,
  });

  return response.data.choices[0].message?.content!.trim()!;
}

export function ImagePromptDialog(): ModalView {
  return Modal({
    id: "imagine-modal",
    title: "그림 그리기",
    blocks: [
      TextInput({
        id: "image-prompt",
        label: "그림에 대한 설명",
      }),
    ],
    okLabel: "그리기",
  });
}
