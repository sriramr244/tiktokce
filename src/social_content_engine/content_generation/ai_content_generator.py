import os
import json
import requests
from typing import Optional, Literal
from dotenv import load_dotenv
import openai
from social_content_engine.utils.logger import setup_logger

logger = setup_logger(__name__)
load_dotenv()  # load .env once at import

Provider = Literal["auto", "openai", "gemini"]

class AIContentGenerator:
    """
    Generate content using OpenAI or Google Gemini (REST), with selectable provider.

    Provider modes:
      - "openai": use OpenAI only
      - "gemini": use Gemini only
      - "auto": try OpenAI, on 429 insufficient_quota (or any failure) try Gemini
    """

    def __init__(
        self,
        api_key: Optional[str] = None,            # OpenAI key (optional; else read from env)
        provider: Provider = None,                # optional; else read from env AI_PROVIDER (defaults to "auto")
        openai_model: str = "gpt-4o-mini",
        gemini_model: str = "gemini-1.5-flash",
        timeout_s: int = 60,
    ):
        self.openai_api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        # provider precedence: arg > env > default
        self.provider: Provider = provider or os.getenv("AI_PROVIDER", "auto").lower()  # type: ignore
        if self.provider not in ("auto", "openai", "gemini"):
            logger.warning(f"Unknown AI_PROVIDER '{self.provider}', defaulting to 'auto'.")
            self.provider = "auto"

        self.openai_model = openai_model
        self.gemini_model = gemini_model
        self.timeout_s = timeout_s

        if self.openai_api_key:
            try:
                openai.api_key = self.openai_api_key
                logger.info("AIContentGenerator: OpenAI configured.")
            except "RuntimeError":
                logger.info("AIContentGenerator: OpenAI not configured.")
            
        else:
            logger.info("AIContentGenerator: OPENAI_API_KEY not set.")

        if self.gemini_api_key:
            logger.info("AIContentGenerator: Gemini key present.")
        else:
            logger.info("AIContentGenerator: GEMINI_API_KEY not set.")

        logger.info(f"AIContentGenerator provider mode: {self.provider}")

    # -------- Public API --------
    def generate_content(self, prompt: str) -> str:
        logger.info(f"Generating content (provider={self.provider}, prompt_len={len(prompt)}).")

        if self.provider == "openai":
            return self._generate_openai_only(prompt)
        elif self.provider == "gemini":
            return self._generate_gemini_only(prompt)
        else:  # "auto"
            return self._generate_auto(prompt)

    # -------- Provider strategies --------
    def _generate_openai_only(self, prompt: str) -> str:
        if not self.openai_api_key:
            raise RuntimeError("AI_PROVIDER=openai but OPENAI_API_KEY is not set.")
        return self._generate_openai(prompt)

    def _generate_gemini_only(self, prompt: str) -> str:
        if not self.gemini_api_key:
            raise RuntimeError("AI_PROVIDER=gemini but GEMINI_API_KEY is not set.")
        return self._generate_gemini(prompt)

    def _generate_auto(self, prompt: str) -> str:
        # Try OpenAI first if configured
        if self.openai_api_key:
            try:
                return self._generate_openai(prompt)
            except Exception as e:
                if self._is_insufficient_quota(e):
                    logger.warning("OpenAI quota hit (429 insufficient_quota). Falling back to Gemini.")
                else:
                    logger.error(f"OpenAI error (non-quota): {e}. Attempting Gemini fallback if available.")
                if self.gemini_api_key:
                    return self._generate_gemini(prompt)
                raise RuntimeError(f"OpenAI failed and no Gemini fallback configured. Original error: {e}")
        # If no OpenAI key, try Gemini
        if self.gemini_api_key:
            return self._generate_gemini(prompt)
        raise RuntimeError("Provider=auto but neither OPENAI_API_KEY nor GEMINI_API_KEY is set.")

    # -------- Providers --------
    def _generate_openai(self, prompt: str) -> str:
        logger.info(f"Using OpenAI model={self.openai_model}")
        resp = openai.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        content = resp.choices[0].message.content
        logger.info("OpenAI generation successful.")
        return content

    def _generate_gemini(self, prompt: str) -> str:
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set; cannot call Gemini.")
        logger.info(f"Using Gemini model={self.gemini_model} via REST")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [
                {"parts": [{"text": "You are a helpful assistant."}, {"text": prompt}]}
            ]
        }
        r = requests.post(url, json=payload, timeout=self.timeout_s)
        try:
            r.raise_for_status()
        except requests.HTTPError as http_err:
            # Try to extract structured error for clarity
            try:
                err_json = r.json()
            except Exception:
                err_json = {"error": str(http_err), "status": r.status_code, "text": r.text[:300]}
            logger.error(f"Gemini HTTP error: {err_json}")
            raise RuntimeError(f"Gemini HTTP error: {err_json}")

        data = r.json()
        text = (
            data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
        )
        if not text:
            raise RuntimeError(f"Gemini returned no text. Raw: {json.dumps(data)[:500]}")
        logger.info("Gemini generation successful.")
        return text

    # -------- Helpers --------
    def _is_insufficient_quota(self, exc: Exception) -> bool:
        """
        Detect OpenAI 429 insufficient_quota across different client versions.
        """
        s = str(exc)
        if "insufficient_quota" in s:
            return True
        if "Error code: 429" in s and "insufficient_quota" in s:
            return True
        # Attempt to parse embedded JSON error
        try:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1:
                obj = json.loads(s[start:end+1])
                code = obj.get("error", {}).get("code")
                if code == "insufficient_quota":
                    return True
        except Exception:
            pass
        return False
