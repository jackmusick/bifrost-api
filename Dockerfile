# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice
FROM mcr.microsoft.com/azure-functions/python:4.0-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Install Azure CLI for DefaultAzureCredential support
RUN apt-get update && \
    apt-get install -y curl && \
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy Azure Functions app code
COPY function_app.py host.json bifrost.py /home/site/wwwroot/
COPY bifrost/ /home/site/wwwroot/bifrost/
COPY shared/ /home/site/wwwroot/shared/
COPY functions/ /home/site/wwwroot/functions/
COPY platform/ /home/site/wwwroot/platform/

# For local run - create a known key ('test') for x-functions-key
RUN mkdir -p /azure-functions-host/Secrets/
RUN echo '{"masterKey":{"name":"master","value":"test","encrypted":false},"functionKeys":[]}' > /azure-functions-host/Secrets/host.json

# Expose Azure Functions runtime port
EXPOSE 80

# Expose debugpy port (only used when ENABLE_DEBUGGING=true)
EXPOSE 5678

# Use default Azure Functions startup
CMD ["/opt/startup/start_nonappservice.sh"]