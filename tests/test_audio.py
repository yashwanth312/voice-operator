from voice_operator.audio import chunk_bytes, BYTES_PER_CHUNK


def test_chunk_bytes_splits_evenly():
    data = b"\x00" * (BYTES_PER_CHUNK * 3)
    chunks = list(chunk_bytes(data))
    assert len(chunks) == 3
    assert all(len(c) == BYTES_PER_CHUNK for c in chunks)


def test_chunk_bytes_keeps_remainder():
    data = b"\x00" * (BYTES_PER_CHUNK + 10)
    chunks = list(chunk_bytes(data))
    assert len(chunks) == 2
    assert len(chunks[-1]) == 10
