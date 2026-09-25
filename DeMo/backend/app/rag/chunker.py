def chunk_text(text, chunk_size=500, overlap=100):

    words = text.split()

    chunks = []

    current_chunk = []
    current_length = 0

    for word in words:

        word_length = len(word) + 1

        if current_length + word_length > chunk_size:

            chunks.append(
                " ".join(current_chunk)
            )

            # Keep some words for overlap
            overlap_words = current_chunk[-20:]

            current_chunk = overlap_words + [word]

            current_length = sum(
                len(w) + 1
                for w in current_chunk
            )

        else:

            current_chunk.append(word)
            current_length += word_length

    if current_chunk:

        chunks.append(
            " ".join(current_chunk)
        )

    return chunks


def chunk_documents(documents):

    all_chunks = []

    for document in documents:

        chunks = chunk_text(
            document["text"]
        )

        for chunk in chunks:

            all_chunks.append({
                "source": document["source"],
                "text": chunk
            })

    return all_chunks