import os
import subprocess
import urllib.parse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class StockAssetFetcher:
    def __init__(self, media_dir: str = "work/assets"):
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        load_dotenv()
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")

    def fetch_background(self, query: str, scene_idx: int, duration_s: float, width: int = 1080, height: int = 1920, overwrite: bool = False) -> str:
        """Fetches stock background video/image (Pexels, Pixabay) or synthesizes procedural background video."""
        out_path = self.media_dir / f"bg_scene_{scene_idx:03d}.mp4"
        raw_pex_path = self.media_dir / f"raw_bg_pex_{scene_idx}.mp4"
        raw_pix_path = self.media_dir / f"raw_bg_pix_{scene_idx}.mp4"
        
        # If real stock video already downloaded on disk, reuse it unless overwrite requested
        if out_path.exists() and not overwrite and (raw_pex_path.exists() or raw_pix_path.exists()):
            return str(out_path)

        headers = {"User-Agent": "doc2video/1.0 (Python/requests)"}
        
        # Search query fallbacks to ensure API matches
        search_terms = [query, query.split()[0] if query.split() else "abstract", "technology", "abstract"]

        # 1. Try Pexels Video API
        if self.pexels_key:
            headers["Authorization"] = self.pexels_key
            for term in search_terms:
                try:
                    clean_q = urllib.parse.quote(term)
                    resp = requests.get(
                        f"https://api.pexels.com/videos/search?query={clean_q}&per_page=10&orientation=portrait",
                        headers=headers,
                        timeout=10
                    )
                    if resp.status_code != 200 or not resp.json().get("videos"):
                        # Try without portrait constraint if 0 results
                        resp = requests.get(
                            f"https://api.pexels.com/videos/search?query={clean_q}&per_page=10",
                            headers=headers,
                            timeout=10
                        )

                    if resp.status_code == 200:
                        data = resp.json()
                        videos = data.get("videos", [])
                        if videos:
                            video_files = videos[0].get("video_files", [])
                            hd_files = [f for f in video_files if f.get("height", 0) >= 1280 or f.get("width", 0) >= 1080]
                            file_url = hd_files[0]["link"] if hd_files else video_files[0]["link"]
                            
                            v_data = requests.get(file_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).content
                            with open(raw_pex_path, "wb") as vf:
                                vf.write(v_data)

                            self._preprocess_video(str(raw_pex_path), str(out_path), duration_s, width, height)
                            print(f"[Stock API] Successfully fetched Pexels video background for scene {scene_idx} ('{term}')")
                            return str(out_path)
                except Exception as e:
                    print(f"[Stock API] Pexels video fetch error for '{term}': {e}.")

        # 2. Try Pixabay Video API
        if self.pixabay_key:
            for term in search_terms:
                try:
                    clean_q = urllib.parse.quote(term)
                    resp = requests.get(
                        f"https://pixabay.com/api/videos/?key={self.pixabay_key}&q={clean_q}&orientation=vertical",
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        hits = resp.json().get("hits", [])
                        if hits:
                            v_obj = hits[0].get("videos", {})
                            file_url = (v_obj.get("large") or v_obj.get("medium") or v_obj.get("small") or {}).get("url")
                            if file_url:
                                v_data = requests.get(file_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).content
                                with open(raw_pix_path, "wb") as vf:
                                    vf.write(v_data)

                                self._preprocess_video(str(raw_pix_path), str(out_path), duration_s, width, height)
                                print(f"[Stock API] Successfully fetched Pixabay video background for scene {scene_idx} ('{term}')")
                                return str(out_path)
                except Exception as e:
                    print(f"[Stock API] Pixabay video fetch error for '{term}': {e}.")

        # 3. Try Pixabay Photo/Image API fallback
        if self.pixabay_key:
            for term in search_terms:
                try:
                    clean_q = urllib.parse.quote(term)
                    resp = requests.get(
                        f"https://pixabay.com/api/?key={self.pixabay_key}&q={clean_q}&image_type=photo&orientation=vertical",
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        hits = resp.json().get("hits", [])
                        if hits:
                            img_url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
                            if img_url:
                                raw_img_path = self.media_dir / f"raw_bg_pix_img_{scene_idx}.jpg"
                                img_data = requests.get(img_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).content
                                with open(raw_img_path, "wb") as img_f:
                                    img_f.write(img_data)

                                self._preprocess_image(str(raw_img_path), str(out_path), duration_s, width, height)
                                print(f"[Stock API] Successfully fetched Pixabay photo background for scene {scene_idx} ('{term}')")
                                return str(out_path)
                except Exception as e:
                    print(f"[Stock API] Pixabay photo fetch error for '{term}': {e}.")

        # 4. Fallback: Generate procedural motion gradient video with FFmpeg
        print(f"[Stock Fallback] Generating procedural background for scene {scene_idx} ('{query}')")
        self._generate_procedural_bg(str(out_path), duration_s, width, height, scene_idx)
        return str(out_path)

    def _preprocess_video(self, in_path: str, out_path: str, duration_s: float, width: int, height: int):
        cmd = [
            "ffmpeg", "-y", "-ss", "0", "-i", in_path, "-t", str(duration_s),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},eq=saturation=0.75:brightness=-0.05",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-an", out_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _preprocess_image(self, in_path: str, out_path: str, duration_s: float, width: int, height: int):
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", in_path, "-t", str(duration_s),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},eq=saturation=0.75:brightness=-0.05",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-r", "30", "-pix_fmt", "yuv420p", "-an", out_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _generate_procedural_bg(self, out_path: str, duration_s: float, width: int, height: int, seed: int):
        colors = [
            ("0x0f172a", "0x1e1b4b"),
            ("0x111827", "0x064e3b"),
            ("0x18181b", "0x311042"),
            ("0x020617", "0x172554")
        ]
        c1, c2 = colors[seed % len(colors)]
        
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={c1}:s={width}x{height}:d={duration_s}:r=30",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast", out_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

