from langchain_text_splitters import RecursiveCharacterTextSplitter
from file_loaders import universal_file_loader


splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20,
)

def split_text_into_chunks(file_path):
    text = universal_file_loader(file_path)

    chunks = splitter.split_text(text)

    return chunks

if __name__ == "__main__":
    file_path = "Files\Vinayak Mishra Resume.docx"
    chunks = split_text_into_chunks(file_path)
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}: {chunk}")