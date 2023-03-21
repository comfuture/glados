import type {
  ChatCompletionRequestMessage,
  ChatCompletionRequestMessageRoleEnum,
} from "openai";

import GPT3Tokenizer from "gpt3-tokenizer";
import { channelTypes } from "@slack/bolt/dist/types/events/message-events";

const tokenizer = new GPT3Tokenizer({ type: "gpt3" });

// XXX: chatgpt의 messages 토큰 계산법을 알지 못하지만 채팅 닉네임 형태의 prefix가 있을것이라고 가정
const USER_TOKEN_LEN = tokenizer.encode("<user>").bpe.length;
const BOT_TOKEN_LEN = tokenizer.encode("<assistant>").bpe.length;

/** ChatGPT의 메시지 이력을 저장하는 클래스 */
export class ChatSession {
  private ttl: number = 60 * 5 * 1000; // 5분
  private lastAccessTime: number = Date.now();
  private history: [number, ChatCompletionRequestMessage][];
  private _user?: string;
  private _channel?: string;
  private _type: channelTypes = "channel";

  constructor(type: channelTypes, user?: string, channel?: string) {
    this.history = [];
    this._user = user;
    this._channel = channel;
    this._type = type;
  }

  public get user(): string | undefined {
    return this._user;
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

    // 총 토큰수가 maxToken - 1000을 넘으면 히스토리를 앞에서부터 제거한다.
    // TODO: 제거하지 말고 요약해서 앞에 추가하면 더 좋음
    const maxTokens = +(process.env.OPENAI_MAX_TOKEN ?? 4096);
    const totalTokenSize = this.history.reduce((acc, [len]) => acc + len, 0);
    const tobeForgotten = totalTokenSize - maxTokens - 1000;
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

  /** 대화가 {ttl}이상 정체되어 있으면 종료되었다고 가정합니다.
   * 세션타잎이 channel이 아닌 경우에는 만료되지 않습니다.
   */
  public isRotten(): boolean {
    return (
      this._type === "channel" && Date.now() - this.lastAccessTime > this.ttl
    );
  }

  public isActive(): boolean {
    return Date.now() - this.lastAccessTime <= this.ttl;
  }
}

/** ChatGPT의 사용자별 ChatSession을 관리하는 클래스 */
export class SessionManager {
  private static sessions: Map<string, ChatSession> = new Map();

  public static getSession(
    type: channelTypes,
    user: string,
    channel?: string
  ): ChatSession {
    const key = `${user}|${channel}`;
    if (!SessionManager.sessions.has(key)) {
      const newSession = new ChatSession(type, user, channel);
      SessionManager.sessions.set(key, newSession);
      return newSession;
    }
    const session = SessionManager.sessions.get(key);
    if (!session || !session?.isActive()) {
      SessionManager.sessions.delete(key);
      return SessionManager.getSession(type, user, channel);
    }
    return session;
  }

  public static hasSession(user: string, channel?: string): boolean {
    const key = `${user}|${channel}`;
    return (
      SessionManager.sessions.has(key) && !this.sessions.get(key)?.isRotten()
    );
  }

  public static hasActiveSession(user: string, channel?: string): boolean {
    const key = `${user}|${channel}`;
    console.log("hasActiveSession", key, SessionManager.sessions);
    return (
      SessionManager.sessions.has(key) && !!this.sessions.get(key)?.isActive()
    );
  }

  public static clearSession(user: string, channel?: string) {
    const key = `${user}|${channel}`;
    SessionManager.sessions.delete(key);
  }
}
