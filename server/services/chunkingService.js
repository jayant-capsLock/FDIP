
const TARGET_CHUNK_SIZE = 1800;
const MAX_CHUNK_SIZE = 2000;
const OVERLAP_SIZE = 250;
const MIN_CHUNK_SIZE = 200;

export const chunkDocument = (text) => {
  if (!text || typeof text !== "string") {
    return [];
  }

  // Normalize OCR output without destroying line structure.
  const normalizedText = text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+/g, " ")
    .trim();

  if (!normalizedText) {
    return [];
  }

  // Preserve paragraphs and table rows as individual units.
  const segments = normalizedText
    .split(/\n+/)
    .map((segment) => segment.trim())
    .filter(Boolean);

  const chunks = [];
  let currentChunk = "";

  const pushChunk = () => {
    const cleaned = currentChunk.trim();

    if (cleaned) {
      chunks.push(cleaned);
    }
  };

  for (const segment of segments) {
    // Handle unusually long lines separately.
    if (segment.length > MAX_CHUNK_SIZE) {
      pushChunk();
      currentChunk = "";

      let position = 0;

      while (position < segment.length) {
        const end = Math.min(
          position + MAX_CHUNK_SIZE,
          segment.length
        );

        chunks.push(segment.slice(position, end).trim());

        position = end - OVERLAP_SIZE;

        if (position < 0) {
          position = 0;
        }

        if (end === segment.length) {
          break;
        }
      }

      continue;
    }

    const candidate = currentChunk
      ? `${currentChunk}\n${segment}`
      : segment;

    if (candidate.length <= TARGET_CHUNK_SIZE) {
      currentChunk = candidate;
      continue;
    }

    pushChunk();

    // Carry previous context into the next chunk.
    const overlap = currentChunk.slice(-OVERLAP_SIZE).trim();

    currentChunk = overlap
      ? `${overlap}\n${segment}`
      : segment;

    // If overlap + segment exceeds the maximum, keep
    // the segment intact rather than splitting it.
    if (currentChunk.length > MAX_CHUNK_SIZE) {
      pushChunk();
      currentChunk = segment;
    }
  }

  pushChunk();

  // Merge a small final chunk into its predecessor.
  if (
    chunks.length > 1 &&
    chunks[chunks.length - 1].length < MIN_CHUNK_SIZE
  ) {
    const lastChunk = chunks.pop();

    chunks[chunks.length - 1] += `\n${lastChunk}`;
  }

  return chunks.map((chunk, index) => ({
    chunk_index: index,
    chunk_text: chunk,
    char_count: chunk.length,
    page_start: 1,
    page_end: 1,
  }));
};
