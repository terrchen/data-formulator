# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import sys
import os

import flask
from flask import Flask, request, send_from_directory, redirect, url_for
from flask import stream_with_context, Response
import html

from flask_cors import CORS

import json
import time
from pathlib import Path

from vega_datasets import local_data

APP_ROOT = Path(os.path.join(Path(__file__).parent, 'server')).absolute()
sys.path.append(os.path.abspath(APP_ROOT))

from agents.agent_concept_derive import ConceptDeriveAgent
from agents.agent_data_transformation import DataTransformationAgent
from agents.agent_data_transform_v2 import DataTransformationAgentV2
from agents.agent_data_rec import DataRecAgent

from agents.agent_sort_data import SortDataAgent
from agents.agent_data_load import DataLoadAgent
from agents.agent_data_filter import DataFilterAgent
from agents.agent_generic_py_concept import GenericPyConceptDeriveAgent
from agents.agent_code_explanation import CodeExplanationAgent

from agents.client_utils import get_client

import pathlib

from dotenv import load_dotenv


APP_DIR = pathlib.Path(__file__).parent.resolve()
load_dotenv(os.path.join(APP_DIR, 'openai-keys.env'))

import os

app = Flask(__name__, static_url_path='', static_folder=os.path.join(APP_ROOT, "..", "build"))
CORS(app)


@app.route('/vega-datasets')
def get_example_dataset_list():
    dataset_names = local_data.list_datasets()
    dataset_info = []
    for name in dataset_names:
        try:
            info_obj = {'name': name, 'snapshot': local_data.__getattr__(name)().to_dict("records")[:10]} 
        except:
            pass
        dataset_info.append(info_obj)
    
    response = flask.jsonify(dataset_info)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/vega-dataset/<path:path>')
def get_datasets(path):
    try:
        df = local_data.__getattr__(path)()
        data_object = json.dumps(df.to_dict("records"))
    except:
        data_object = "[]"
    response = data_object
    return response

@app.route('/check-available-models', methods=['GET', 'POST'])
def check_available_models():

    client = get_client(os.getenv("ENDPOINT"), "")
    models = [model.strip() for model in os.getenv("MODELS").split(',')]

    results = []
    
    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Respond 'I can hear you.' if you can hear me. Do not say anything other than 'I can hear you.'"},
                ]
            )

            print(f"model: {model}")
            print(f"welcome message: {response.choices[0].message.content}")

            if "I can hear you." in response.choices[0].message.content:
                results.append({
                    "endpoint": "default",
                    "key": "",
                    "model": model
                })
        except:
            pass
    return json.dumps(results)

@app.route('/test-model', methods=['GET', 'POST'])
def test_model():
    
    if request.is_json:
        app.logger.info("# code query: ")
        content = request.get_json()
        endpoint = html.escape(content['endpoint'].strip())
        key = html.escape(f"{content['key']}".strip())

        print(content)

        client = get_client(endpoint, key)
        model = html.escape(content['model'].strip())

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Respond 'I can hear you.' if you can hear me. Do not say anything other than 'I can hear you.'"},
                ]
            )

            print(f"model: {model}")
            print(f"welcome message: {response.choices[0].message.content}")

            if "I can hear you." in response.choices[0].message.content:
                result = {
                    "endpoint": endpoint,
                    "key": key,
                    "model": model,
                    "status": 'ok'
                }
        except Exception as e:
            print(e)
            result = {
                "endpoint": endpoint,
                "key": key,
                "model": model,
                "status": 'error'
            }
    else:
        {'status': 'error'}
    
    return json.dumps(result)

@app.route('/about', defaults={'path': ''})
def catch_all(path):
  return send_from_directory(app.static_folder, "index.html")


@app.route("/", defaults={"path": ""})
def index_alt(path):
    print(app.static_folder)
    return send_from_directory(app.static_folder, "index.html")

@app.errorhandler(404)
def page_not_found(e):
    # your processing here
    print(app.static_folder)
    return send_from_directory(app.static_folder, "index.html") #'Hello 404!' #send_from_directory(app.static_folder, "index.html")

###### test functions ######

@app.route('/hello')
def hello():
    values = [
            {"a": "A", "b": 28}, {"a": "B", "b": 55}, {"a": "C", "b": 43},
            {"a": "D", "b": 91}, {"a": "E", "b": 81}, {"a": "F", "b": 53},
            {"a": "G", "b": 19}, {"a": "H", "b": 87}, {"a": "I", "b": 52}
        ]
    spec =  {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "A simple bar chart with embedded data.",
        "data": { "values": values },
        "mark": "bar",
        "encoding": {
            "x": {"field": "a", "type": "nominal", "axis": {"labelAngle": 0}},
            "y": {"field": "b", "type": "quantitative"}
        }
    }
    return json.dumps(spec)


@app.route('/hello-stream')
def streamed_response():
    def generate():
        values = [
            {"a": "A", "b": 28}, {"a": "B", "b": 55}, {"a": "C", "b": 43},
            {"a": "D", "b": 91}, {"a": "E", "b": 81}, {"a": "F", "b": 53},
            {"a": "G", "b": 19}, {"a": "H", "b": 87}, {"a": "I", "b": 52}
        ]
        spec =  {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": "A simple bar chart with embedded data.",
            "data": { "values": [] },
            "mark": "bar",
            "encoding": {
                "x": {"field": "a", "type": "nominal", "axis": {"labelAngle": 0}},
                "y": {"field": "b", "type": "quantitative"}
            }
        }
        for i in range(3):
            time.sleep(3)
            spec["data"]["values"] = values[i:]
            yield json.dumps(spec)
    return Response(stream_with_context(generate()))


###### agent related functions ######

@app.route('/process-data-on-load', methods=['GET', 'POST'])
def process_data_on_load_request():

    if request.is_json:
        app.logger.info("# process data query: ")
        content = request.get_json()
        token = content["token"]

        client = get_client(content['model']['endpoint'], content['model']['key'])
        model = content['model']['model']
        app.logger.info(f" model: {content['model']}")
        
        agent = DataLoadAgent(client=client, model=model)
        candidates = agent.run(content["input_data"])
        
        candidates = [c['content'] for c in candidates if c['status'] == 'ok']

        response = flask.jsonify({ "status": "ok", "token": token, "result": candidates })
    else:
        response = flask.jsonify({ "token": -1, "status": "error", "result": [] })

    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/derive-concept-request', methods=['GET', 'POST'])
def derive_concept_request():

    if request.is_json:
        app.logger.info("# code query: ")
        content = request.get_json()
        token = content["token"]

        client = get_client(content['model']['endpoint'], content['model']['key'])
        model = content['model']['model']
        app.logger.info(f" model: {content['model']}")
        
        agent = ConceptDeriveAgent(client=client, model=model)

        #print(content["input_data"])

        candidates = agent.run(content["input_data"], [f['name'] for f in content["input_fields"]], 
                                       content["output_name"], content["description"])
        
        candidates = [c['code'] for c in candidates if c['status'] == 'ok']

        response = flask.jsonify({ "status": "ok", "token": token, "result": candidates })
    else:
        response = flask.jsonify({ "token": -1, "status": "error", "result": [] })

    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/codex-sort-request', methods=['GET', 'POST'])
def sort_data_request():

    if request.is_json:
        app.logger.info("# sort query: ")
        content = request.get_json()
        token = content["token"]

        client = get_client(content['model']['endpoint'], content['model']['key'])
        model = content['model']['model']
        app.logger.info(f" model: {content['model']}")

        agent = SortDataAgent(client=client, model=model)
        candidates = agent.run(content['field'], content['items'])

        #candidates, dialog = limbo_concept.call_codex_sort(content["items"], content["field"])
        candidates = candidates if candidates != None else []
        response = flask.jsonify({ "status": "ok", "token": token, "result": candidates })            
    else:
        response = flask.jsonify({ "token": -1, "status": "error", "result": [] })

    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/derive-data', methods=['GET', 'POST'])
def derive_data():

    if request.is_json:
        app.logger.info("# request data: ")
        content = request.get_json()        
        token = content["token"]

        client = get_client(content['model']['endpoint'], content['model']['key'])
        model = content['model']['model']
        app.logger.info(f" model: {content['model']}")

        # each table is a dict with {"name": xxx, "rows": [...]}
        input_tables = content["input_tables"]
        new_fields = content["new_fields"]
        instruction = content["extra_prompt"]

        mode = "transform"
        if len(new_fields) == 0:
            mode = "recommendation"

        if mode == "recommendation":
            # now it's in recommendation mode
            agent = DataRecAgent(client, model)
            results = agent.run(input_tables, instruction)
        else:
            agent = DataTransformationAgentV2(client=client, model=model)
            results = agent.run(input_tables, instruction, [field['name'] for field in new_fields])

        repair_attempts = 0
        while results[0]['status'] == 'error' and repair_attempts < 2:
            error_message = results[0]['content']
            new_instruction = f"We run into the following problem executing the code, please fix it:\n\n{error_message}\n\nPlease think step by step, reflect why the error happens and fix the code so that no more errors would occur."

            prev_dialog = results[0]['dialog']

            if mode == "transform":
                results = agent.followup(input_tables, prev_dialog, [field['name'] for field in new_fields], new_instruction)
            if mode == "recommendation":
                results = agent.followup(input_tables, prev_dialog, new_instruction)

            repair_attempts += 1
        
        for result in results:
            if result['status'] != 'no transformation':
                code_expl_agent = CodeExplanationAgent(client=client, model=model)
                expl = code_expl_agent.run(input_tables, result['code'])
                result['codeExpl'] = expl
                print(expl)
            else:
                result['codeExpl'] = 'no transformation is necessary'

        response = flask.jsonify({ "status": "ok", "token": token, "results": results })
    else:
        response = flask.jsonify({ "token": "", "status": "error", "results": [] })

    response.headers.add('Access-Control-Allow-Origin', '*')
    return response



@app.route('/refine-data', methods=['GET', 'POST'])
def refine_data():

    if request.is_json:
        app.logger.info("# request data: ")
        content = request.get_json()        
        token = content["token"]

        client = get_client(content['model']['endpoint'], content['model']['key'])
        model = content['model']['model']
        app.logger.info(f" model: {content['model']}")

        # each table is a dict with {"name": xxx, "rows": [...]}
        input_tables = content["input_tables"]
        output_fields = content["output_fields"]
        dialog = content["dialog"]
        new_instruction = content["new_instruction"]
        
        print("previous dialog")
        print(dialog[0]['content'])
        prev_system_prompt = dialog[0]['content']

        if prev_system_prompt.startswith("You are a data scientist to help user to filter data based on user description."):
            agent = DataFilterAgent(client, model=model)
            results = agent.followup(input_tables[0], dialog, new_instruction)
        elif prev_system_prompt.startswith("You are a data scientist to help user to derive new column based on existing columns in a dataset."):
            agent = GenericPyConceptDeriveAgent(client, model=model)
            new_field_name = [field['name'] for field in output_fields if field['name'] not in input_tables[0][0].keys()][0]
            results = agent.followup(input_tables[0], new_field_name, dialog, new_instruction)
        else:
            agent = DataTransformationAgentV2(client, model=model)
            results = agent.followup(input_tables, dialog, [field['name'] for field in output_fields], new_instruction)

            repair_attempts = 0
            while results[0]['status'] == 'error' and repair_attempts < 2:
                error_message = results[0]['content']
                new_instruction = f"We run into the following problem executing the code, please fix it:\n\n{error_message}\n\nPlease think step by step, reflect why the error happens and fix the code so that no more errors would occur."

                response_message = dialog['response']['choices'][0]['message']
                prev_dialog = [*dialog['messages'], {"role": response_message['role'], 'content': response_message['content']}]

                results = agent.followup(input_tables, prev_dialog, [field['name'] for field in output_fields], new_instruction)
                repair_attempts += 1
            
        for result in results:
            code_expl_agent = CodeExplanationAgent(client=client, model=model)
            expl = code_expl_agent.run(input_tables, result['code'])
            result['codeExpl'] = expl
            print(expl)

        response = flask.jsonify({ "status": "ok", "token": token, "results": results})
    else:
        response = flask.jsonify({ "token": "", "status": "error", "results": []})

    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__ == '__main__':
    #app.run(debug=True, host='127.0.0.1', port=5000)
    #use 0.0.0.0 for public
    app.run(host='0.0.0.0', port=5000, threaded=True)