import "./ensure_env";
import { Configuration, OpenAIApi } from "openai";

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

export default useOpenAI(process.env.OPENAI_API_KEY ?? "");
