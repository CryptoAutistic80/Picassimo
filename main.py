 # _____ _______     _______ _______ ____            _    _ _______ _____  _____ _______ _____ _____  
# / ____|  __ \ \   / /  __ \__   __/ __ \      /\  | |  | |__   __|_   _|/ ____|__   __|_   _/ ____| 
#| |    | |__) \ \_/ /| |__) | | | | |  | |    /  \ | |  | |  | |    | | | (___    | |    | || |      
#| |    |  _  / \   / |  ___/  | | | |  | |   / /\ \| |  | |  | |    | |  \___ \   | |    | || |      
#| |____| | \ \  | |  | |      | | | |__| |  / ____ \ |__| |  | |   _| |_ ____) |  | |   _| || |____  
# \_____|_|  \_\ |_|  |_|      |_|  \____/  /_/    \_\____/   |_|  |_____|_____/   |_|  |_____\_____| 
                                                                                                     
                                                                                                     
# ____  _            _        _           _         _____                       _                      
#|  _ \| |          | |      | |         (_)       |_   _|                     (_)                     
#| |_) | | ___   ___| | _____| |__   __ _ _ _ __     | |  _ __ ___   __ _  __ _ _ _ __   ___  ___ _ __ 
#|  _ <| |/ _ \ / __| |/ / __| '_ \ / _` | | '_ \    | | | '_ ` _ \ / _` |/ _` | | '_ \ / _ \/ _ \ '__|
#| |_) | | (_) | (__|   < (__| | | | (_| | | | | |  _| |_| | | | | | (_| | (_| | | | | |  __/  __/ |   
#|____/|_|\___/ \___|_|\_\___|_| |_|\__,_|_|_| |_| |_____|_| |_| |_|\__,_|\__, |_|_| |_|\___|\___|_|   
#                                                                          __/ |                       
#      James Walford 2023                                                                   |___/


import io
import os
import openai
import aiohttp
import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from maintenance import Maintenance
from image_process import process_image, stitch_images, size_mapping
from keep_alive import keep_alive

openai.api_key = os.environ.get("Key_OpenAI")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Create a Semaphore to limit the number of simultaneous API requests
api_semaphore = asyncio.Semaphore(30)

# Create the request queue for OpenAI API requests
request_queue = asyncio.Queue()

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        await bot.tree.sync()
        print("commands synced")
    except Exception as e:
        print(e)

    Maintenance()  # Start the maintenance task

    # Start the worker tasks to process items from the queue
    for _ in range(30):
        asyncio.create_task(worker())


# Worker that will process items from the queue
async def worker():
    while True:
        item = await request_queue.get()
        async with api_semaphore:
            # The "item" here is a tuple of (function, arguments)
            function, args = item
            await function(*args)
        request_queue.task_done()

class ImageButton(discord.ui.Button):
    def __init__(self, label, image_path):
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=1)
        self.image_path = image_path

    async def callback(self, interaction: discord.Interaction):
        request_queue.put_nowait((self.send_image, [interaction]))

    async def send_image(self, interaction):
        with open(self.image_path, 'rb') as f:
            picture = discord.File(f)
            await interaction.response.send_message(file=picture, ephemeral=True)
          

class VariationButton(discord.ui.Button):
    def __init__(self, label, image_path, size):
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=2)
        self.image_path = image_path
        self.size = size

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Generating variations. This may take a moment...", ephemeral=True)
        # add the task to the queue instead of directly calling the function
        request_queue.put_nowait((generate_variation, [interaction, self.image_path, self.size]))


class RegenerateButton(discord.ui.Button):
    def __init__(self, size, number, prompt):
        super().__init__(style=discord.ButtonStyle.primary, row=1, label="🔄")
        self.size = size
        self.prompt = prompt

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Add the `generate_image` function to the request queue
        request_queue.put_nowait((generate_image, [interaction, self.prompt, self.size]))


class RegenerateButton2(discord.ui.Button):
    def __init__(self, size, image_path):
        super().__init__(style=discord.ButtonStyle.primary, row=1, label="🔄")
        self.size = size
        self.image_path = image_path

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔄 Regenerating image variation. This may take a moment...", ephemeral=True)
        # add the task to the queue instead of directly calling the function
        request_queue.put_nowait((generate_variation, [interaction, self.image_path, self.size]))

class ProcessImageButton(discord.ui.Button):
    def __init__(self, size):
        super().__init__(style=discord.ButtonStyle.primary, label="Process Image")
        self.size = size

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("Processing your image. This may take a moment...", ephemeral=True)
        messages = [message async for message in interaction.channel.history(limit=20)]
        message_with_attachment = None
        for message in messages:
            if message.attachments:
                message_with_attachment = message
                break

        if message_with_attachment:
            image_url = message_with_attachment.attachments[0].url

            # Download the image file
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send('Could not download file...', ephemeral=True)
                    data = await resp.read()
                    with open('input_image.png', 'wb') as f:
                        f.write(data)

            # Process the image
            processed_image_path = process_image("input_image.png")

            await generate_variation(interaction, processed_image_path, self.size)
        else:
            await interaction.followup.send("No recent image found to process.", ephemeral=True)


class ImageView(discord.ui.View):
    def __init__(self, image_paths, size, number, prompt, include_regenerate=True, image_path=None):
        super().__init__()
        for idx, image_path in enumerate(image_paths):
            self.add_item(ImageButton(label=f'VI {idx+1}', image_path=image_path))
        if include_regenerate:
            if image_path:
                self.add_item(RegenerateButton2(size, image_path))
            else:
                self.add_item(RegenerateButton(size, number, prompt))
        for idx, image_path in enumerate(image_paths):
            self.add_item(VariationButton(label=f'GV {idx+1}', image_path=image_path, size=size))
          

async def generate_image(interaction, user_prompt, size):
    size_str = size_mapping[size]
    # Ensure that the New_Generations directory exists
    os.makedirs('New_Generations', exist_ok=True)
    response = openai.Image.create(
        prompt=user_prompt,
        n=4,  # Always generate 4 images
        size=size_str  # Use the string version of the size
    )

    file_to_send, image_files = stitch_images(response)

    with open(file_to_send, 'rb') as f:
        picture = discord.File(f)
        embed = discord.Embed(title="Your Picassimo!", description=f"**Prompt:** {user_prompt}\n\n**Size:** {size_mapping[size]}")
        embed.set_image(url=f"attachment://{file_to_send}")

    view = ImageView(image_files, size, 4, user_prompt, include_regenerate=True)
    await interaction.followup.send(embed=embed, file=picture, view=view,)
  
    os.remove(file_to_send)


async def generate_variation(interaction, image_path, size):
    size_str = size_mapping[size]
    os.makedirs('New_Generations', exist_ok=True)

    if not (image_path.startswith('http://') or image_path.startswith('https://')):
        with open(image_path, 'rb') as image_file:
            response = openai.Image.create_variation(
                image=image_file,
                n=4,
                size=size_str
            )
    else:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_path) as resp:
                if resp.status != 200:
                    return await interaction.followup.send('Could not download file...', ephemeral=True)
                data = await resp.read()
                byte_stream = io.BytesIO(data)
                byte_array = byte_stream.getvalue()
                response = openai.Image.create_variation(
                    image=byte_array,
                    n=4,
                    size=size_str
                )

    file_to_send, image_files = stitch_images(response, variation=True)

    with open(file_to_send, 'rb') as f:
        picture = discord.File(f)
        embed = discord.Embed(title="Your Picassimo Variations!", description=f"**Size:** {size_mapping[size]}")
        embed.set_image(url=f"attachment://{file_to_send}")

    view = ImageView(image_files, size, 4, "Variations", include_regenerate=True, image_path=image_path)
    await interaction.followup.send(embed=embed, file=picture, view=view)

    os.remove(file_to_send)


@bot.tree.command(name="paint", description="Generate an image based on your prompt")
@app_commands.describe(size='choose size')
@app_commands.choices(size=[
    discord.app_commands.Choice(name='256x256', value=1),
    discord.app_commands.Choice(name='512x512', value=2),
    discord.app_commands.Choice(name='1024x1024', value=3)
])
async def paint_slash_command(interaction: discord.Interaction, size: discord.app_commands.Choice[int], prompt: str):
    target_channel_name = '🎨-picassimo'

    if interaction.channel.name == target_channel_name:
        await interaction.response.defer()
        # add the task to the queue instead of directly calling the function
        request_queue.put_nowait((generate_image, [interaction, prompt, size.value]))
    else:
        await interaction.response.send_message(f"This command can only be used in the {target_channel_name} channel.", ephemeral=True)
      

@bot.tree.command(name="upload", description="Generate variations from an uploaded image")
@app_commands.describe(size='choose size')
@app_commands.choices(size=[
    discord.app_commands.Choice(name='256x256', value=1),
    discord.app_commands.Choice(name='512x512', value=2),
    discord.app_commands.Choice(name='1024x1024', value=3)
])
async def upload_slash_command(interaction: discord.Interaction, size: discord.app_commands.Choice[int]):
    view = discord.ui.View()
    view.add_item(ProcessImageButton(size.value))

    # Create an embed message
    embed = discord.Embed(
        title="Generate Image Variations",
        description="Please click the button to process the last uploaded image.",
        color=discord.Color.blue()  # You can choose another color if you prefer
    )

    # Send the embed message with the button view
    await interaction.response.send_message(embed=embed, view=view)


keep_alive()

discord_token = os.getenv('DISCORD_TOKEN')
bot.run(discord_token)


