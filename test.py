# entry point / test runner

from social_content_engine.main import SocialContentEngine
import os
from dotenv import load_dotenv

load_dotenv()

base_path = os.path.join(os.path.dirname(__file__), "data")
test_pdf_path = os.path.join(base_path, "Default_Document.pdf")
background_video_path = os.path.join(base_path, "Default_Video.mp4")

def run_one(mode: str, words_per_line: int = 5):
    """
    Run the pipeline once for a given subtitle mode.
    Modes: "manual", "wordcount", "asr"
    """
    out_path = os.path.join(base_path, f"final_video_with_cta_{mode}.mp4")

    # Create engine and set mode from OUTSIDE the build
    engine = SocialContentEngine(
        api_key=os.getenv("OPENAI_API_KEY"),
        video_path=background_video_path,
        output_video_file=out_path,
        # These args work if you updated SocialContentEngine to accept them
        subtitle_mode=mode,
        words_per_line=words_per_line,
    )

    try:
        final_video = engine.process_document(test_pdf_path)
        print(f"[{mode}] Final Video: {final_video}")
        assert final_video.endswith(".mp4"), f"[{mode}] Output is not an MP4"
        assert os.path.isfile(final_video), f"[{mode}] Final video file was not created"
    except ImportError as e:
        # If faster-whisper isn't installed and mode is ASR, skip cleanly
        if mode.lower() == "asr":
            print(f"[{mode}] Skipped (missing ASR dependency): {e}")
        else:
            raise

if __name__ == "__main__":
    # Run all three modes. "manual" will fall back to "wordcount"
    # if no manual segments were provided.
    run_one("asr", words_per_line=5)
