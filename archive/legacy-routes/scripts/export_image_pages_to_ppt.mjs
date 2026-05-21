import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function main() {
  const imageDir = process.argv[2];
  const outputPptx = process.argv[3];

  if (!imageDir || !outputPptx) {
    throw new Error("Usage: node export_image_pages_to_ppt.mjs <imageDir> <outputPptx>");
  }

  const files = (await fs.readdir(imageDir))
    .filter((name) => /\.(png|jpg|jpeg|webp)$/i.test(name))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

  if (!files.length) {
    throw new Error(`No supported images found in ${imageDir}`);
  }

  const presentation = Presentation.create({
    slideSize: { width: 1280, height: 720 },
  });

  for (const file of files) {
    const slide = presentation.slides.add();
    slide.background.fill = "#FFFFFF";
    slide.images.add({
      blob: await readImageBlob(path.join(imageDir, file)),
      fit: "cover",
      alt: file,
      position: { left: 0, top: 0, width: 1280, height: 720 },
    });
  }

  await fs.mkdir(path.dirname(outputPptx), { recursive: true });
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPptx);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
