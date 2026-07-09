# Use a lightweight Python 3.10 base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the dependency list and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files into the container
COPY . .

# Set the default command to run a quick test simulation
CMD ["python", "sim/run_multiseed.py", "--seeds", "2", "--bg", "5.0"]