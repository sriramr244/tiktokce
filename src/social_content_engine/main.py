from typing import Optional
import os
import logging

from social_content_engine.config.settings import Config
from social_content_engine.document_processing.pdf_processor import PDFProcessor
from social_content_engine.content_generation.ai_content_generator import AIContentGenerator
from social_content_engine.audio_conversion.text_to_speech import TextToSpeechConverter
from social_content_engine.video_creation.video_overlay import VideoOverlay
from social_content_engine.cta_integration.add_cta import CTAAdder


class SocialContentEngine:
    def __init__(
        self,
        api_key: str,
        config: Optional[Config] = None,
        video_path: Optional[str] = None,
        output_video_file: Optional[str] = None,
        audio_file: Optional[str] = None,
        cta_text: Optional[str] = None,
        # NEW: user-configurable subtitle options
        subtitle_mode: Optional[str] = None,     # "manual" | "wordcount" | "asr"
        words_per_line: Optional[int] = None,    # used for wordcount mode
    ):
        self.config = config or Config()
        self.api_key = api_key

        # Paths / text
        self.background_video_file = video_path or getattr(self.config, "get_video_path", lambda: None)() or self.config.get_video_path()
        self.output_video_file = output_video_file or getattr(self.config, "get_output_video_path", lambda: None)() or self.config.get_output_video_path()
        self.audio_file = audio_file or getattr(self.config, "get_audio_path", lambda: None)() or self.config.get_audio_path()
        self.cta_text = cta_text or getattr(self.config, "get_cta_text", lambda: None)() or self.config.get_cta_text()

        # Resolve subtitle prefs (priority: ctor args > Config > .env > defaults)
        cfg_mode = None
        if hasattr(self.config, "get_subtitle_mode"):
            try:
                cfg_mode = (self.config.get_subtitle_mode() or "").lower()
            except Exception:
                cfg_mode = None
        env_mode = (os.getenv("SUBTITLE_MODE") or "").lower()
        self.subtitle_mode = (subtitle_mode or cfg_mode or env_mode or "wordcount").lower()

        cfg_wpl = None
        if hasattr(self.config, "get_words_per_line"):
            try:
                cfg_wpl = int(self.config.get_words_per_line())
            except Exception:
                cfg_wpl = None
        env_wpl = os.getenv("WORDS_PER_LINE")
        try:
            env_wpl = int(env_wpl) if env_wpl is not None else None
        except ValueError:
            env_wpl = None
        self.words_per_line = words_per_line if words_per_line is not None else (cfg_wpl if cfg_wpl is not None else (env_wpl if env_wpl is not None else 5))

        # Core components
        self.pdf_processor = PDFProcessor()
        self.content_generator = AIContentGenerator(api_key=self.api_key)
        self.tts_converter = None
        self.video_overlay = VideoOverlay(self.background_video_file, self.audio_file)
        self.cta_adder = CTAAdder()

    def process_document(self, pdf_path: str):
        # 1) Extract
        extracted_text = self.pdf_processor.extract_text(pdf_path)
        if not extracted_text:
            raise ValueError("No text extracted from the document.")

        # 2) Generate script
        generated_content = self.content_generator.generate_content(extracted_text)

        # 3) TTS
        self.tts_converter = TextToSpeechConverter(generated_content)
        enhanced_audio_path = self.tts_converter.convert_to_speech()

        # 4) Subtitles according to user-selected mode
        #    - if 'manual' but no segments were set externally, fall back to 'wordcount'
        mode = (self.subtitle_mode or "wordcount").lower()
        if mode == "manual" and not self.video_overlay.subtitles:
            logging.warning("Subtitle mode set to 'manual' but no manual segments provided. Falling back to 'wordcount'.")
            mode = "wordcount"

        self.video_overlay.audio_path = enhanced_audio_path
        self.video_overlay.set_script_text(generated_content)   # used by wordcount; harmless for asr/manual
        self.video_overlay.set_subtitle_mode(mode=mode, words_per_line=self.words_per_line)
        self.video_overlay.create_final_video(self.output_video_file)

        # 5) CTA
        final_video_path_with_cta = self.cta_adder.add_cta(self.output_video_file, self.cta_text)
        logging.info(f"Final video with CTA saved at {final_video_path_with_cta}")
        return final_video_path_with_cta
