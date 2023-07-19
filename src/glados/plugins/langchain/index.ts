import {
  App,
  GenericMessageEvent,
  FileShareMessageEvent,
  SayArguments,
} from "@slack/bolt";
import { PineconeClient } from "@pinecone-database/pinecone";
import { definePlugin } from "../..";
import openai from "../../utils/openai";

const setup = async (app: App) => {
}


export default definePlugin({
  name: "langchain",
  setup,
});
