import azure.functions as func
import json
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Health check endpoint called")
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "Workflow Engine"}),
        mimetype="application/json"
    )

@app.route(route="admin/workflow", methods=["GET"])
def admin_workflow(req: func.HttpRequest) -> func.HttpResponse:
    # Will be populated by decorator registry
    # Optional query parameter: ?type=workflows or ?type=options
    workflow_type = req.params.get('type')

    logging.info(f"Admin workflow endpoint called with type={workflow_type}")

    response_data = {
        "workflows": [],
        "option_generators": []
    }

    # Filter by type if specified
    if workflow_type == 'workflows':
        response_data = {"workflows": response_data["workflows"]}
    elif workflow_type == 'options':
        response_data = {"option_generators": response_data["option_generators"]}

    return func.HttpResponse(
        json.dumps(response_data),
        mimetype="application/json"
    )
