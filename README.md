# Social Content Engine

The Social Content Engine is a modular backend system designed to automate the creation of content tailored for various social media platforms. Initially focused on TikTok, the engine is flexible enough to be extended to other platforms.

## Features

- **Document Processing**: Extracts text from uploaded documents (e.g., PDFs).
- **Content Generation**: Uses AI models (like OpenAI GPT) to generate engaging content based on extracted text.
- **Audio Conversion**: Converts generated text to speech.
- **Video Creation**: Overlays generated content onto video clips and synchronizes captions with audio.
- **Call-to-Action Integration**: Adds a custom call-to-action at the end of each video.
- **API Interface**: Flask-based API to interact with the social content engine.
- **Streamlit Frontend**: A simple web interface for uploading documents, managing content, and generating videos.

## Folder Structure

```markdown
tiktokce/
├── src/
│   ├── social_content_engine/
│   │   ├── document_processing/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_processor.py
│   │   ├── content_generation/
│   │   │   ├── __init__.py
│   │   │   ├── ai_content_generator.py
│   │   ├── audio_conversion/
│   │   │   ├── __init__.py
│   │   │   ├── text_to_speech.py
│   │   ├── video_creation/
│   │   │   ├── __init__.py
│   │   │   ├── video_overlay.py
│   │   │   ├── video_library/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── manage_videos.py
│   │   ├── cta_integration/
│   │   │   ├── __init__.py
│   │   │   ├── add_cta.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
├── api/
│   ├── __init__.py
│   ├── routes.py
│   ├── main.py
├── frontend/
│   ├── app.py
├── tests/
│   ├── __init__.py
│   ├── test_document_processing.py
│   ├── test_content_generation.py
│   ├── test_audio_conversion.py
│   ├── test_video_creation.py
│   ├── test_api.py
├── data/
│   ├── sample_documents/
│   ├── video_library/
├── README.md
├── requirements.txt
├── .gitignore
├── setup.py
├── LICENSE
└── MANIFEST.in
```
## Getting Started
1. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
2. Run the API
    ```bash
    python api/main.py
4. Run the Streamlit Frontend
    ```bash
    streamlit run frontend/app.py
5. Access Swagger Documentation
Swagger UI for the API is available at http://localhost:5000/apidocs.