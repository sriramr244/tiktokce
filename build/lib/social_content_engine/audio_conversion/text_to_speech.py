from moviepy.audio.fx.all import audio_fadein, audio_fadeout, volumex
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import os
from gtts import gTTS


class TextToSpeechConverter:
    def __init__(self, text):
        self.text = text

    def convert_to_speech(self, output_path="output_audio.mp3"):
        # Convert text to speech using gTTS
        tts = gTTS(self.text)
        tts.save(output_path)

        # Load the generated audio using moviepy
        audio_clip = mp.AudioFileClip(output_path)

        # Enhance the audio with fade in/out and volume adjustments
        enhanced_audio = self.enhance_audio(audio_clip)

        # Save the enhanced audio
        enhanced_output_path = os.path.join(
            os.path.dirname(output_path), "enhanced_" + os.path.basename(output_path)
        )
        enhanced_audio.write_audiofile(enhanced_output_path)

        return enhanced_output_path

    def enhance_audio(self, audio_clip):
        audio_clip = audio_fadein(audio_clip, 2)  # Fade in for 2 seconds
        audio_clip = audio_fadeout(audio_clip, 2)  # Fade out for 2 seconds
        audio_clip = volumex(audio_clip, 1.2)  # Increase volume by 20%
        return audio_clip

    def generate_text_image(self, text, image_path, font_size=24):
        # Create an image with text using Pillow
        font = ImageFont.truetype("arial.ttf", font_size)
        image = Image.new("RGB", (800, 200), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        draw.text((10, 90), text, font=font, fill=(255, 255, 255))
        image.save(image_path)


# Example Usage:
# converter = TextToSpeechConverter("Hello, world!")
# converter.generate_text_image("Hello, world!", "text_image.png")
