from app.services.knowledge_service import chunk_text, cosine_similarity, embed_text, vector_backend_status


def test_chunk_text_splits_large_content():
    content = "Paragraph one.\n\n" + ("A" * 400)
    chunks = chunk_text(content, chunk_size=120, overlap=20)
    assert len(chunks) >= 3
    assert all(chunk.strip() for chunk in chunks)


def test_embed_text_similarity_prefers_related_text():
    query = embed_text("dragon empire capital")
    related = embed_text("the dragon empire has a capital city")
    unrelated = embed_text("space station docking report")
    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class _FakeStatusDB:
    def __init__(self, values):
        self.values = iter(values)

    def execute(self, *_args, **_kwargs):
        return _ScalarResult(next(self.values))


def test_vector_backend_status_reports_missing_extension_files():
    db = _FakeStatusDB([False])
    status = vector_backend_status(db)
    assert status["mode"] == "fallback"
    assert status["pgvector_ready"] is False
    assert "not installed" in status["reason"]
