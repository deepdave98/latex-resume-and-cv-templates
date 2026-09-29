import { createHash } from "node:crypto";

// Tiny, deterministic PDF fixtures. They stay in memory; no private files or
// PDF-writing dependencies are needed to run the browser tests.
function literal(value) {
  return `(${value.replace(/[\\()]/g, "\\$&").replace(/\r/g, "\\r").replace(/\n/g, "\\n")})`;
}

function stream(bytes, dictionary = "") {
  const data = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes, "ascii");
  return Buffer.concat([
    Buffer.from(`<< /Length ${data.length} ${dictionary} >>\nstream\n`, "ascii"),
    data,
    Buffer.from("\nendstream", "ascii"),
  ]);
}

function writePdf(objects, trailer = "") {
  const parts = [Buffer.from("%PDF-1.7\n%fixture\n", "ascii")];
  const offsets = [0];
  let length = parts[0].length;
  for (let index = 1; index < objects.length; index += 1) {
    offsets.push(length);
    const value = objects[index];
    const part = Buffer.concat([
      Buffer.from(`${index} 0 obj\n`, "ascii"),
      Buffer.isBuffer(value) ? value : Buffer.from(value, "ascii"),
      Buffer.from("\nendobj\n", "ascii"),
    ]);
    parts.push(part);
    length += part.length;
  }
  parts.push(Buffer.from(
    `xref\n0 ${objects.length}\n0000000000 65535 f \n` +
    offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("") +
    `trailer\n<< /Size ${objects.length} /Root 1 0 R ${trailer} >>\nstartxref\n${length}\n%%EOF\n`,
    "ascii",
  ));
  return Buffer.concat(parts);
}

export function pdfFixture(pages = [{ text: "Resume fixture" }], { title = "Resume fixture", info = {}, xmp } = {}) {
  const objects = [null, "", "", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"];
  const add = (value) => objects.push(value) - 1;
  const pageIds = pages.map(() => add(""));
  const fields = [];
  for (let index = 0; index < pages.length; index += 1) {
    const page = pages[index];
    const pageId = pageIds[index];
    const annotations = [];
    let content = page.content ?? "";
    if (page.text) {
      content += `\nBT /F1 12 Tf 72 720 Td ${literal(page.text)} Tj ET`;
    }
    let imageResource = "";
    let extraFont = "";
    if (page.cjk) {
      const descriptor = add("<< /Type /FontDescriptor /FontName /HeiseiKakuGo-W5 /Flags 4 /FontBBox [-92 -250 1010 922] /ItalicAngle 0 /Ascent 880 /Descent -120 /CapHeight 700 /StemV 80 >>");
      const descendant = add(`<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HeiseiKakuGo-W5 /CIDSystemInfo << /Registry (Adobe) /Ordering (Japan1) /Supplement 5 >> /FontDescriptor ${descriptor} 0 R /DW 1000 >>`);
      const font = add(`<< /Type /Font /Subtype /Type0 /BaseFont /HeiseiKakuGo-W5 /Encoding /UniJIS-UCS2-H /DescendantFonts [${descendant} 0 R] >>`);
      extraFont = `/F2 ${font} 0 R`;
      content += "\nBT /F2 18 Tf 72 680 Td <65E5672C8A9E> Tj ET";
    }
    if (page.image) {
      const image = add(stream("000000ffffff000000ffffff>",
        "/Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /ASCIIHexDecode"));
      imageResource = `/XObject << /Image ${image} 0 R >>`;
      content += "\nq 160 0 0 160 72 560 cm /Image Do Q";
    }
    if (page.jpeg2000) {
      // A locally generated 2x2 black RGB image, encoded with OpenJPEG 2.5.4.
      // Unlike the raw image fixture this exercises the embedded WASM decoder.
      const data = Buffer.from("AAAADGpQICANCocKAAAAFGZ0eXBqcDIgAAAAAGpwMiAAAAAtanAyaAAAABZpaGRyAAAAAgAAAAIAAwcHAAAAAAAPY29scgEAAAAAABAAAACYanAyY/9P/1EALwAAAAAAAgAAAAIAAAAAAAAAAAAAAAIAAAACAAAAAAAAAAAAAwcBAQcBAQcBAf9SAAwAAAABAAEEBAAB/1wAB0BASEhQ/2QAJQABQ3JlYXRlZCBieSBPcGVuSlBFRyB2ZXJzaW9uIDIuNS40/5AACgAAAAAAHQAB/5PfgAgH34AIB9+ACAeAgID/2Q==", "base64");
      const image = add(stream(data, "/Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /JPXDecode"));
      imageResource = `/XObject << /Image ${image} 0 R >>`;
      content += "\nq 160 0 0 160 72 560 cm /Image Do Q";
    }
    for (const [linkIndex, link] of (page.links ?? []).entries()) {
      const y = 670 - linkIndex * 25;
      const rectangle = link.rect ?? [72, y, 300, y + 15];
      const destination = link.internal
        ? `/Dest [${pageIds[0]} 0 R /Fit]`
        : `/A << /S /URI /URI ${literal(link.url)} >>`;
      annotations.push(add(`<< /Type /Annot /Subtype /Link /Rect [${rectangle.join(" ")}] /Border [0 0 0] ${destination} >>`));
      content += `\nBT /F1 12 Tf ${rectangle[0] ?? 72} ${rectangle[1] ?? y} Td ${literal(link.label ?? "Portfolio")} Tj ET`;
    }
    if (page.formValue) {
      const appearance = add(stream(`BT /F1 12 Tf 4 8 Td ${literal(page.formValue)} Tj ET`,
        "/Type /XObject /Subtype /Form /BBox [0 0 250 30] /Resources << /Font << /F1 3 0 R >> >>"));
      const field = add(`<< /Type /Annot /Subtype /Widget /FT /Tx /T (Contact) /V ${literal(page.formValue)} /Rect [72 600 322 630] /P ${pageId} 0 R /F 4 /AP << /N ${appearance} 0 R >> >>`);
      annotations.push(field);
      fields.push(field);
    }
    const contentId = add(stream(content));
    objects[pageId] = `<< /Type /Page /Parent 2 0 R /MediaBox [${page.mediaBox ?? "0 0 612 792"}] /Rotate ${page.rotation ?? 0} /Resources << /Font << /F1 3 0 R ${extraFont} >> ${imageResource} >> /Contents ${contentId} 0 R /Annots [${annotations.map((id) => `${id} 0 R`).join(" ")}] >>`;
  }
  const xmpId = typeof xmp === 'string' ? add(stream(Buffer.from(xmp, 'utf8'), '/Type /Metadata /Subtype /XML')) : null;
  objects[1] = `<< /Type /Catalog /Pages 2 0 R${xmpId ? ` /Metadata ${xmpId} 0 R` : ''}${fields.length ? ` /AcroForm << /Fields [${fields.map((id) => `${id} 0 R`).join(" ")}] /DA (/F1 12 Tf 0 g) /DR << /Font << /F1 3 0 R >> >> >>` : ""} >>`;
  objects[2] = `<< /Type /Pages /Count ${pages.length} /Kids [${pageIds.map((id) => `${id} 0 R`).join(" ")}] >>`;
  const values = Object.entries({ Title: title, ...info }).filter(([, value]) => typeof value === 'string');
  const metadata = add(`<< ${values.map(([key, value]) => {
    const encoded = /^[\x00-\x7f]*$/.test(value) ? literal(value) : `<feff${Buffer.from(value, 'utf16le').swap16().toString('hex')}>`;
    return `/${key} ${encoded}`;
  }).join(' ')} >>`);
  return writePdf(objects, `/Info ${metadata} 0 R`);
}

const PASSWORD_PADDING = Buffer.from("28bf4e5e4e758a4164004e56fffa01082e2e00b6d0683e802f0ca9fe6453697a", "hex");
const md5 = (bytes) => createHash("md5").update(bytes).digest();

function paddedPassword(password) {
  return Buffer.concat([Buffer.from(password, "latin1"), PASSWORD_PADDING]).subarray(0, 32);
}

function rc4(key, input) {
  const state = Uint8Array.from({ length: 256 }, (_, index) => index);
  let j = 0;
  for (let i = 0; i < 256; i += 1) {
    j = (j + state[i] + key[i % key.length]) & 255;
    [state[i], state[j]] = [state[j], state[i]];
  }
  const result = Buffer.alloc(input.length);
  let i = 0;
  j = 0;
  for (let position = 0; position < input.length; position += 1) {
    i = (i + 1) & 255;
    j = (j + state[i]) & 255;
    [state[i], state[j]] = [state[j], state[i]];
    result[position] = input[position] ^ state[(state[i] + state[j]) & 255];
  }
  return result;
}

export function encryptedFixture(password = "review-test") {
  // Standard Security revision 2 is intentionally used only to exercise the
  // reader's password flow. This is not encryption advice or production code.
  const id = Buffer.from("00112233445566778899aabbccddeeff", "hex");
  const owner = rc4(md5(paddedPassword("fixture-owner")).subarray(0, 5), paddedPassword(password));
  const permissions = Buffer.alloc(4);
  permissions.writeInt32LE(-4);
  const key = md5(Buffer.concat([paddedPassword(password), owner, permissions, id])).subarray(0, 5);
  const user = rc4(key, PASSWORD_PADDING);
  const contentKey = md5(Buffer.concat([key, Buffer.from([5, 0, 0, 0, 0])])).subarray(0, 10);
  const objects = [null,
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
    stream(rc4(contentKey, Buffer.from("BT /F1 12 Tf 72 720 Td (Protected resume fixture) Tj ET", "ascii"))),
    `<< /Filter /Standard /V 1 /R 2 /Length 40 /O <${owner.toString("hex")}> /U <${user.toString("hex")}> /P -4 >>`,
  ];
  return writePdf(objects, `/Encrypt 6 0 R /ID [<${id.toString("hex")}> <${id.toString("hex")}>]`);
}

export function filePayload(buffer, name = "fixture.pdf", mimeType = "application/pdf") {
  return { name, mimeType, buffer };
}
