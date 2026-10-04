import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia} from '@remotion/renderer';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const valueFor = (flag) => args[args.indexOf(flag) + 1];
const source = valueFor('--source');
const output = valueFor('--output');
const title = valueFor('--title') || 'PostEazy';
const duration = Number(valueFor('--duration'));
if (!source || !output || !Number.isFinite(duration) || duration <= 0) throw new Error('Usage: node render-video.mjs --source input.mp4 --output output.mp4 --title title --duration seconds');

const serveUrl = await bundle({entryPoint: path.join(here, 'remotion', 'src', 'index.jsx')});
await renderMedia({
  serveUrl,
  codec: 'h264',
  outputLocation: output,
  composition: {id: 'creative-video', width: 1080, height: 1920, fps: 30, durationInFrames: Math.max(1, Math.ceil(duration * 30))},
  inputProps: {videoPath: source, title},
});
