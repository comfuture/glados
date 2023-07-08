import { describe, it, expect } from 'vitest'
import { splitArgs, parseFunction, getDefinedFunctions, invokeFunction } from '../src/glados/plugins/chatgpt/functions'
import diceFn from '../src/glados/plugins/chatgpt/functions/dice'
import echoFn from '../src/glados/plugins/chatgpt/functions/echo'

describe('functions', () => {
  it('should split args from string', () => {
    const args = splitArgs('roll the dice --fn dice')
    expect(args).toEqual(['roll', 'the', 'dice', '--fn', 'dice'])
  })
  it('should split args from quoted string', () => {
    const args = splitArgs('--fn "hello world"')
    expect(args).toEqual(['--fn', 'hello world'])
  })
  it('should find function definition from string', () => {
    const message = 'roll the dice -f dice'
    const fns = parseFunction(message)
    expect(fns).toEqual([diceFn])
  })
  it('should find multiple function definitions from string', () => {
    const message = 'roll the dice -f dice -f echo'
    const fns = parseFunction(message)
    expect(fns).toEqual([diceFn, echoFn])
  })
  it('shoud returns defined functions', () => {
    const fns = getDefinedFunctions()
    expect(fns).toEqual([
      {name: 'dice', description: diceFn.description},
      {name: 'echo', description: echoFn.description},
    ])
  })
  it('should invoke a function', () => {
    invokeFunction('echo', {message: 'hello'}).then((result) => {
      expect(result).toEqual({
        role: 'function',
        content: 'hello',
      })
    })
  })
})