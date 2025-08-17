import os
import mimetypes
from dataclasses import dataclass
from typing import List

from localknow.config import settings


SUPPORTED_EXTS = {".pdf", ".txt", ".md", ".csv", ".docx"}


@dataclass
class ValidationIssue:
    path: str
    reason: str


@dataclass
class ValidationResult:
    valid_paths: List[str]
    issues: List[ValidationIssue]


class ContentValidator:
    def validate_folder(self, folder_path: str) -> ValidationResult:
        valid_paths: List[str] = []
        issues: List[ValidationIssue] = []

        for root, _dirs, files in os.walk(folder_path):
            for name in files:
                path = os.path.join(root, name)
                ext = os.path.splitext(name)[1].lower()
                try:
                    size = os.path.getsize(path)
                except OSError:
                    issues.append(ValidationIssue(path, "unreadable"))
                    continue

                if ext not in SUPPORTED_EXTS:
                    issues.append(ValidationIssue(path, f"unsupported extension: {ext}"))
                    continue

                if size <= 0:
                    issues.append(ValidationIssue(path, "empty file"))
                    continue

                if size > settings.max_doc_bytes:
                    issues.append(ValidationIssue(path, f"file too large: {size}"))
                    continue

                mime, _ = mimetypes.guess_type(path)
                if mime is None and ext not in {".md", ".txt"}:
                    issues.append(ValidationIssue(path, "unknown MIME"))
                    continue

                valid_paths.append(path)

        return ValidationResult(valid_paths=valid_paths, issues=issues) 