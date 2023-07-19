import "./ensure_env";
import { ChatCompletionRequestMessage, Configuration, OpenAIApi } from "openai";
import { EventEmitter } from "stream";
import { ChatSession } from "../plugins/chatgpt/session";

const cachedAPIClients = new Map<string, OpenAIApi>();

/** 주어진 API 키를 사용하여 OpenAI API 클라이언트를 생성합니다.
 * 이미 생성한 적이 있다면 캐시된 클라이언트를 재사용합니다.
 */
export function useOpenAI(apiKey: string): OpenAIApi {
  if (!apiKey.startsWith("sk-")) {
    throw new Error("API 키가 설정되지 않았거나 잘못된 키 입니다.");
  }
  if (!cachedAPIClients.has(apiKey)) {
    const configuration = new Configuration({ apiKey });
    const apiClient = new OpenAIApi(configuration);
    cachedAPIClients.set(apiKey, apiClient);
    return apiClient;
  }
  const cachedClient = cachedAPIClients.get(apiKey);
  if (!cachedClient) {
    throw new Error("API 클라이언트 생성중 문제가 발생했습니다.");
  }
  return cachedClient;
}

export async function chatCompletionStream(
  prompt: string,
  streamHandler: (message: string) => Promise<void>,
  session?: ChatSession
): Promise<EventEmitter> {
  const messages: ChatCompletionRequestMessage[] = [];

  if (session) {
    session.addHistory(prompt, "user");
    messages.push.apply(messages, session.getHistory());
  } else {
    // If no session is provided, just use the prompt as the first message
    messages.push({ role: "user", content: prompt });
  }

  const apiClient = useOpenAI(process.env.OPENAI_API_KEY ?? "");
  const resp = await apiClient.createChatCompletion(
    {
      model: process.env.OPENAI_MODEL ?? "gpt-3.5-turbo",
      messages,
      temperature: 0.7,
      n: 1,
      max_tokens:
        parseInt(process.env.OPENAI_MAX_TOKEN ?? "4037", 10) -
        (session?.promptTokens ?? 1024),
      frequency_penalty: 0.2,
      stream: true,
    },
    { responseType: "stream", headers: { accept: "text/event-stream" } }
  );

  const emitter = new EventEmitter();
  let fullMessage = "";
  let line = "";

  (resp.data as any as NodeJS.ReadableStream).on(
    "data",
    async (data: Buffer) => {
      const packets = data
        .toString()
        .split("\n")
        .filter((line) => line.trim() !== "");
      for (const packet of packets) {
        const message = packet.replace(/^data: /, "");
        if (message === "[DONE]") {
          continue; // Stream finished
        }
        try {
          const parsed = JSON.parse(message);
          const partialMessage = parsed.choices[0].delta.content ?? "";
          fullMessage += partialMessage;
          line += partialMessage;
          if (line.includes("\n")) {
            const lines = line.split("\n");

            line = lines.pop() ?? "";
            lines.forEach(async (line_) => {
              if (!line_.trim()) {
                // replace empty lines with a \n
                line_ = "\n";
              }
              await streamHandler(`${line_}\n`);
              emitter.emit("line", `${line_}\n`);
            });
          }
        } catch (error) {
          console.error("Could not JSON parse stream message", message, error);
        }
      }
    }
  );

  (resp.data as any as NodeJS.ReadableStream).on("end", () => {
    // if there is a line left, emit it
    if (line) {
      streamHandler(line);
      emitter.emit("line", line);
    }
    emitter.emit("end", fullMessage);
  });

  return emitter;
}

/**
 * OpenAI API 클라이언트를 생성합니다.
 */
export default useOpenAI(process.env.OPENAI_API_KEY ?? "");
