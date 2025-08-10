from typing import Optional, Union
import os
from social_content_engine.config.settings import Config
from social_content_engine.document_processing.pdf_processor import PDFProcessor
from social_content_engine.content_generation.ai_content_generator import (
    AIContentGenerator,
)
from social_content_engine.audio_conversion.text_to_speech import TextToSpeechConverter
from social_content_engine.video_creation.video_overlay import VideoOverlay
from social_content_engine.cta_integration.add_cta import CTAAdder
import logging


class SocialContentEngine:
    def __init__(
        self,
        api_key: str,
        config: Optional[Config] = None,
        video_path: Optional[str] = None,  # Updated this line
        output_video_file: Optional[str] = None,
        audio_file: Optional[str] = None,
        cta_text: Optional[str] = None,
    ):
        self.config = config or Config()
        self.api_key = api_key
        self.background_video_file = video_path or self.config.get_video_path()
        self.output_video_file = (
            output_video_file or self.config.get_output_video_path()
        )
        self.audio_file = audio_file or self.config.get_audio_path()
        self.cta_text = cta_text or self.config.get_cta_text()

        self.pdf_processor = PDFProcessor()
        self.content_generator = AIContentGenerator(api_key=self.api_key)
        self.tts_converter = None  # Initialize as None, will be set later
        self.video_overlay = VideoOverlay(self.background_video_file, self.audio_file)
        self.cta_adder = CTAAdder()

    def process_document(self, pdf_path: str):
        """
        Process the provided PDF document to generate video content.
        """
        # Step 1: Extract text from the PDF
        extracted_text = self.pdf_processor.extract_text(pdf_path)
        if not extracted_text:
            raise ValueError("No text extracted from the document.")

        # Step 2: Generate content for the video
        generated_content = self.content_generator.generate_content(extracted_text)

        # Step 3: Convert the generated content to speech
        self.tts_converter = TextToSpeechConverter(
            generated_content
        )  # Pass the text here
        enhanced_audio_path = self.tts_converter.convert_to_speech()

        self.video_overlay.update_audio_and_subtitles(
            enhanced_audio_path, subtitle_segments
        )
        self.video_overlay.create_final_video(self.output_video_file)

        # Step 5: Add CTA to the video
        final_video_path_with_cta = self.cta_adder.add_cta(
            self.output_video_file, self.cta_text
        )

        logging.info(f"Final video with CTA saved at {final_video_path_with_cta}")
        return final_video_path_with_cta

    def generate_subtitle_segments(self, text: str):
        """
        Generate subtitle segments based on the provided text.
        This is a simple segmentation approach; in practice, you may want to use NLP techniques.
        """
        lines = text.split("\n")
        subtitle_segments = []
        start_time = 0
        for line in lines:
            duration = (
                len(line.split()) // 2
            )  # Approximate duration based on word count
            subtitle_segments.append((start_time, start_time + duration, line))
            start_time += duration
        return subtitle_segments


# if __name__ == "__main__":
#     # Example usage
#     api_key = "your-openai-api-key"
#     pdf_path = "data/Default_Document.pdf"
#     video_path = "data/Default_Video.mp4"
#     output_video_path = "data/final_video_with_subtitles.mp4"
#     cta_text = "Subscribe to our channel!"

#     engine = SocialContentEngine(
#         api_key=api_key,
#         video_path=video_path,  # Use the correct argument name
#         output_video_file=output_video_path,
#     )
#     engine.process_document(pdf_path)
