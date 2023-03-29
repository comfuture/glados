import { WebClient } from "@slack/web-api";
import { SayFn } from "@slack/bolt";
import { Context, Markdown, Section, Text } from "../../blocks";
export { chatCompletionStream } from "../../utils/openai";

type PartialSlackContext = {
  say: SayFn;
  client: WebClient;
  channel: string;
  thread_ts?: string;
};

export function createCompletionHandler({
  say,
  client,
  channel,
  thread_ts,
}: PartialSlackContext): (text: string) => Promise<void> {
  let flag: "markdown" | "sourceblock" | "list" = "markdown";
  let lastTs = "";
  let lastMessage = "";
  return async (line: string) => {
    let oldFlag = "" + flag;

    // line = line.trim();
    if (line.trim() === "") {
      return;
    }

    // console.log(">>>", line);
    // return;

    // if message starts with ``` or ```{language}, toggle flag to sourceblock / markdown
    if (/^\`\`\`/.test(line)) {
      if (oldFlag === "sourceblock") {
        // if flag is already sourceblock, set flag to markdown
        lastMessage = "";
        flag = "markdown";
      } else {
        // if flag was not sourceblock, toggle flag to sourceblock
        lastMessage = "";
        flag = "sourceblock";
        // get source code language
        /^`{3}([\S]+)?\n/;
        const language = line.match(/^`{3}([\S]+)?\n/)?.[1];
        if (language !== undefined) {
          // if language is given, say it
          await say({
            text: `source: ${language}`,
            blocks: [Context([Text(language!)])],
            thread_ts,
          });
          line.replace(language, "");
        }
      }
      line = "";
    } else if (
      line.trim().startsWith("- ") ||
      line.trim().startsWith("* ") ||
      /\d+\. /.test(line.trim())
    ) {
      // if message presents markdown list, set flag to list
      if (oldFlag !== "list") {
        lastMessage = "";
      }
      flag = "list";
    } else if (oldFlag === "list") {
      // if message wat list but now it is not, set flag to markdown
      lastMessage = "";
      flag = "markdown";
    } else if (oldFlag === "sourceblock") {
      // if message was sourceblock and found nothing special, leave flag to sourceblock
      flag = "sourceblock";
    }

    switch (flag) {
      case "sourceblock":
        if (oldFlag !== "sourceblock") {
          // if flag is changed, send it
          lastMessage = line;
          // console.log("flag is changed to sourceblock", line);
          const r = await say({
            text: lastMessage,
            blocks: [
              Section({
                text: Markdown("```\n" + lastMessage ?? "..." + "\n```"),
              }),
            ],
            thread_ts,
          });
          lastTs = r.ts!;
        } else if (lastTs !== "") {
          // if flag is not changed, update it
          // console.log("flag is still sourceblock", line);
          lastMessage += line;
          await client?.chat.update({
            ts: lastTs,
            channel,
            text: lastMessage,
            blocks: [
              Section({ text: Markdown("```\n" + lastMessage + "\n```") }),
            ],
            thread_ts,
          });
        }
        break;
      case "list":
        if (oldFlag !== "list") {
          // if flag is changed, send it
          // console.log("flag is changed to list", line);
          lastMessage = line;
          const r = await say({
            text: lastMessage,
            blocks: [Section({ text: Markdown(line) })],
            thread_ts,
          });
          lastTs = r.ts!;
        } else if (lastTs !== "") {
          // if flag is not changed, update it
          // console.log("flag is still list");
          lastMessage += line;
          await client?.chat.update({
            ts: lastTs,
            channel,
            text: lastMessage,
            blocks: [Section({ text: Markdown(lastMessage) })],
            thread_ts,
          });
        }
        break;
      case "markdown":
        // console.log("flag is markdown", line);
        if (!line) {
          break;
        }
        if (line.startsWith("#")) {
          // replace leading # with *
          line = line.replace(/^#+ /, "*").replace(/\n$/, "*\n");
        }

        await say({
          text: line,
          blocks: [Section({ text: Markdown(line) })],
          thread_ts,
        });
        break;
    }
  };
}
