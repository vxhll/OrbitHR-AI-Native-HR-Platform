import re


class PolicyChunker:
    def __init__(self, max_chunk_size: int = 1200):
        self.max_chunk_size = max_chunk_size

    def chunk_documents(self, documents: list[dict]) -> list[dict]:
        chunks = []

        for document in documents:
            sections = self._split_into_sections(document["text"])

            chunk_index = 0

            for section_title, section_text in sections:
                section_text = section_text.strip()

                if not section_text:
                    continue

                section_chunks = self._split_large_section(section_text)

                for chunk_text in section_chunks:
                    chunks.append(
                        {
                            "id": (
                                f'{document["policy_id"]}'
                                f'_{chunk_index}'
                            ),
                            "text": chunk_text,
                            "metadata": {
                                "source": document["source"],
                                "policy_id": document["policy_id"],
                                "section": section_title,
                                "chunk_index": chunk_index,
                            },
                        }
                    )

                    chunk_index += 1

        return chunks

    def _split_into_sections(
        self,
        text: str,
    ) -> list[tuple[str, str]]:
        lines = text.splitlines()

        sections = []
        current_title = "POLICY HEADER"
        current_lines = []

        section_pattern = re.compile(
            r"^\d+\.\s+.+$"
        )

        for line in lines:
            stripped = line.strip()

            if section_pattern.match(stripped):
                if current_lines:
                    sections.append(
                        (
                            current_title,
                            "\n".join(current_lines).strip(),
                        )
                    )

                current_title = stripped
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(
                (
                    current_title,
                    "\n".join(current_lines).strip(),
                )
            )

        return sections

    def _split_large_section(
        self,
        text: str,
    ) -> list[str]:
        if len(text) <= self.max_chunk_size:
            return [text]

        paragraphs = re.split(
            r"\n\s*\n",
            text,
        )

        chunks = []
        current = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            candidate = (
                f"{current}\n\n{paragraph}"
                if current
                else paragraph
            )

            if len(candidate) <= self.max_chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)

                if len(paragraph) <= self.max_chunk_size:
                    current = paragraph
                else:
                    chunks.extend(
                        self._split_long_paragraph(paragraph)
                    )
                    current = ""

        if current:
            chunks.append(current)

        return chunks

    def _split_long_paragraph(
        self,
        paragraph: str,
    ) -> list[str]:
        words = paragraph.split()

        chunks = []
        current_words = []
        current_length = 0

        for word in words:
            additional_length = (
                len(word)
                if not current_words
                else len(word) + 1
            )

            if (
                current_words
                and current_length + additional_length
                > self.max_chunk_size
            ):
                chunks.append(
                    " ".join(current_words)
                )
                current_words = [word]
                current_length = len(word)
            else:
                current_words.append(word)
                current_length += additional_length

        if current_words:
            chunks.append(
                " ".join(current_words)
            )

        return chunks