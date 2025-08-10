from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from social_content_engine.utils.logger import setup_logger

# Set up a logger for the CTAAdder
logger = setup_logger(__name__)


class CTAAdder:
    """
    A class to add a call-to-action (CTA) at the end of a video.
    """

    @staticmethod
    def add(
        video_file: str, cta_text: str, output_file: str = "final_video_with_cta.mp4"
    ) -> str:
        """
        Add a call-to-action (CTA) to a video.

        Args:
            video_file (str): Path to the video file.
            cta_text (str): The CTA text to add to the video.
            output_file (str): The name of the output video file with the CTA. Defaults to 'final_video_with_cta.mp4'.

        Returns:
            str: The path to the saved video file with the CTA.
        """
        try:
            logger.info(f"Adding CTA to video: {video_file}")

            # Load the video file
            video = VideoFileClip(video_file)
            video_duration = video.duration

            # Create a text clip for the CTA
            cta_clip = TextClip(
                cta_text, fontsize=30, color="white", bg_color="black", size=video.size
            )
            cta_clip = cta_clip.set_pos("center").set_duration(
                5
            )  # Show CTA for 5 seconds

            # Position the CTA clip at the end of the video
            cta_clip = cta_clip.set_start(video_duration - 5)

            # Create the final composite video with the CTA
            final_clip = CompositeVideoClip([video, cta_clip])

            # Write the final video file with the CTA
            final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac")
            logger.info(f"Successfully added CTA and saved to {output_file}.")
            return output_file
        except Exception as e:
            logger.error(f"Error adding CTA to video: {e}")
            raise RuntimeError(f"Error adding CTA to video: {e}")


# Example usage:
# video_file = "final_video.mp4"
# cta_text = "Subscribe to our channel!"
# cta_adder = CTAAdder()
# final_video_with_cta = cta_adder.add(video_file, cta_text)
# print(f"Video with CTA saved to {final_video_with_cta}")
