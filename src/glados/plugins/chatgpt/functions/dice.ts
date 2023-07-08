import { Static, Type } from "@sinclair/typebox"
import { defineFunction } from ".";

const DiceParams = Type.Object({
  sides: Type.Number({
    default: 6,
    minimum: 1,
    maximum: 1000,
    description: "The number of sides of the dice"
  }),
})
type T = Static<typeof DiceParams>

function rollDice(args: T) {
  return '' + (Math.floor(Math.random() * args.sides) + 1);
}

export default defineFunction(rollDice, {
  name: "dice",
  description: "Rolls a dice",
  parameters: DiceParams,
})