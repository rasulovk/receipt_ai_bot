FROM python:3.10-alpine

# Create a non-root user with UID 1001
RUN adduser -D -u 1001 appuser

# Set the working directory
WORKDIR /home/appuser

# Install build dependencies (if needed, e.g. for pip packages with C extensions)
RUN apk add --no-cache build-base

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# # Copy the rest of the code
# COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /home/appuser

# Switch to the non-root user
USER appuser

# Set the default command
CMD ["python", "/home/appuser/main.py"]