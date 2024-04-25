import tiktoken


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text."""
    encoder = tiktoken.encoding_for_model(model)
    tokens = encoder.encode(text)
    return len(tokens)
