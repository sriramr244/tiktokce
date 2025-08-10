import os


class Config:
    """
    Configuration class for the Social Content Engine.

    This class provides a flexible way to configure paths, API keys, and other settings
    for the Social Content Engine. Default values are provided, but users can override them
    via keyword arguments.

    Attributes:
        base_dir (str): The base directory for the project. Defaults to the current working directory.
        data_dir (str): The directory where data files are stored. Defaults to a 'data' folder within the base directory.
        document_path (str): The path to the document (PDF) file. Defaults to 'Document.pdf' in the data directory.
        video_path (str): The path to the background video file. Defaults to 'Video.mp4' in the data directory.
        output_video_path (str): The path where the output video will be saved. Defaults to 'output_video.mp4' in the data directory.
        audio_path (str): The path where the generated audio file will be saved. Defaults to 'output_audio.mp3' in the data directory.
        api_key (str): The OpenAI API key for content generation. Defaults to a placeholder string.
        cta_text (str): The default call-to-action text to be added to videos. Defaults to "Subscribe Now!".

    Methods:
        get_document_path(): Returns the document path.
        get_video_path(): Returns the video path.
        get_output_video_path(): Returns the output video path.
        get_audio_path(): Returns the audio path.
        get_api_key(): Returns the API key.
        get_cta_text(): Returns the call-to-action text.
        set_document_path(path): Sets a new document path.
        set_video_path(path): Sets a new video path.
        set_output_video_path(path): Sets a new output video path.
        set_audio_path(path): Sets a new audio path.
        set_api_key(api_key): Sets a new API key.
        set_cta_text(text): Sets a new call-to-action text.
    """

    def __init__(self, **kwargs):
        """
        Initializes the Config class with optional keyword arguments.

        Args:
            **kwargs: Arbitrary keyword arguments that can be used to override the default paths and settings.

            - base_dir (str): The base directory for the project.
            - data_dir (str): The directory where data files are stored.
            - document_path (str): The path to the document (PDF) file.
            - video_path (str): The path to the background video file.
            - output_video_path (str): The path where the output video will be saved.
            - audio_path (str): The path where the generated audio file will be saved.
            - api_key (str): The OpenAI API key for content generation.
            - cta_text (str): The default call-to-action text to be added to videos.

        Examples:
            >>> config = Config(document_path="/path/to/document.pdf", api_key="my_openai_api_key")
            >>> config = Config()  # Uses all default paths and settings
        """
        # Set base directory and data directory
        self.base_dir = kwargs.get("base_dir", os.getcwd())
        self.data_dir = kwargs.get("data_dir", os.path.join(self.base_dir, "data"))

        # Set paths, allowing overrides via kwargs
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

        # Set API key
        self.api_key = kwargs.get("api_key", "your_openai_api_key_here")

        # Call-to-action text
        self.cta_text = kwargs.get("cta_text", "Subscribe Now!")

    def get_document_path(self):
        return self.document_path

    def get_video_path(self):
        return self.video_path

    def get_output_video_path(self):
        return self.output_video_path

    def get_audio_path(self):
        return self.audio_path

    def get_openai_api_key(self):
        return self.api_key

    def get_cta_text(self):
        return self.cta_text

    # Setters
    def set_document_path(self, path):
        self.document_path = path

    def set_video_path(self, path):
        self.video_path = path

    def set_output_video_path(self, path):
        self.output_video_path = path

    def set_audio_path(self, path):
        self.audio_path = path

    def set_openai_api_key(self, api_key):
        self.api_key = api_key

    def set_cta_text(self, text):
        self.cta_text = text
