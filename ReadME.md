# Picassimo Bot!

Picassimo Bot is a Discord bot built using the Python discord.py library. It leverages OpenAI's image generation API to create and manipulate images based on user prompts. 

## Features

* **Image Generation**: You can generate images by providing a textual prompt. The bot will interpret the prompt and generate an image accordingly.
* **Image Variation**: You can upload an image and the bot will generate variations of it.
* **Thread Management**: The bot can handle large numbers of users with its built-in thread management system.

## Setup

1. **Clone the Repository**: Clone this repository to your local machine.
2. **Install Dependencies**: Install necessary Python dependencies by running `pip install -r requirements.txt`.
3. **Setup Environment Variables**: Create a `.env` file in your project root and add the following environment variables:

   - `Key_OpenAI`: Your OpenAI API key.
   - `DISCORD_TOKEN`: Your Discord bot token.

4. **Invite the Bot**: Invite the bot to your Discord server.
5. **Run the Bot**: Run the bot using the command `python main.py`.

## Usage

To use Picassimo Bot, invite it to your Discord server and use the following commands:

* **!paint [size] [prompt]**: Generates an image based on your text prompt.
* **!upload [size]**: Generates variations of an uploaded image.

Size options include `256x256`, `512x512`, and `1024x1024`.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

Contribution
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

License
MIT
