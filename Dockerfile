FROM python:3.12-slim

# Install system dependencies: ffmpeg, curl, ca-certificates, nodejs
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# Set up non-root user (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:/home/user/.deno/bin:$PATH

# Install Deno for yt-dlp JavaScript challenge solver & PO token generator
RUN curl -fsSL https://deno.land/install.sh | sh

WORKDIR /home/user/app

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user:user . .

ENV PORT=7860
EXPOSE 7860

CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "300", "app:app"]
