from glados.client.slack.formatter import format_response

markdown = """# Heading
## Subheading
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
1. Item 1
1. Item 2
1. Item 3

![image](https://example.com/image.png)

- Item 1
  * Item 1-1
  * Item 1-2
- Item 2
- Item 3

```python
def hello():
    print("hello world")
```

The quick brown fox jumps over the lazy dog.

[link](https://example.com)

https://example.com

"""


def test_slack_formatter():
    formatted = list(format_response(markdown))
    print(formatted)
    assert formatted == []
