import os
import re
import textwrap

import aiofiles
import aiohttp
import numpy as np

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch

from config import YOUTUBE_IMG_URL
from SoloCloud import app


async def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def add_corners(im):
    bigsize = (im.size[0] * 3, im.size[1] * 3)
    mask = Image.new("L", bigsize, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(im.size, Image.LANCZOS)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)


async def get_thumb(videoid, user_id):
    if os.path.isfile(f"cache/{videoid}_{user_id}.png"):
        return f"cache/{videoid}_{user_id}.png"
    
    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        # Retrieve video details
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
                title = re.sub("\W+", " ", title)
                title = title.title()
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                views = result["viewCount"]["short"]
            except:
                views = "Unknown Views"
            try:
                channel = result["channel"]["name"]
            except:
                channel = "Unknown Channel"
        
        # Download thumbnail image
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        # Download and process profile picture
        try:
            profile_photos = await app.get_profile_photos(user_id)
            profile_photo_path = await app.download_media(profile_photos[0]['file_id'], file_name=f'{user_id}.jpg')
        except:
            default_profile_photo = await app.get_profile_photos(app.id)
            profile_photo_path = await app.download_media(default_profile_photo[0]['file_id'], file_name=f'{app.id}.jpg')

        profile_photo = Image.open(profile_photo_path)
        await add_corners(profile_photo)
        resized_profile_photo = await changeImageSize(107, 107, profile_photo)

        # Open other images
        youtube_thumb = Image.open(f"cache/thumb{videoid}.png")
        bg = Image.open(f"SoloCloud/assets/FUCK.png")

        # Resize and enhance images
        youtube_thumb_resized = await changeImageSize(1280, 720, youtube_thumb)
        youtube_thumb_resized = youtube_thumb_resized.convert("RGBA")
        bg_resized = await changeImageSize(1280, 720, bg)
        bg_resized = bg_resized.convert("RGBA")

        # Apply filters and composite images
        blurred_youtube_thumb = youtube_thumb_resized.filter(filter=ImageFilter.BoxBlur(30))
        enhanced_blurred_youtube_thumb = ImageEnhance.Brightness(blurred_youtube_thumb).enhance(0.6)
        final_image = Image.alpha_composite(enhanced_blurred_youtube_thumb, bg_resized)
        final_image.save(f"cache/temp{videoid}.png")

        # Crop and paste images
        x_center = youtube_thumb.width / 2
        y_center = youtube_thumb.height / 2
        x1 = x_center - 250
        y1 = y_center - 250
        x2 = x_center + 250
        y2 = y_center + 250
        cropped_youtube_thumb = youtube_thumb.crop((x1, y1, x2, y2))
        cropped_youtube_thumb.thumbnail((430, 430), Image.LANCZOS)
        cropped_youtube_thumb.save(f"cache/chop{videoid}.png")

        if not os.path.isfile(f"cache/cropped{videoid}.png"):
            im = Image.open(f"cache/chop{videoid}.png").convert("RGBA")
            await add_corners(im)
            im.save(f"cache/cropped{videoid}.png")

        cropped_profile_photo = Image.open(f"cache/cropped{videoid}.png")
        cropped_profile_photo.thumbnail((365, 365), Image.LANCZOS)
        width = int((1280 - 365) / 2)

        background = Image.open(f"cache/temp{videoid}.png")
        background.paste(cropped_profile_photo, (width + 2, 50), mask=cropped_profile_photo)
        background.paste(bg_resized, (0, 0), mask=bg_resized)

        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype("SoloCloud/assets/font2.ttf", 45)
        arial = ImageFont.truetype("SoloCloud/assets/font2.ttf", 30)
        name_font = ImageFont.truetype("SoloCloud/assets/font.ttf", 30)
        para = textwrap.wrap(title, width=30)

        draw.text((5, 5), f"ARI x MUSIC", fill="white", font=name_font)

        try:
            if para[0]:
                text_w, text_h = draw.textsize(f"{para[0]}", font=font)
                draw.text(
                    ((1280 - text_w) / 2, 440),
                    f"{para[0]}",
                    fill="white",
                    stroke_width=1,
                    stroke_fill="white",
                    font=font,
                )
            if para[1]:
                text_w, text_h = draw.textsize(f"{para[1]}", font=font)
                draw.text(
                    ((1280 - text_w) / 2, 490),
                    f"{para[1]}",
                    fill="white",
                    stroke_width=1,
                    stroke_fill="white",
                    font=font,
                )
        except:
            pass

        draw.text(
            (400, 580),
            f"{channel} | {views[:23]}",
            (255, 255, 255),
            font=arial,
        )
        draw.text(
            (250, 545),
            "00:00",
            (255, 255, 255),
            font=arial,
        )
        draw.text(
            (950, 545),
            f"{duration[:23]}",
            (255, 255, 255),
            font=arial,
        )

        try:
            os.remove(f"cache/thumb{videoid}.png")
            os.remove(profile_photo_path)
        except:
            pass

        # Save and return the thumbnail image path
        final_image_path = f"cache/{videoid}_{user_id}.png"
        background.save(final_image_path)
        return final_image_path

    except Exception as e:
        print(e)
        return YOUTUBE_IMG_URL
