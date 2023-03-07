import {
  ChatCompletionRequestMessage,
  CreateImageRequestSizeEnum,
} from "openai";
import openai from "../../utils/openai";

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
    { role: "user", content: description },
  ];

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
