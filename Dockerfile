FROM python:3.11

# Set up a new user named "user" with user ID 1000
# Hugging Face requires apps to run as a non-root user for security
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy the current directory contents into the container at $HOME/app
COPY --chown=user . $HOME/app

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Start the FastAPI app on port 7860 (Required by Hugging Face)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
