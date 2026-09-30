import math
from pathlib import Path
from PIL import Image, ImageDraw
from core.ir import SceneSpec, Fragment
from render.typeset import load_font, fit_text_size
from render.scrim import solve_scrim_alpha, draw_gradient_scrim


def ease_out_cubic(p: float) -> float:
    """Cubic ease-out curve."""
    p = max(0.0, min(1.0, p))
    return 1.0 - (1.0 - p) ** 3


def render_frame(scene: SceneSpec, t: float, width: int = 1080, height: int = 1920) -> Image.Image:
    """Renders a single video frame at timestamp t as a transparent RGBA image."""
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # Smooth scene boundary transition ramps (enter and exit fade)
    enter_fade = min(1.0, t / 0.25) if t < 0.25 else 1.0
    exit_fade = min(1.0, (scene.duration_s - t) / 0.25) if t > scene.duration_s - 0.25 else 1.0
    scene_fade = max(0.0, min(1.0, enter_fade * exit_fade))

    # Optional motion offset during enter/exit for push/slide transitions
    trans_x_offset = 0
    if scene.transition in ("push", "slide"):
        if t < 0.25:
            trans_x_offset = int(40 * (1.0 - enter_fade))
        elif t > scene.duration_s - 0.25:
            trans_x_offset = int(-40 * (1.0 - exit_fade))

    # 1. Full Bleed Number Layout
    if scene.layout == "full_bleed_number":
        main_word = scene.fragments[0].words[0] if scene.fragments and scene.fragments[0].words else "0"
        num_font = load_font(int(height * 0.22))
        
        # Word reveal timing
        w_start = scene.word_times[0][1] if scene.word_times else 0.1
        progress = ease_out_cubic((t - w_start) / 0.11) if t >= w_start else 0.0
        
        alpha = int(255 * progress * scene_fade)
        y_offset = int(15 * (1.0 - progress))
        
        if alpha > 0:
            bbox = num_font.getbbox(main_word)
            w = bbox[2] - bbox[0]
            x = (width - w) // 2 + trans_x_offset
            y = int(height * 0.35) - y_offset
            
            # Scrim
            scrim = draw_gradient_scrim(width, height, (x - 20, y - 20, x + w + 20, y + 250), 0.5 * scene_fade)
            frame = Image.alpha_composite(frame, scrim)
            draw = ImageDraw.Draw(frame)
            
            # Accent color for big number
            draw.text((x, y), main_word, font=num_font, fill=(251, 191, 36, alpha))

        return frame

    # 2. Document Figure Layout (Embedded map, graph, diagram from document)
    if scene.layout == "document_figure":
        card_x1 = int(width * 0.08)
        card_x2 = int(width * 0.92)
        card_y1 = int(height * 0.16)
        card_y2 = int(height * 0.56)
        card_w = card_x2 - card_x1
        card_h = card_y2 - card_y1

        # Background scrim for visual contrast
        scrim = draw_gradient_scrim(width, height, (card_x1 - 10, card_y1 - 10, card_x2 + 10, card_y2 + 10), 0.7 * scene_fade)
        frame = Image.alpha_composite(frame, scrim)
        draw = ImageDraw.Draw(frame)

        # Render extracted document media image if available
        if scene.doc_image_path and Path(scene.doc_image_path).exists():
            try:
                doc_img = Image.open(scene.doc_image_path).convert("RGBA")
                doc_img.thumbnail((card_w, card_h), Image.Resampling.LANCZOS)
                
                if scene_fade < 1.0:
                    r, g, b, a = doc_img.split()
                    a = a.point(lambda p: int(p * scene_fade))
                    doc_img.putalpha(a)
                
                img_w, img_h = doc_img.size
                img_x = card_x1 + (card_w - img_w) // 2 + trans_x_offset
                img_y = card_y1 + (card_h - img_h) // 2
                
                # Gold accent border box around figure
                border_rect = [img_x - 4, img_y - 4, img_x + img_w + 4, img_y + img_h + 4]
                draw.rectangle(border_rect, outline=(251, 191, 36, int(220 * scene_fade)), width=3)
                
                frame.paste(doc_img, (img_x, img_y), doc_img)
                draw = ImageDraw.Draw(frame)
            except Exception as e:
                print(f"[render_frame] Error rendering document image {scene.doc_image_path}: {e}")

        # Render narration text in lower third container below figure
        box_y1 = int(height * 0.62)
        box_y2 = int(height * 0.90)
        box_x1 = int(width * 0.08)
        box_x2 = int(width * 0.92)

    # 3. Stat Callout Layout (High-Impact Numerical Badge Card)
    elif scene.layout == "stat_callout":
        import re
        full_text = " ".join([w for f in scene.fragments for w in f.words])
        stat_match = re.search(r"(\$|\b)[\d,]+(\.\d+)?\s*(percent|%|billion|million|k|M|B|x|\+)\b", full_text, re.IGNORECASE)
        stat_val = stat_match.group(0) if stat_match else (scene.fragments[0].words[0] if scene.fragments and scene.fragments[0].words else "78%")

        badge_y = int(height * 0.22)
        badge_font = load_font(int(height * 0.09))
        bbox = badge_font.getbbox(stat_val)
        bw = bbox[2] - bbox[0]
        bx = (width - bw) // 2 + trans_x_offset

        scrim = draw_gradient_scrim(width, height, (bx - 40, badge_y - 20, bx + bw + 40, badge_y + 150), 0.75 * scene_fade)
        frame = Image.alpha_composite(frame, scrim)
        draw = ImageDraw.Draw(frame)

        alpha = int(255 * scene_fade)
        if alpha > 0:
            # Draw Stat Pill Badge Box
            draw.rounded_rectangle((bx - 25, badge_y - 10, bx + bw + 25, badge_y + 130), radius=18, fill=(124, 58, 237, int(190 * scene_fade)), outline=(251, 191, 36, alpha), width=3)
            draw.text((bx, badge_y + 10), stat_val, font=badge_font, fill=(255, 255, 255, alpha))

        # Render accompanying fragments below stat card
        box_y1 = int(height * 0.52)
        box_y2 = int(height * 0.88)
        box_x1 = int(width * 0.08)
        box_x2 = int(width * 0.92)

    # 4. Standard Stacked / Lower Third / Split Left Layouts
    else:
        if scene.layout == "lower_third":
            box_y1 = int(height * 0.65)
            box_y2 = int(height * 0.90)
            box_x1 = int(width * 0.08)
            box_x2 = int(width * 0.92)
        elif scene.layout == "split_left":
            box_y1 = int(height * 0.30)
            box_y2 = int(height * 0.70)
            box_x1 = int(width * 0.08)
            box_x2 = int(width * 0.52)
        else:  # center_stack
            box_y1 = int(height * 0.35)
            box_y2 = int(height * 0.65)
            box_x1 = int(width * 0.08)
            box_x2 = int(width * 0.92)

    box_w = box_x2 - box_x1
    box_h = box_y2 - box_y1

    # Fit font size based on longest fragment
    longest_frag_text = max([" ".join(f.words) for f in scene.fragments], key=len, default="Sample")
    font_size = fit_text_size(longest_frag_text, max_width=int(box_w * 0.88), max_height=int(box_h / max(1, len(scene.fragments))), min_size=36, max_size=120)
    font = load_font(font_size)

    # Draw Scrim layer with smooth scene fade
    scrim = draw_gradient_scrim(width, height, (box_x1 - 30, box_y1 - 30, box_x2 + 30, box_y2 + 30), 0.6 * scene_fade)
    frame = Image.alpha_composite(frame, scrim)
    draw = ImageDraw.Draw(frame)

    # Calculate line positions
    line_height = int(font_size * 1.1)
    total_height = line_height * len(scene.fragments)
    start_y = box_y1 + (box_h - total_height) // 2

    word_idx = 0
    for frag_idx, frag in enumerate(scene.fragments):
        line_y = start_y + frag_idx * line_height
        
        # Calculate line total width to align
        line_words = frag.words
        line_boxes = [font.getbbox(w) for w in line_words]
        word_widths = [b[2] - b[0] for b in line_boxes]
        space_w = font.getbbox(" ")[2] - font.getbbox(" ")[0]
        total_line_w = sum(word_widths) + space_w * (len(line_words) - 1)

        if scene.layout == "split_left":
            line_x = box_x1
        else:
            line_x = box_x1 + (box_w - total_line_w) // 2

        curr_x = line_x + trans_x_offset
        for w_in_frag, word_str in enumerate(line_words):
            # Lookup word reveal animation progress
            w_start = scene.word_times[word_idx][1] if word_idx < len(scene.word_times) else 0.1 * (word_idx + 1)
            progress = ease_out_cubic((t - w_start) / 0.11) if t >= w_start else 0.0
            
            alpha = int(255 * progress * scene_fade)
            y_offset = int(8 * (1.0 - progress))

            if alpha > 0:
                is_emphasis = w_in_frag in frag.emphasis
                text_color = (251, 191, 36, alpha) if is_emphasis else (255, 255, 255, alpha)

                # Outline for legibility insurance
                draw.text((curr_x + 1, line_y - y_offset + 1), word_str, font=font, fill=(0, 0, 0, int(alpha * 0.4)))
                draw.text((curr_x, line_y - y_offset), word_str, font=font, fill=text_color)

            curr_x += word_widths[w_in_frag] + space_w
            word_idx += 1

    return frame
