import hashlib
import json
from dataclasses import asdict

from app.rag.llm.prompts.builtin_library import list_builtin_prompt_templates


def test_builtin_prompt_library_content_is_byte_stable() -> None:
    templates = list_builtin_prompt_templates()
    payload = json.dumps(
        [asdict(template) for template in templates],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    assert len(templates) == 33
    assert hashlib.sha256(payload.encode()).hexdigest() == (
        "08d345bab5e79828773ed760eb48e5e757b9b1262c523f9b4f10f7d5d4afc19b"
    )
