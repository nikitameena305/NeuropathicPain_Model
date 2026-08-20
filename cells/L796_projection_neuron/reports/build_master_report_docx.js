// Converts L796_MASTER_REPORT.md into L796_MASTER_REPORT.docx
// Usage:
//   npm install docx
//   node build_master_report_docx.js

const fs = require("fs");
const path = require("path");
const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  ShadingType,
} = require("docx");

const SRC = path.join(__dirname, "L796_MASTER_REPORT.md");
const OUT = path.join(__dirname, "L796_MASTER_REPORT.docx");

const md = fs.readFileSync(SRC, "utf-8");
const lines = md.split(/\r?\n/);

// ---- inline formatting: **bold**, `code` ----
function parseInline(text) {
  const runs = [];
  const re = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      runs.push(new TextRun(text.slice(last, m.index)));
    }
    if (m[2] !== undefined) {
      runs.push(new TextRun({ text: m[2], bold: true }));
    } else if (m[3] !== undefined) {
      runs.push(new TextRun({ text: m[3], font: "Consolas", shading: { type: ShadingType.CLEAR, fill: "EEEEEE" } }));
    }
    last = re.lastIndex;
  }
  if (last < text.length) {
    runs.push(new TextRun(text.slice(last)));
  }
  if (runs.length === 0) {
    runs.push(new TextRun(text));
  }
  return runs;
}

function cellBorders() {
  const b = { style: BorderStyle.SINGLE, size: 2, color: "999999" };
  return { top: b, bottom: b, left: b, right: b };
}

function makeTable(headerCells, bodyRows) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: headerCells.map(
      (h) =>
        new TableCell({
          borders: cellBorders(),
          shading: { type: ShadingType.CLEAR, fill: "DDEBF7" },
          children: [new Paragraph({ children: parseInline(h).map((r) => { r.bold = true; return r; }) })],
        })
    ),
  });

  const rows = bodyRows.map(
    (row) =>
      new TableRow({
        children: row.map(
          (cellText) =>
            new TableCell({
              borders: cellBorders(),
              children: [new Paragraph({ children: parseInline(cellText) })],
            })
        ),
      })
  );

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [headerRow, ...rows],
  });
}

function splitPipeRow(line) {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);
}

const children = [];
let i = 0;

while (i < lines.length) {
  const line = lines[i];

  if (line.trim() === "") {
    i++;
    continue;
  }

  // fenced code block
  if (line.trim().startsWith("```")) {
    const codeLines = [];
    i++;
    while (i < lines.length && !lines[i].trim().startsWith("```")) {
      codeLines.push(lines[i]);
      i++;
    }
    i++; // skip closing fence
    codeLines.forEach((cl) => {
      children.push(
        new Paragraph({
          children: [new TextRun({ text: cl.length ? cl : " ", font: "Consolas", size: 18 })],
          shading: { type: ShadingType.CLEAR, fill: "F5F5F5" },
        })
      );
    });
    continue;
  }

  // headers
  const hMatch = /^(#{1,6})\s+(.*)$/.exec(line);
  if (hMatch) {
    const level = hMatch[1].length;
    const headingMap = {
      1: HeadingLevel.HEADING_1,
      2: HeadingLevel.HEADING_2,
      3: HeadingLevel.HEADING_3,
      4: HeadingLevel.HEADING_4,
      5: HeadingLevel.HEADING_5,
      6: HeadingLevel.HEADING_6,
    };
    children.push(
      new Paragraph({
        heading: headingMap[level] || HeadingLevel.HEADING_6,
        spacing: { before: 240, after: 120 },
        children: parseInline(hMatch[2]),
      })
    );
    i++;
    continue;
  }

  // markdown table: a line starting with | followed by a separator line
  if (line.trim().startsWith("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
    const header = splitPipeRow(line);
    i += 2;
    const bodyRows = [];
    while (i < lines.length && lines[i].trim().startsWith("|")) {
      bodyRows.push(splitPipeRow(lines[i]));
      i++;
    }
    children.push(makeTable(header, bodyRows));
    children.push(new Paragraph({ text: "" }));
    continue;
  }

  // bullet list
  if (/^\s*[-*]\s+/.test(line)) {
    const content = line.replace(/^\s*[-*]\s+/, "");
    children.push(
      new Paragraph({
        bullet: { level: 0 },
        children: parseInline(content),
      })
    );
    i++;
    continue;
  }

  // numbered list
  const numMatch = /^\s*(\d+)\.\s+(.*)$/.exec(line);
  if (numMatch) {
    children.push(
      new Paragraph({
        numbering: { reference: "master-report-numbering", level: 0 },
        children: parseInline(numMatch[2]),
      })
    );
    i++;
    continue;
  }

  // plain paragraph (accumulate until blank line)
  const paraLines = [line];
  i++;
  while (i < lines.length && lines[i].trim() !== "" && !/^(#{1,6})\s+/.test(lines[i]) && !lines[i].trim().startsWith("|") && !lines[i].trim().startsWith("```")) {
    paraLines.push(lines[i]);
    i++;
  }
  children.push(new Paragraph({ children: parseInline(paraLines.join(" ")), spacing: { after: 120 } }));
}

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "master-report-numbering",
        levels: [
          {
            level: 0,
            format: "decimal",
            text: "%1.",
            alignment: "start",
          },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {},
      children,
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUT, buffer);
  console.log(`Saved: ${OUT}`);
});
