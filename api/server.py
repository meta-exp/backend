from flask import Flask, jsonify, request, abort, session
from flask_session import Session
from flask_cors import CORS
from util.config import REACT_PORT, API_PORT, SESSION_CACHE_DIR, SESSION_MODE, SESSION_THRESHOLD, RATED_DATASETS_PATH
from util.meta_path_loader import MetaPathLoaderDispatcher
from active_learning.meta_path_selector import RandomMetaPathSelector
import json
import os
import time

app = Flask(__name__)

# TODO: Change if we have a database in the background
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = SESSION_CACHE_DIR
SESSION_FILE_THRESHOLD = SESSION_THRESHOLD
# We need leading zeros on the modifier
SESSION_FILE_MODE = int(SESSION_MODE, 8)
SESSION_PERMANENT = True
app.config.from_object(__name__)
# TODO: Change for deployment, e.g. use environment variable
app.config["SECRET_KEY"] = "37Y,=i9.,U3RxTx92@9j9Z[}"
Session(app)

CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:{}".format(REACT_PORT)}})

def run(port, hostname, debug_mode):
    app.run(host=hostname, port=port, debug=debug_mode, threaded=True)

@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == 'POST':
        data = request.get_json()
        print(data)
        session['username'] = data['username']
        session['dataset'] = data['dataset']
        session['purpose'] = data['purpose']
        # TODO use key from dataset to select data
        meta_path_loader = MetaPathLoaderDispatcher().get_loader("Rotten Tomato")
        meta_paths = meta_path_loader.load_meta_paths()
        session['meta_path_distributor'] = RandomMetaPathSelector(meta_paths=meta_paths)
        session['meta_path_id'] = 1
        session['rated_meta_paths'] = []
    return jsonify({'status': 200})


@app.route('/logout')
def logout():
    rated_meta_paths = {
        'meta_paths': session['rated_meta_paths'],
        'dataset': session['dataset'],
        'username': session['username'],
        'purpose': session['purpose']
    }
    filename = '{}_{}_{}.json'.format(session['datset'], session['username'], time.time())
    path = os.path.join(RATED_DATASETS_PATH, filename)
    json.dump(rated_meta_paths, open(path,"w", encoding="utf8"))
    session.clear()
    return 'OK'

# TODO: If meta-paths for A and B will be written in Java, they will need this information in Java
@app.route("/node-sets", methods=["POST"])
def receive_node_sets():
    # TODO: Check if necessary information is in request object
    if not request.json:
        abort(400)


@app.route("/node-sets", methods=["GET"])
def send_node_sets():
    # TODO: Call fitting method in active_learning
    # TODO: Check if necessary information is in request object

    return jsonify("Hello world")


# TODO: If meta-paths for A and B will be written in Java, they will need this information in Java
@app.route("/types", methods=["POST"])
def receive_edge_node_types():
    # TODO: Check if necessary information is in request object
    if not request.json:
        abort(400)

@app.route("/next-meta-paths/<int:batch_size>", methods=["GET"])
def send_next_metapaths_to_rate(batch_size):
    meta_path_id = session['meta_path_id']
    next_batch = session['meta_path_distributor'].get_next(size=batch_size)
    paths = [{'id': id,
              'metapath': meta_path.as_list(),
              'rating': 0.5} for id, meta_path in zip(range(meta_path_id, meta_path_id + batch_size), next_batch)]
    meta_path_id += batch_size
    session['meta_path_id'] = meta_path_id
    return jsonify(paths)


@app.route("/get-available-datasets", methods=["GET"])
def get_available_datasets():
    """
        Deliver all available data sets for rating and a short description of each.
    """
    return jsonify(MetaPathLoaderDispatcher().get_available_datasets())


# TODO: Maybe post each rated meta-path
@app.route("/rate-meta-paths", methods=["POST"])
def receive_rated_metapaths():
    if not request.is_json:
        abort(400)
    rated_metapaths = request.get_json()
    for datapoint in rated_metapaths:
        if not all(key in datapoint for key in ['id', 'metapath', 'rating']):
            abort(400)  # malformed input
    session['rated_meta_paths'] = session['rated_meta_paths'] + rated_metapaths
    return 'OK'


@app.route("/results", methods=["GET"])
def send_results():
    # TODO: Call fitting method in explanation
    return jsonify("Hello world")


if __name__ == '__main__':
    app.run(port=API_PORT, threaded=True)
