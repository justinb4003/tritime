import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()


@app.route(route="punch",
           auth_level=func.AuthLevel.ANONYMOUS)
def punch_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Punch it')
    badge = req.params.get('badge')
    action = req.params.get('action')
    logging.info(f'badge = {badge}')
    logging.info(f'action = {action}')
    return func.HttpResponse(
            "OK",
            status_code=200
    )