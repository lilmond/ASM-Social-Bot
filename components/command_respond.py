import discord

async def respond(interaction: discord.Interaction, color: int, title: str, description: str, ephemeral: bool = True, footer_text: str = None):
    message_embed = discord.Embed()
    message_embed.color = color
    message_embed.title = title
    message_embed.description = description
    message_embed.set_footer(text=footer_text)
    
    await interaction.response.send_message(embed=message_embed, ephemeral=ephemeral)
