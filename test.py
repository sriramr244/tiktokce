from social_content_engine.main import SocialContentEngine
import os
from dotenv import load_dotenv

load_dotenv()

base_path = os.path.join(os.path.dirname(__file__), "data")
test_pdf_path = os.path.join(base_path, "Default_Document.pdf")
background_video_path = os.path.join(base_path, "Default_Video.mp4")
output_video_path = os.path.join(base_path, "final_video_with_cta.mp4")

engine = SocialContentEngine(
    api_key=os.getenv("OPENAI_API_KEY"),
    video_path=background_video_path,
    output_video_file=output_video_path,
)


def run_tests():
    """
    Run all tests sequentially to validate the Social Content Engine's functionality.
    """
    extracted_text = engine.process_document(test_pdf_path)
    print(f"Extracted and Processed Text: {extracted_text}")
    assert len(extracted_text) > 0, "Failed to process document and generate text"
    final_video = engine.process_document(test_pdf_path)
    print(f"Final Video: {final_video}")
    assert final_video.endswith(
        ".mp4"
    ), "Failed to create final video with subtitles and CTA"


if __name__ == "__main__":
    run_tests()
