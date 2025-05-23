import os
import re
import logging
from mkdocs.plugins import BasePlugin

class VTranscript(BasePlugin):
    def on_page_markdown(self, markdown, page, config, files):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger("mkdocs.plugins.vtranscript")
            self.logger.setLevel(logging.DEBUG)

        def process_srt(srt_content, video_title):
            blocks = re.split(r'\n\s*\n', srt_content.strip())
            all_text = []
            for block in blocks:
                lines = block.splitlines()
                if len(lines) >= 3 and '-->' in lines[1]:
                    text = " ".join(line.strip() for line in lines[2:] if line.strip())
                else:
                    text = " ".join(line.strip() for line in lines if line.strip())
                if text:
                    all_text.append(text)

            full_text = " ".join(all_text)
            sentences = re.split(r'(?<=[.!?])\s+', full_text)
            paragraphs = []

            if len(sentences) < 2:
                # Fallback: grupos de 50 palabras
                words = full_text.split()
                chunk_size = 50
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size]).strip()
                    if chunk:
                        paragraphs.append(f"<p>VIDEO: {video_title} - {chunk}</p>")
            else:
                # Agrupamos 3 oraciones por párrafo
                group_size = 3
                for i in range(0, len(sentences), group_size):
                    group = sentences[i:i+group_size]
                    paragraph = " ".join(group).strip()
                    if paragraph:
                        paragraphs.append(f"<p>VIDEO: {video_title} - {paragraph}</p>")

            return "".join(paragraphs)

        def replace_video(match):
            video_path = match.group(1)
            video_title = os.path.splitext(os.path.basename(video_path))[0]
            transcript_rel_path = os.path.splitext(video_path)[0] + '.srt'
            md_dir = os.path.dirname(page.file.src_path)
            transcript_full_path = os.path.join(config['docs_dir'], md_dir, transcript_rel_path)
            transcript_html = ""

            if os.path.exists(transcript_full_path):
                try:
                    with open(transcript_full_path, encoding='utf8') as f:
                        raw_text = f.read()
                    transcript_html = process_srt(raw_text, video_title)
                except Exception as e:
                    self.logger.error("Error reading SRT file %s: %s", transcript_full_path, e)
            else:
                self.logger.warning("No SRT file found for video: %s", video_title)

            hidden_div = f"<div class=\"sr-only\">\n{transcript_html}\n</div>"
            return match.group(0) + "\n" + hidden_div

        video_pattern = r'!\[type:video\]\((.*?)\)'
        return re.sub(video_pattern, replace_video, markdown)
