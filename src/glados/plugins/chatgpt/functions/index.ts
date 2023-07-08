import { JSONSchema4, JSONSchema4Object } from 'json-schema';
import { parse } from 'dotenv';
import { parseArgs } from 'node:util';
import type { ChatCompletionRequestMessage } from 'openai';

// export type FunctionResultMessage = {
//   role: 'function_call',
//   content: string,
// }

export type FunctionDefinition = {
  name: string;
  description: string;
  parameters: JSONSchema4Object;
}

export type DefinedFunctionInfo = {
  name: string;
  description: string;
}

// stores defined functions
const functions: Record<string, { definition: FunctionDefinition, handler: Function }> = {}

export function defineFunction(handler: Function, definition: FunctionDefinition): FunctionDefinition {
  functions[definition.name] = {
    definition,
    handler,
  }
  console.info('Function loaded:',  definition.name)
  return definition
}

export function getDefinedFunctions(): DefinedFunctionInfo[] {
  const ret = []
  for (const [name, { definition }] of Object.entries(functions)) {
    ret.push({
      name,
      description: definition.description,
    })
  }
  return ret
}

/**
 * returns a function description and function with given name
 * @param name the name of the function
 * @returns a tuple of function description and function
 */
export function getFunction(name: string): [FunctionDefinition, Function] | undefined {
  const fn = functions[name]
  if (!fn) return undefined
  return [fn.definition, fn.handler]
}

/**
 * invokes a function with given name and params
 * @param name the name of the function
 * @param params parameterized key-value pairs
 * @returns the formatted result for chat completion message
 */
export function invokeFunction(name: string, params: Record<string, any>): Promise<ChatCompletionRequestMessage> {
  const [def, fn] = getFunction(name) || []
  const result: Promise<any> | any = fn?.(params)

  if (!fn) return Promise.reject(new Error(`function not found: ${name}`));
  if (result instanceof Promise) {
    return result.then((content: string) => ({
      role: 'function',
      name,
      content,
    }))
  } else {
    return Promise.resolve({
      role: 'function',
      name,
      content: result,
    })
  }
}

export function splitArgs(str: string): string[] {
  const regex = /[^\s"]+|"([^"]*)"/gi;
  const args = [];
  let match;

  do {
    match = regex.exec(str);
    if (match !== null) {
      args.push(match[1] ? match[1] : match[0]);
    }
  } while (match !== null);

  return args;
}

/**
 * parses a function name from user message
 * ex)
 * "What is the weather in Seoul? -f weather" -> {name: 'weather', ... }
 * @param message 
 * @returns 
 */

export function parseFunction(message: string): FunctionDefinition[] {
  const pos = message.indexOf('-f')
  if (pos === -1) return []
  const args = splitArgs(message.slice(pos))
  const options = {
    fn: { short: 'f', type: 'string' as const, multiple: true }
  };
  const { values } = parseArgs({ args, options })

  const ret: FunctionDefinition[] = []
  for (const functionName of values['fn'] ?? []) {
    if (functions[functionName]) {
      ret.push(functions[functionName].definition)
    }
  }
  return ret
}