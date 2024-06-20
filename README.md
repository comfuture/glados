# GLaDOS

a Chat interface for independent environments. It supports only Slack for now.
but it can be extended to other platforms like Discord, Telegram, web, etc.

## Features

- [x] Function call
- [x] Code interpreter
- [x] File search

## Installation

Create a chatbot in slack and get the token.

`glados/client/slack/manifest.json` is a configuration for Slack apps. With a
manifest, you can create an app with a pre-defined configuration, or adjust the
configuration of an existing app.

Prepare a mongo database and get the connection string. You can make it free
using MongoDB Atlas.

Prepare a cloudflare account and get the API keys. GLaDOS uses cloudflare to
store and serve the files.

Then create a `.env` file in the root directory from dist template and fill the
values.

```sh
cp .env.dist .env
```

### Running locally

Run the following command to start the bot.

```sh
python main.py --client slack
```

For running the bot in socket mode, you should enable the socket mode in the bot
settings.

## Deployment

Latest version of GLaDOS is available on Github container registry
https://ghcr.io/comfuture/glados:latest .

### Using Docker

You can pull the image using the following command.

```sh
docker --context remote pull ghcr.io/comfuture/glados:latest
```

Or run directly using docker compose with the following command.

```sh
docker --context remote compose up -d --force-recreate
```

Before running the docker compose, you should ensure all the ENV variables are
set.

### Manual

Pull the latest code from the repository and run the following command.

```sh
python main.py --client slack
```
