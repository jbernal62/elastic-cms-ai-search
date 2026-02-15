FROM python:3.11-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ML models into the image so there's no runtime download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); SentenceTransformer('clip-ViT-B-32')"

COPY . .

CMD ["functions-framework", "--target=process_asset", "--signature-type=cloudevent"]
