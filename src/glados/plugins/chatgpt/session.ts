import type {
  ChatCompletionRequestMessage,
  ChatCompletionRequestMessageRoleEnum,
} from "openai";

import GPT3Tokenizer from "gpt3-tokenizer";

const tokenizer = new GPT3Tokenizer({ type: "gpt3" });

// XXX: chatgpt의 messages 토큰 계산법을 알지 못하지만 채팅 닉네임 형태의 prefix가 있을것이라고 가정
const USER_TOKEN_LEN = tokenizer.encode("<user>").bpe.length;
const BOT_TOKEN_LEN = tokenizer.encode("<assistant>").bpe.length;

/** ChatGPT의 메시지 이력을 저장하는 클래스 */
export class ChatSession {
  private ttl: number = 120 * 1000;
  private lastAccessTime: number = Date.now();
  private history: [number, ChatCompletionRequestMessage][];

  constructor() {
    this.history = [];
  }

  /** 히스토리를 가져온다 */
  public getHistory(): ChatCompletionRequestMessage[] {
    return this.history.map(([, message]) => message);
  }

  /** 히스토리를 추가한다. 히스토리가 너무 긴 경우 앞에서부터 서서히 잊는다.
   * @returns 현재 히스토리의 총 토큰수
   */
  public addHistory(
    content: string,
    role: ChatCompletionRequestMessageRoleEnum = "user"
  ): number {
    const { bpe } = tokenizer.encode(content);
    const tokenSize =
      bpe.length + (role === "user" ? USER_TOKEN_LEN : BOT_TOKEN_LEN);

    this.history.push([tokenSize, { role, content }]);

    // 총 토큰수가 3072를 넘으면 히스토리를 앞에서부터 제거한다.
    // TODO: 제거하지 말고 요약해서 앞에 추가하면 더 좋음
    const totalTokenSize = this.history.reduce((acc, [len]) => acc + len, 0);
    const tobeForgotten = totalTokenSize - 3072;
    if (tobeForgotten > 0) {
      let forgotten = 0;
      while (forgotten < tobeForgotten) {
        const [len] = this.history.shift()!;
        forgotten += len;
      }
    }
    this.lastAccessTime = Date.now();
    return totalTokenSize - Math.min(0, tobeForgotten);
  }

  public clearHistory() {
    this.history = [];
  }

  /** 대화가 {ttl}이상 정체되어 있으면 종료되었다고 가정합니다 */
  public isRotten(): boolean {
    return Date.now() - this.lastAccessTime > this.ttl;
  }
}

/** ChatGPT의 사용자별 ChatSession을 관리하는 클래스 */
export class SessionManager {
  private static sessions: Map<string, ChatSession> = new Map();

  public static getSession(user: string): ChatSession {
    if (!this.sessions.has(user)) {
      const newSession = new ChatSession();
      SessionManager.sessions.set(user, newSession);
      return newSession;
    }
    const session = this.sessions.get(user);
    if (!session || session?.isRotten()) {
      SessionManager.sessions.delete(user);
      return SessionManager.getSession(user);
    }
    return session;
  }

  public static clearSession(user: string) {
    this.sessions.delete(user);
  }
}
