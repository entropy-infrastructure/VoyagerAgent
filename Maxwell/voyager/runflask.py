import os
from flask import Flask, request
from .voyager_entry import Voyager
import requests

app = Flask(__name__)
ips = []
parent = "0.0.0.0"
nodes = {}

def send_instruction(child_ip, instruction):
    data = {'instruction': instruction}
    requests.post(f'http://{child_ip}/instruction', json=data)

def register_with_parent(parent_ip, node_ip):
    data = {'node_ip': node_ip}
    requests.post(f'http://{parent_ip}/register', json=data)

def register_with_child(child_ip, node_ip):
    data = {'parent_ip': node_ip}
    requests.post(f'http://{child_ip}/parent', json=data)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    parent_ip = data.get('parent_ip')
    node_ip = data.get('node_ip')
    if parent_ip not in nodes:
        nodes[parent_ip] = []
    nodes[parent_ip].append(node_ip)
    return '', 204

@app.route('/parent', methods=['POST'])
def register():
    data = request.get_json()
    node_ip = data.get('parent_ip')
    parent = node_ip

    return '', 204

@app.route('/instruction', methods=['POST'])
def receive_instruction():
    data = request.get_json()
    instruction = data.get('instruction')
    # Now do something with the instruction

    for ip in ips:
        send_instruction(ip, instruction)

    return '', 204

if __name__ == "__main__":
    v = Voyager(openai_api_key=os.environ['OPENAI_API_KEY'])

    #deploy thing
    ips.extend(v._learn())
    register_with_parent(ips)

    #start pinging
    v._learn()

    app.run("0.0.0.0", "80;80")
