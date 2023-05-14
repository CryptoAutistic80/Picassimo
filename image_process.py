from PIL import Image
import os
from datetime import datetime
import urllib.request

size_mapping = {
    1: "256x256",
    2: "512x512",
    3: "1024x1024",
}

def process_image(image_path):
    img = Image.open(image_path)

    # Crop the image to square if necessary
    if img.width != img.height:
        min_size = min(img.width, img.height)
        img = img.crop(
            (
                (img.width - min_size) // 2,
                (img.height - min_size) // 2,
                (img.width + min_size) // 2,
                (img.height + min_size) // 2
            )
        )

    # Convert the image to PNG if necessary
    if img.format != 'PNG':
        image_path = image_path.rsplit('.', 1)[0] + '.png'
        img.save(image_path)

    # Resize the image if necessary
    max_size = 1024
    if max(img.width, img.height) > max_size:
        if img.width > img.height:
            new_width = max_size
            new_height = int(max_size * img.height / img.width)
        else:
            new_height = max_size
            new_width = int(max_size * img.width / img.height)
        img = img.resize((new_width, new_height))
        img.save(image_path)

    # Reduce file size if necessary
    while os.path.getsize(image_path) > 4 * 1024 * 1024:
        img = Image.open(image_path)
        img.save(image_path, optimize=True, quality=50)
        
    return image_path


def stitch_images(response, variation=False):
    # Array to store image files
    image_files = []

    for idx, img in enumerate(response['data']):
        image_url = img['url']
        print(image_url)

        # Save the images in the New_Generations directory
        file_name = "New_Generations/image" + datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + f"_{'var_' if variation else ''}{idx}.png"
        urllib.request.urlretrieve(image_url, file_name)
        image_files.append(file_name)

    # Open images and resize if necessary
    imgs = [Image.open(i) for i in image_files]

    # Create a new image of size 2x2 of the input images
    collage_image = Image.new('RGB', (imgs[0].width * 2, imgs[0].height * 2))
    collage_image.paste(imgs[0], (0, 0))
    collage_image.paste(imgs[1], (imgs[0].width, 0))
    collage_image.paste(imgs[2], (0, imgs[0].height))
    collage_image.paste(imgs[3], (imgs[0].width, imgs[0].height))

    # Save the collage image
    file_to_send = "collage" + datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + f"_{'var' if variation else ''}.png"
    collage_image.save(file_to_send)

    return file_to_send, image_files
