import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont


import moviepy.editor as mp


class VideoOverlay:
    def __init__(self, video_path, audio_path, subtitles=[]):
        self.video_path = video_path
        self.audio_path = audio_path
        self.subtitles = subtitles

    def update_audio_and_subtitles(self, audio_path, subtitles):
        """
        Update the audio and subtitles for the video.
        """
        self.audio_path = audio_path
        self.subtitles = subtitles

    def create_final_video(self, output_path):
        video_clip = mp.VideoFileClip(self.video_path)
        audio_clip = mp.AudioFileClip(self.audio_path)

        # Generate and add dynamic subtitles using Pillow
        subtitle_clips = self.generate_dynamic_subtitles()
        final_video = mp.CompositeVideoClip([video_clip, *subtitle_clips]).set_audio(
            audio_clip
        )

        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

    def generate_dynamic_subtitles(self):
        subtitle_clips = []
        for start_time, end_time, text in self.subtitles:
            image_path = f"subtitle_{start_time}.png"
            self.create_text_image(text, image_path)
            subtitle_clip = (
                mp.ImageClip(image_path)
                .set_duration(end_time - start_time)
                .set_start(start_time)
            )
            subtitle_clips.append(subtitle_clip)
        return subtitle_clips

    def create_text_image(self, text, image_path, font_size=24):
        font = ImageFont.truetype("arial.ttf", font_size)
        image = Image.new("RGB", (800, 200), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        draw.text((10, 90), text, font=font, fill=(255, 255, 255))
        image.save(image_path)
