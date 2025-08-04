# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY ./app /usr/src/app

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable to ensure Python output is sent straight to the terminal
ENV PYTHONUNBUFFERED=1

# Run the application using Gunicorn
# This is the standard way to run a Flask app in production.
# It starts 4 worker processes, listening on port 5000.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "main:app"]
