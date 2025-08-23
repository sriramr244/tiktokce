import os


class Config:
    """
    Configuration class for the Social Content Engine.
    """

    def __init__(self, **kwargs):
        # Base/data dirs
        self.base_dir = kwargs.get("base_dir", os.getcwd())
        self.data_dir = kwargs.get("data_dir", os.path.join(self.base_dir, "data"))

        # File paths
        self.document_path = kwargs.get(
            "document_path", os.path.join(self.data_dir, "Document.pdf")
        )
        self.video_path = kwargs.get(
            "video_path", os.path.join(self.data_dir, "Video.mp4")
        )
        self.output_video_path = kwargs.get(
            "output_video_path", os.path.join(self.data_dir, "output_video.mp4")
        )
        self.audio_path = kwargs.get(
            "audio_path", os.path.join(self.data_dir, "output_audio.mp3")
        )

        # Keys & CTA
        self.api_key = kwargs.get("api_key", os.getenv("OPENAI_API_KEY", ""))
        self.cta_text = kwargs.get("cta_text", os.getenv("CTA_TEXT", "Subscribe Now!"))

        # Subtitle settings (NEW: pick up from kwargs or .env)
        self.subtitle_mode = kwargs.get(
            "subtitle_mode", os.getenv("SUBTITLE_MODE", "wordcount")
        ).lower()
        self.words_per_line = int(
            kwargs.get("words_per_line", os.getenv("WORDS_PER_LINE", 5))
        )

    # --- Getters ---
    def get_document_path(self): return self.document_path
    def get_video_path(self): return self.video_path
    def get_output_video_path(self): return self.output_video_path
    def get_audio_path(self): return self.audio_path
    def get_openai_api_key(self): return self.api_key
    def get_cta_text(self): return self.cta_text
    def get_subtitle_mode(self): return self.subtitle_mode
    def get_words_per_line(self): return self.words_per_line

    # --- Setters ---
    def set_document_path(self, path): self.document_path = path
    def set_video_path(self, path): self.video_path = path
    def set_output_video_path(self, path): self.output_video_path = path
    def set_audio_path(self, path): self.audio_path = path
    def set_openai_api_key(self, api_key): self.api_key = api_key
    def set_cta_text(self, text): self.cta_text = text
    def set_subtitle_mode(self, mode): self.subtitle_mode = mode
    def set_words_per_line(self, n): self.words_per_line = int(n)
