import openai
from social_content_engine.utils.logger import setup_logger

# Set up a logger for the AIContentGenerator
logger = setup_logger(__name__)


class AIContentGenerator:
    """
    A class to generate content using OpenAI's API.
    """

    def __init__(self, api_key: str):
        """
        Initialize the AIContentGenerator with an API key.

        Args:
            api_key (str): The API key to authenticate with OpenAI.
        """
        self.api_key = api_key
        openai.api_key = self.api_key
        logger.info("Initialized AIContentGenerator with provided API key.")

    def generate_content(self, prompt: str) -> str:
        """
        Generate content based on a prompt using OpenAI's API.

        Args:
            prompt (str): The input text prompt.

        Returns:
            str: The generated content.
        """
        try:
            logger.info(f"Generating content with prompt: {prompt}")
            response = openai.chat.completions.create(
                model="gpt-4",  # or "gpt-3.5-turbo" or another model as needed
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,  # Adjust as needed
                temperature=0.7,  # Adjust for creativity vs. determinism
            )
            content = response.choices[0].message.content  # Corrected access method
            logger.info("Successfully generated content.")
            return content
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during content generation: {e}")
            raise RuntimeError(f"Unexpected error during content generation: {e}")
