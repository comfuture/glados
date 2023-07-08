import "./ensure_env";
import { ChatCompletionRequestMessage, Configuration, OpenAIApi } from "openai";
import { EventEmitter } from "stream";
import { ChatSession } from "../plugins/chatgpt/session";
import { invokeFunction } from "../plugins/chatgpt/functions";

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
  message: ChatCompletionRequestMessage,
  streamHandler: (message: string) => Promise<void>,
  session?: ChatSession
): Promise<EventEmitter> {
  const messages: ChatCompletionRequestMessage[] = [];

  if (session) {
    session.addHistory(message);
    messages.push.apply(messages, session.getHistory());
  } else {
    // If no session is provided, just use the prompt as the first message
    messages.push(message);
  }

  const apiClient = useOpenAI(process.env.OPENAI_API_KEY ?? "");

  const emitter = new EventEmitter();
  let fullMessage = "";
  let line = "";
  let functionRequest = {
    name: '',
    arguments: '',
  }

  emitter.emit('reaction-add', 'hourglass')
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
      ...session?.getFunctionsParams(),
      stream: true,
    },
    { responseType: "stream", headers: { accept: "text/event-stream" } }
  );

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
          emitter.emit('reaction-remove', 'hourglass')
          emitter.emit('reaction-remove', 'jigsaw')
          continue; // Stream finished
        }
        try {
          const parsed = JSON.parse(message);
          const partialMessage = parsed.choices[0].delta.content ?? "";
          fullMessage += partialMessage;
          if (parsed.choices[0].delta.function_call) {
            if (parsed.choices[0].delta.function_call["name"]) {
              functionRequest.name = parsed.choices[0].delta.function_call["name"];
            }
            if (parsed.choices[0].delta.function_call["arguments"]) {
              functionRequest.arguments += parsed.choices[0].delta.function_call["arguments"];
            }
          }
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

          if (parsed["finish_reason"] === "stop") {
            emitter.emit('end', fullMessage)
          }

          // TODO: function-call 로 끝난 경우 여기서 추가 처리 필요
          if (parsed.choices[0]["finish_reason"] === "function_call") {
            emitter.emit('reaction-add', 'jigsaw')
            // invoke the function
            if (functionRequest.name !== null) {
              console.info(`>>> ${functionRequest.name}(${functionRequest.arguments})`);
              const callResultMessage = await invokeFunction(
                functionRequest.name,
                JSON.parse(functionRequest.arguments)
              )
              console.info(callResultMessage.content)
              line = ''
              await chatCompletionStream(
                callResultMessage,
                streamHandler,
                session
              ).catch(async (e) => {
                await streamHandler(`함수 실행중 오류가 발생했습니다. ${e}\n`);
                emitter.emit('reaction-add', 'x')
              })
            }
          }

        } catch (error) {
          console.error("Error", error);
          emitter.emit('reaction-add', 'x')
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
    if (fullMessage.length > 0) {
      session?.addHistory({role: 'assistant', content: fullMessage});
    }
    // emitter.emit("end", fullMessage);
  });

  return emitter;
}

export default useOpenAI(process.env.OPENAI_API_KEY ?? "");
