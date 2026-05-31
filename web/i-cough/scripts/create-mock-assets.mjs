import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const outDir = join(process.cwd(), "public", "mock");
mkdirSync(outDir, { recursive: true });

function writeUInt16LE(buffer, value, offset) {
  buffer.writeUInt16LE(value, offset);
}

function writeUInt32LE(buffer, value, offset) {
  buffer.writeUInt32LE(value, offset);
}

function createWav(filePath, index) {
  const sampleRate = 16000;
  const durationSeconds = 2;
  const samples = sampleRate * durationSeconds;
  const dataSize = samples * 2;
  const buffer = Buffer.alloc(44 + dataSize);

  buffer.write("RIFF", 0);
  writeUInt32LE(buffer, 36 + dataSize, 4);
  buffer.write("WAVE", 8);
  buffer.write("fmt ", 12);
  writeUInt32LE(buffer, 16, 16);
  writeUInt16LE(buffer, 1, 20);
  writeUInt16LE(buffer, 1, 22);
  writeUInt32LE(buffer, sampleRate, 24);
  writeUInt32LE(buffer, sampleRate * 2, 28);
  writeUInt16LE(buffer, 2, 32);
  writeUInt16LE(buffer, 16, 34);
  buffer.write("data", 36);
  writeUInt32LE(buffer, dataSize, 40);

  for (let i = 0; i < samples; i++) {
    const t = i / sampleRate;
    const coughPulse =
      Math.exp(-Math.pow((t - 0.45) * 8, 2)) +
      0.7 * Math.exp(-Math.pow((t - 1.1) * 10, 2));
    const tone = Math.sin(2 * Math.PI * (180 + index * 23) * t);
    const noise = Math.sin(2 * Math.PI * (820 + index * 31) * t) * 0.35;
    const value = Math.max(-1, Math.min(1, (tone + noise) * coughPulse * 0.45));
    buffer.writeInt16LE(Math.round(value * 32767), 44 + i * 2);
  }

  writeFileSync(filePath, buffer);
}

function createSpectrogram(filePath, index) {
  const cols = 28;
  const rows = 14;
  const cellW = 14;
  const cellH = 10;
  const width = cols * cellW;
  const height = rows * cellH;
  const rects = [];

  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const wave = Math.sin((x + index) * 0.55) + Math.cos((y - index) * 0.7);
      const peak = Math.exp(-Math.pow((x - 9 - index * 0.4) / 4, 2));
      const value = Math.max(0, Math.min(1, 0.35 + wave * 0.18 + peak * (1 - y / rows)));
      const hue = 220 - value * 180;
      const light = 18 + value * 52;
      rects.push(
        `<rect x="${x * cellW}" y="${y * cellH}" width="${cellW + 1}" height="${cellH + 1}" fill="hsl(${hue.toFixed(
          0,
        )} 86% ${light.toFixed(0)}%)"/>`,
      );
    }
  }

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#07111f"/>
  ${rects.join("\n  ")}
</svg>
`;

  writeFileSync(filePath, svg, "utf8");
}

for (let i = 1; i <= 10; i++) {
  const num = String(i).padStart(2, "0");
  createWav(join(outDir, `audio-${num}.wav`), i);
  createSpectrogram(join(outDir, `spectrogram-${num}.svg`), i);
}

console.log("Created 10 mock audio files and 10 mock spectrogram images in public/mock");
