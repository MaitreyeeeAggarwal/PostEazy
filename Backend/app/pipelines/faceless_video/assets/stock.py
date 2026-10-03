import os
import subprocess
import urllib.parse
import requests
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

pipeline_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv()
if pipeline_env.exists():
    load_dotenv(dotenv_path=pipeline_env)


class StockAssetFetcher:
    def __init__(self, media_dir: str = "work/assets"):
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        
        # Load environment values
        p_vals = dotenv_values(pipeline_env) if pipeline_env.exists() else {}
        
        pex = os.getenv("PEXELS_API_KEY")
        if not pex or pex == "your_pexels_api_key_here":
            pex = p_vals.get("PEXELS_API_KEY") or pex
        self.pexels_key = pex

        pix = os.getenv("PIXABAY_API_KEY")
        if not pix or pix == "your_pixabay_api_key_here":
            pix = p_vals.get("PIXABAY_API_KEY") or pix
        self.pixabay_key = pix

        uns = os.getenv("UNSPLASH_ACCESS_KEY") or os.getenv("UNSPLASH_API_KEY")
        if not uns or uns == "your_unsplash_access_key_here":
            uns = p_vals.get("UNSPLASH_ACCESS_KEY") or p_vals.get("UNSPLASH_API_KEY") or uns
        self.unsplash_key = uns

    def fetch_background(self, query: str, scene_idx: int, duration_s: float, width: int = 1080, height: int = 1920, overwrite: bool = False) -> str:
        """Fetches stock background video/image (Pexels, Unsplash, Pixabay) or synthesizes procedural background video."""
        out_path = self.media_dir / f"bg_scene_{scene_idx:03d}.mp4"
        raw_pex_path = self.media_dir / f"raw_bg_pex_{scene_idx}.mp4"
        raw_uns_path = self.media_dir / f"raw_bg_uns_{scene_idx}.jpg"
        raw_pix_path = self.media_dir / f"raw_bg_pix_{scene_idx}.mp4"
        
        # If real stock asset already downloaded on disk, reuse it unless overwrite requested
        if out_path.exists() and not overwrite and (raw_pex_path.exists() or raw_uns_path.exists() or raw_pix_path.exists()):
            return str(out_path)

        headers = {"User-Agent": "doc2video/1.0 (Python/requests)"}
        
        # Search query fallbacks to ensure API matches
        search_terms = [query, query.split()[0] if query.split() else "abstract", "technology", "abstract"]

        # 1. Try Unsplash High-Quality Photo API
        if self.unsplash_key and self.unsplash_key != "your_unsplash_access_key_here":
            for term in search_terms:
                try:
                    clean_q = urllib.parse.quote(term)
                    u_headers = {
                        "User-Agent": "doc2video/1.0",
                        "Authorization": f"Client-ID {self.unsplash_key}"
                    }
                    resp = requests.get(
                        f"https://api.unsplash.com/search/photos?query={clean_q}&orientation=portrait&per_page=10",
                        headers=u_headers,
                        timeout=10
                    )
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])
                        if results:
                            img_url = (results[0].get("urls") or {}).get("regular") or (results[0].get("urls") or {}).get("full")
                            if img_url:
                                img_data = requests.get(img_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).content
                                with open(raw_uns_path, "wb") as img_f:
                                    img_f.write(img_data)

                                self._preprocess_image(str(raw_uns_path), str(out_path), duration_s, width, height)
                                print(f"[Stock API] Successfully fetched Unsplash photo background for scene {scene_idx} ('{term}')")
                                return str(out_path)
                except Exception as e:
                    print(f"[Stock API] Unsplash photo fetch error for '{term}': {e}.")

        # 2. Try Pexels Video API
        if self.pexels_key and self.pexels_key != "your_pexels_api_key_here":
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

        # 3. Try Pixabay Video API
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
        """Generates dynamic ambient motion gradient video using FFmpeg procedural filters."""
        palettes = [
            ("0x0f172a", "0x1e1b4b", "0x38bdf8"), # Slate & Indigo with Cyan glow
            ("0x090d16", "0x311042", "0xa855f7"), # Deep Void & Purple with Violet glow
            ("0x042f2e", "0x0f172a", "0x34d399"), # Dark Teal & Charcoal with Emerald glow
            ("0x1c1917", "0x451a03", "0xfbbf24")  # Dark Amber & Bronze with Gold glow
        ]
        c_bg, c_grad, c_glow = palettes[seed % len(palettes)]
        
        # FFmpeg filtergraph: color canvas + vignette + subtle noise/contrast
        vf_chain = (
            f"vignette=PI/4,eq=saturation=1.2:contrast=1.05"
        )
        
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={c_bg}:s={width}x{height}:d={duration_s}:r=30",
            "-vf", vf_chain,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", out_path
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as err:
            # Fallback simple color block if filter fails
            cmd_fallback = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={c_bg}:s={width}x{height}:d={duration_s}:r=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path
            ]
            subprocess.run(cmd_fallback, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
