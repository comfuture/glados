import { Static, Type } from "@sinclair/typebox"
import { defineFunction } from ".";

const EchoParams = Type.Object({
  message: Type.String({description: "The message to echo"}),
})
type T = Static<typeof EchoParams>

function echo(args: T): string {
  return args.message
}

export default defineFunction(echo, {
  name: "echo",
  description: "Echoes the given message",
  parameters: EchoParams,
})
