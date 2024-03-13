from discord import Client, Message


class DiscordTransport(Client):
    async def on_message(self, message: Message):
        ...
