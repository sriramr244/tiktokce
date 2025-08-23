# social_content_engine/video_creation/video_overlay.py

import os
import uuid
import tempfile
import shutil
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont, ImageFilter


class VideoOverlay:
    def __init__(
        self,
        video_path,
        audio_path,
        subtitles=None,
        subtitle_mode: str = "manual",   # "manual" | "wordcount" | "asr"
        words_per_line: int = 5,

        # ---- proportional styling knobs ----
        banner_ratio: float = 0.06,      # subtitle box height as % of video height
        bottom_margin_ratio: float = 0.04,
        side_margin_ratio: float = 0.05,
        font_height_ratio: float = 0.36, # font size as % of banner height
        bg_opacity: int = 160,           # 0..255 (alpha for bg)
        stroke_ratio: float = 0.08,      # stroke width as % of font size
        shadow_px: int = 2,              # blur radius for bg soft edge

        # debugging
        keep_sub_images: bool = False,   # keep generated PNGs
    ):
        self.video_path = video_path
        self.audio_path = audio_path
        self.subtitles = subtitles or []          # list[(start, end, text)] if manual
        self.subtitle_mode = (subtitle_mode or "manual").lower()
        self.words_per_line = int(words_per_line)
        self.script_text = ""                     # used when mode=="wordcount"

        # temp assets tracking
        self._tmp_dir = None
        self._tmp_images = []

        # style knobs
        self.banner_ratio = float(banner_ratio)
        self.bottom_margin_ratio = float(bottom_margin_ratio)
        self.side_margin_ratio = float(side_margin_ratio)
        self.font_height_ratio = float(font_height_ratio)
        self.bg_opacity = int(bg_opacity)
        self.stroke_ratio = float(stroke_ratio)
        self.shadow_px = int(shadow_px)
        self.keep_sub_images = bool(keep_sub_images)

    # ------------ Configuration helpers ------------
    def set_script_text(self, text: str):
        self.script_text = text or ""

    def set_subtitle_mode(self, mode: str = "wordcount", words_per_line: int = None):
        self.subtitle_mode = (mode or "manual").lower()
        if words_per_line is not None:
            self.words_per_line = int(words_per_line)

    def update_audio_and_subtitles(self, audio_path, subtitles):
        self.audio_path = audio_path
        self.subtitles = subtitles or []
        self.subtitle_mode = "manual"

    # ------------ Main entry point ------------
    def create_final_video(self, output_path):
        video_clip = mp.VideoFileClip(self.video_path)
        vw, vh = video_clip.w, video_clip.h

        # Build subtitles if needed
        if not self.subtitles:
            if self.subtitle_mode == "wordcount":
                self.subtitles = self._build_subtitles_by_wordcount(
                    text=self.script_text,
                    audio_path=self.audio_path,
                    words_per_line=self.words_per_line,
                )
            elif self.subtitle_mode == "asr":
                self.subtitles = self._build_subtitles_by_asr(
                    audio_path=self.audio_path,
                    max_chars_per_line=38,
                )

        audio_clip = mp.AudioFileClip(self.audio_path).set_duration(video_clip.duration)
        subtitle_clips, final_video = [], None

        try:
            subtitle_clips = self._generate_dynamic_subtitles(vw, vh)
            final_video = mp.CompositeVideoClip([video_clip, *subtitle_clips]).set_audio(audio_clip)
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        finally:
            # Close clips
            for sc in subtitle_clips:
                try: sc.close()
                except: pass
            try: 
                if final_video: final_video.close()
            except: pass
            try: audio_clip.close()
            except: pass
            try: video_clip.close()
            except: pass

            # Cleanup temp PNGs
            if self._tmp_dir and os.path.isdir(self._tmp_dir) and not self.keep_sub_images:
                shutil.rmtree(self._tmp_dir, ignore_errors=True)
            self._tmp_dir, self._tmp_images = None, []

    # ------------ Subtitle builders ------------
    def _build_subtitles_by_wordcount(self, text: str, audio_path: str, words_per_line: int):
        try:
            duration = mp.AudioFileClip(audio_path).duration or 0.0
        except Exception:
            duration = 0.0
        if duration <= 0:
            return []

        words = [w for w in (text or "").strip().split() if w]
        if not words:
            return []

        t_per_word = duration / len(words)
        subs, i = [], 0
        while i < len(words):
            chunk = words[i:i + words_per_line]
            if not chunk: break
            start = i * t_per_word
            end = min(duration, (i + len(chunk)) * t_per_word)
            subs.append((float(start), float(end), " ".join(chunk)))
            i += words_per_line

        if subs and subs[-1][1] < duration:
            s, _, t = subs[-1]
            subs[-1] = (s, float(duration), t)
        return subs

    def _build_subtitles_by_asr(self, audio_path: str, max_chars_per_line: int = 42):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return []

        model = WhisperModel("base", device="cpu")
        segments, _ = model.transcribe(audio_path, word_timestamps=True)

        words = []
        for seg in segments:
            if getattr(seg, "words", None):
                for w in seg.words:
                    token = (w.word or "").strip()
                    if token:
                        words.append({"start": w.start, "end": w.end, "text": token})
            else:
                token = (seg.text or "").strip()
                if token:
                    words.append({"start": seg.start, "end": seg.end, "text": token})

        # Group into lines
        lines, cur, cur_start = [], [], None
        for w in words:
            trial = (" ".join(x["text"] for x in cur + [w])).strip()
            if cur_start is None: cur_start = w["start"]
            if len(trial) <= max_chars_per_line:
                cur.append(w)
            else:
                if cur:
                    lines.append((cur_start, cur[-1]["end"], " ".join(x["text"] for x in cur)))
                cur, cur_start = [w], w["start"]
        if cur:
            lines.append((cur_start, cur[-1]["end"], " ".join(x["text"] for x in cur)))

        out, last_end = [], 0.0
        for s, e, t in lines:
            s, e = float(max(0.0, s)), float(max(s + 0.01, e))
            if s < last_end: s = last_end
            out.append((s, e, t.strip()))
            last_end = e
        return out

    # ------------ Rendering ------------
    def _ensure_tmpdir(self):
        if not self._tmp_dir:
            self._tmp_dir = tempfile.mkdtemp(prefix="subs_")
        return self._tmp_dir

    def _generate_dynamic_subtitles(self, vw: int, vh: int):
        clips = []
        box_h = max(50, int(vh * self.banner_ratio))
        bottom_margin = max(8, int(vh * self.bottom_margin_ratio))
        y_pos = vh - box_h - bottom_margin
        tmpdir = self._ensure_tmpdir()

        for start_time, end_time, text in self.subtitles:
            if end_time <= start_time: continue
            image_path = os.path.join(tmpdir, f"subtitle_{uuid.uuid4().hex}.png")
            self._create_text_image(text, image_path, vw, box_h)
            self._tmp_images.append(image_path)
            clips.append(
                mp.ImageClip(image_path)
                  .set_duration(end_time - start_time)
                  .set_start(start_time)
                  .set_position(("center", y_pos))
            )
        return clips

    # ---------- Font & text utilities ----------
    def _find_unicode_font(self, font_size: int):
        candidates = [
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "Arial.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf",
        ]
        for path in candidates:
            try: return ImageFont.truetype(path, font_size)
            except Exception: continue
        return ImageFont.load_default()

    def _sanitize_text(self, s: str) -> str:
        repl = {"\u2013":"-","\u2014":"-","\u2018":"'",
                "\u2019":"'", "\u201c":'"', "\u201d":'"',
                "\u2026":"...", "\u00a0":" ", "\u200b":""}
        for k,v in repl.items(): s = s.replace(k,v)
        return s

    def _safe_textlength(self, draw, text, font):
        try: return draw.textlength(text, font=font)
        except UnicodeEncodeError:
            return draw.textlength(text.encode("ascii","ignore").decode("ascii"), font=font)

    # ---------- Draw subtitle banner ----------
    def _create_text_image(self, text, image_path, img_w, img_h):
        text = self._sanitize_text(text or "")
        image = Image.new("RGBA", (img_w, img_h), (0,0,0,0))

        # Background rounded rect
        bg = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
        bg_draw = ImageDraw.Draw(bg)
        radius = max(10, img_h // 6)
        bg_draw.rounded_rectangle([(0,0),(img_w,img_h)],
                                  radius=radius,
                                  fill=(0,0,0,self.bg_opacity))
        if self.shadow_px>0: bg = bg.filter(ImageFilter.GaussianBlur(self.shadow_px))

        # Font sizing
        font_size = max(18, int(img_h * self.font_height_ratio))
        font = self._find_unicode_font(font_size)

        # Text wrapping
        draw = ImageDraw.Draw(image)
        margin = max(16, int(img_w * self.side_margin_ratio))
        max_line_width = img_w - 2*margin
        words = text.split()
        lines, line = [], []
        for w in words:
            trial = " ".join(line+[w])
            if self._safe_textlength(draw, trial, font) <= max_line_width:
                line.append(w)
            else:
                if line: lines.append(" ".join(line))
                line = [w]
        if line: lines.append(" ".join(line))

        # Text layer with stroke
        text_layer = Image.new("RGBA", (img_w,img_h), (0,0,0,0))
        tdraw = ImageDraw.Draw(text_layer)
        line_step = int(font.size + max(6, font.size*0.2))
        total_h = len(lines)*line_step
        y = max(4,(img_h-total_h)//2)
        stroke_w = max(1,int(font.size*self.stroke_ratio))

        for ln in lines:
            tw = self._safe_textlength(draw, ln, font)
            x = max(4,(img_w-tw)//2)
            try:
                tdraw.text((x,y), ln, font=font, fill=(255,255,255,255),
                           stroke_width=stroke_w, stroke_fill=(0,0,0,255))
            except TypeError:
                tdraw.text((x,y), ln, font=font, fill=(255,255,255,255))
            y += line_step

        # Composite layers
        out = Image.alpha_composite(bg, text_layer)
        final = Image.alpha_composite(image, out)
        final.save(image_path)
