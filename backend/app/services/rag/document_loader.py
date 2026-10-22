from pathlib import Path


class PolicyDocumentLoader:
    def __init__(self, policy_directory: str):
        self.policy_directory = Path(policy_directory)

    def load_documents(self) -> list[dict]:
        if not self.policy_directory.exists():
            raise FileNotFoundError(
                f"Policy directory not found: {self.policy_directory}"
            )

        documents = []

        for file_path in sorted(self.policy_directory.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8").strip()

            if not text:
                continue

            policy_id = self._extract_policy_id(text)

            documents.append(
                {
                    "source": file_path.name,
                    "policy_id": policy_id,
                    "text": text,
                }
            )

        return documents

    @staticmethod
    def _extract_policy_id(text: str) -> str:
        for line in text.splitlines():
            if line.startswith("Policy ID:"):
                return line.split(":", 1)[1].strip()

        return "UNKNOWN"