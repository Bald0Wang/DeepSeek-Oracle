try:
    import jieba
except Exception:  # pragma: no cover
    jieba = None


def tokenize_text(text: str) -> list[str]:
    if not text:
        return []

    if jieba is None:
        return text.split()

    return list(jieba.cut(text))


def count_tokens(text: str) -> int:
    return len(tokenize_text(text))
