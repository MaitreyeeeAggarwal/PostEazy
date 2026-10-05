import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import pptxgen from 'pptxgenjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const valueFor = (flag) => args[args.indexOf(flag) + 1];
const inputPath = valueFor('--input');
const outputPath = valueFor('--output');

if (!inputPath || !outputPath) {
  throw new Error('Usage: node render-presentation.mjs --input deck.json --output deck.pptx');
}

const deck = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const themes = {
  bold_tech: {bg: '0B1020', surface: '17213A', text: 'F8FAFC', muted: 'B5C2D7', accent: '38BDF8', stickers: ['code_brackets.png', 'cursor.png', 'brain.png']},
  minimalist_editorial: {bg: 'FCF8F3', surface: 'FFFFFF', text: '2E261F', muted: '6B625A', accent: 'B15B41', stickers: ['circle_ring.png', 'arrow_up_right.png', 'star_four_gold.png']},
  neon_cyberpunk: {bg: '090D16', surface: '151B30', text: 'FFFFFF', muted: 'C4B5FD', accent: 'EC4899', stickers: ['lightning_purple.png', 'rocket.png', 'sparkle_purple.png']},
  warm_corporate: {bg: 'FFF8F3', surface: 'F1E7DA', text: '283426', muted: '52684A', accent: '4A663E', stickers: ['chart_up.png', 'target.png', 'arrow_up_right.png']},
};
const theme = themes[deck.theme] || themes.bold_tech;
const stickerDir = path.join(here, '..', 'app', 'pipelines', 'assets', 'decorative', 'stickers');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'PostEazy';
pptx.subject = deck.subtitle || 'AI-generated presentation';
pptx.title = deck.title || 'PostEazy Presentation';
pptx.company = 'PostEazy';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Aptos Display',
  bodyFontFace: 'Aptos',
  lang: 'en-US',
};

function addText(slide, text, options) {
  slide.addText(String(text || ''), options);
}

for (const [position, spec] of (deck.slides || []).entries()) {
  const slide = pptx.addSlide();
  slide.background = {color: theme.bg};
  slide.addShape(pptx.ShapeType.rect, {x: 0, y: 0, w: 13.333, h: 0.13, line: {color: theme.accent}, fill: {color: theme.accent}});
  slide.addShape(pptx.ShapeType.roundRect, {x: 0.55, y: 0.42, w: 2.1, h: 0.38, rectRadius: 0.08, line: {color: theme.accent, transparency: 35}, fill: {color: theme.surface}});
  addText(slide, `${(deck.target_audience || 'General').toUpperCase()} BRIEFING`, {x: 0.72, y: 0.51, w: 1.8, h: 0.15, fontFace: 'Aptos', fontSize: 7.5, bold: true, color: theme.accent, charSpacing: 1.2, margin: 0});

  const stickerPositions = [
    {x: 11.72, y: 0.35, size: 0.9, rotate: position % 2 ? -8 : 8, transparency: 4},
    {x: 0.3, y: 3.85, size: 0.78, rotate: -12, transparency: 10},
    {x: 11.76, y: 3.95, size: 0.68, rotate: 14, transparency: 14},
  ];
  theme.stickers.forEach((sticker, stickerIndex) => {
    const stickerPath = path.join(stickerDir, sticker);
    const stickerPosition = stickerPositions[stickerIndex];
    if (stickerPosition && fs.existsSync(stickerPath)) {
      slide.addImage({path: stickerPath, w: stickerPosition.size, h: stickerPosition.size, ...stickerPosition});
    }
  });

  const isTitle = spec.layout === 'title_hero';
  addText(slide, spec.heading || `Slide ${position + 1}`, {
    x: isTitle ? 1.2 : 0.72, y: isTitle ? 1.55 : 1.08, w: isTitle ? 10.9 : 10.4, h: isTitle ? 1.1 : 0.95,
    fontFace: 'Aptos Display', fontSize: isTitle ? 34 : 28, bold: true, color: theme.text,
    align: isTitle ? 'center' : 'left', breakLine: false, margin: 0,
  });
  if (spec.subheading || deck.subtitle) {
    addText(slide, spec.subheading || deck.subtitle, {
      x: isTitle ? 1.7 : 0.74, y: isTitle ? 2.75 : 2.03, w: isTitle ? 9.9 : 10.2, h: 0.55,
      fontSize: isTitle ? 18 : 14, color: theme.muted, align: isTitle ? 'center' : 'left', margin: 0,
    });
  }

  if (spec.layout === 'big_stat' && spec.stat_number) {
    slide.addShape(pptx.ShapeType.roundRect, {x: 7.75, y: 3.1, w: 4.05, h: 2.25, rectRadius: 0.1, line: {color: theme.accent, transparency: 25}, fill: {color: theme.surface}});
    addText(slide, spec.stat_number, {x: 8.05, y: 3.5, w: 3.45, h: 0.72, fontSize: 42, bold: true, color: theme.accent, align: 'center', margin: 0});
    addText(slide, spec.stat_label || 'Key metric', {x: 8.05, y: 4.38, w: 3.45, h: 0.3, fontSize: 12, color: theme.muted, align: 'center', margin: 0});
  }

  const points = spec.body_points || [];
  if (spec.layout === 'feature_cards' && (spec.card_items || []).length) {
    const cards = spec.card_items.slice(0, 3);
    const cardWidth = 3.65;
    cards.forEach((card, index) => {
      const x = 0.72 + index * 4.08;
      slide.addShape(pptx.ShapeType.roundRect, {x, y: 3.15, w: cardWidth, h: 2.65, rectRadius: 0.1, line: {color: theme.accent, transparency: 42}, fill: {color: theme.surface}});
      addText(slide, card.title || 'Insight', {x: x + 0.26, y: 3.5, w: 3.1, h: 0.35, fontSize: 17, bold: true, color: theme.accent, margin: 0});
      addText(slide, card.desc || '', {x: x + 0.26, y: 4.02, w: 3.1, h: 1.05, fontSize: 11.5, color: theme.text, breakLine: false, margin: 0});
    });
  } else {
    const bulletText = points.map((point) => ({text: point, options: {bullet: {indent: 16}, hanging: 4, breakLine: true}}));
    if (bulletText.length) {
      slide.addText(bulletText, {x: isTitle ? 2.0 : 0.85, y: isTitle ? 3.9 : 3.15, w: isTitle ? 9.35 : 6.3, h: isTitle ? 1.65 : 2.75, fontSize: isTitle ? 16 : 17, color: theme.text, breakLine: false, paraSpaceAfterPt: 12, margin: 0});
    }
  }

  addText(slide, `${deck.title || 'PostEazy'}  •  ${position + 1} / ${(deck.slides || []).length}`, {x: 0.72, y: 7.02, w: 6.3, h: 0.18, fontSize: 7.5, color: theme.muted, margin: 0});
}

await pptx.writeFile({fileName: outputPath});
