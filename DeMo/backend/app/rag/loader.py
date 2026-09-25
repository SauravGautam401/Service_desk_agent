from pathlib import Path
from pypdf import PdfReader


def load_pdf(file_path):
    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def load_txt(file_path):
    return Path(file_path).read_text(
        encoding="utf-8"
    )


def load_document(file_path):

    file_path = Path(file_path)

    if file_path.suffix.lower() == ".pdf":
        return load_pdf(file_path)

    elif file_path.suffix.lower() == ".txt":
        return load_txt(file_path)

    else:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}"
        )


def load_knowledge_base(folder_path):

    folder = Path(folder_path)

    documents = []

    for file_path in folder.iterdir():

        if file_path.suffix.lower() in [".txt", ".pdf"]:

            text = load_document(file_path)

            documents.append({
                "source": file_path.name,
                "text": text
            })

    return documents