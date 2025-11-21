# Use official Python 3.11 base image (supports both ARM64 and x86_64)
FROM python:3.11-slim

# Install system dependencies including ICU for Azure Functions Core Tools
RUN apt-get update && \
    apt-get install -y \
    curl \
    wget \
    gnupg \
    lsb-release \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Azure CLI for DefaultAzureCredential support
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install Azure Functions Core Tools v4
RUN wget -q https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y azure-functions-core-tools-4 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up Azure Functions environment
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    FUNCTIONS_WORKER_RUNTIME=python

# Install Python dependencies
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

# Create application directory
RUN mkdir -p /home/site/wwwroot

# Copy Azure Functions app code
COPY function_app.py host.json bifrost.py /home/site/wwwroot/
COPY bifrost/ /home/site/wwwroot/bifrost/
COPY shared/ /home/site/wwwroot/shared/
COPY functions/ /home/site/wwwroot/functions/
COPY platform/ /home/site/wwwroot/platform/

# Set working directory
WORKDIR /home/site/wwwroot

# For local run - create a known key ('test') for x-functions-key
RUN mkdir -p /home/site/wwwroot/.azurefunctions/
RUN echo '{"masterKey":{"name":"master","value":"test","encrypted":false},"functionKeys":[]}' > /home/site/wwwroot/.azurefunctions/host.json

# Expose Azure Functions runtime port
EXPOSE 80

# Expose debugpy port (only used when ENABLE_DEBUGGING=true)
EXPOSE 5678

# Start Azure Functions Core Tools
CMD ["func", "start", "--host", "0.0.0.0", "--port", "80"]
