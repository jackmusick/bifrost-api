import azure.functions as func
import json
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Health check endpoint called")
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "Management API"}),
        mimetype="application/json"
    )

@app.route(route="organizations", methods=["GET"])
def get_organizations(req: func.HttpRequest) -> func.HttpResponse:
    # Placeholder - will be implemented later
    logging.info("Get organizations endpoint called")
    return func.HttpResponse(
        json.dumps([{"id": "1", "name": "Sample Organization"}]),
        mimetype="application/json"
    )
