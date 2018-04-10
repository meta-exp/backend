from flask import Flask, jsonify, request, abort, session
from flask_session import Session
from flask_cors import CORS
from util.config import SERVER_PATH, REACT_PORT, API_PORT, SESSION_CACHE_DIR, SESSION_MODE, SESSION_THRESHOLD, RATED_DATASETS_PATH
from util.meta_path_loader_dispatcher import MetaPathLoaderDispatcher
from util.graph_stats import GraphStats
from active_learning.active_learner import UncertaintySamplingAlgorithm
from explanation.explanation import SimilarityScore
import json
import os
import time
import datetime
from flask_ask import Ask

app = Flask(__name__)
ask = Ask(app, '/alexa')

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

#TODO: Fix CORS origins specification
# Configure Cross Site Scripting
if "METAEXP_DEV" in os.environ.keys() and os.environ["METAEXP_DEV"] == "true":
    if REACT_PORT == 80:
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://{}".format(SERVER_PATH)}})
    else:
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://{}:{}".format(SERVER_PATH, REACT_PORT)}})
else:
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

def run(port, hostname, debug_mode):
    app.run(host=hostname, port=port, debug=debug_mode, threaded=True)


@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == 'POST' and 'username' not in session:
        data = request.get_json()

        # retrieve data from login
        print("Login route received data: {}".format(data))
        session['username'] = data['username']
        session['dataset'] = data['dataset']
        session['purpose'] = data['purpose']

        # setup dataset
        # TODO use key from dataset to select data
        meta_path_loader = MetaPathLoaderDispatcher().get_loader(session['dataset'])
        meta_paths = meta_path_loader.load_meta_paths()
        # TODO get Graph stats for current dataset
        graph_stats = GraphStats()
        session['active_learning_algorithm'] = UncertaintySamplingAlgorithm(meta_paths=meta_paths,
                                                                            hypothesis='Gaussian Process')
        session['meta_path_id'] = 1
        session['rated_meta_paths'] = []
        # TODO feed this selection to the ALgorithms
        session['selected_node_types'] = build_selection(graph_stats.get_node_types())
        session['selected_edge_types'] = build_selection(graph_stats.get_edge_types())

    return jsonify({'status': 200})


@app.route('/logout')
def logout():
    rated_meta_paths = {
        'meta_paths': session['active_learning_algorithm'].create_output(),
        'dataset': session['dataset'],
        'node_type_selection': session['selected_node_types'],
        'edge_type_selection': session['selected_edge_types'],
        'username': session['username'],
        'purpose': session['purpose']
    }
    filename = '{}_{}_{}.json'.format(session['dataset'], session['username'], time.time())
    path = os.path.join(RATED_DATASETS_PATH, filename)
    json.dump(rated_meta_paths, open(path, "w", encoding="utf8"))
    session.clear()
    return 'OK'


# TODO: If functionality "meta-paths for node set A and B" will be written in Java, team alpha will need this information in Java
@app.route("/node-sets", methods=["POST"])
def receive_node_sets():
    """
    Receives the node sets from the "Setup" page which the user selects.
    This endpoint is called for each new added node.

    The repeated calling enables us to start the following computations as early as possible
    so that we can return information on the next pages faster.
    For example on the first call we already know the type of the whole node set and
    therefore can begin to retrieve the corresponding node sets.
    """
    # TODO: Check if necessary information is in request object
    if not request.json:
        abort(400)
    raise NotImplementedError("This API endpoint isn't implemented in the moment")


@app.route("/node-sets", methods=["GET"])
def send_node_sets():
    """
    Returns the node sets which the user previously selected on the "Setup" page.
    """
    # TODO: Does active_learning really needs this endpoint? Does someone needs this endpoint?
    # TODO: Call fitting method in active_learning
    # TODO: Check if necessary information is in request object
    raise NotImplementedError("This API endpoint isn't implemented in the moment")


@app.route("/first-node -set-query", methods=["GET"])
def send_first_node_set():
    return jsonify({'node_set_query': 'MATCH (n)-[r]->(m) RETURN n,r,m'})


@app.route("/second-node-set-query", methods=["GET"])
def send_second_node_set():
    return jsonify({'node_set_query': 'MATCH (n)-[r]->(m) RETURN n,r,m'})


@app.route("/contributing-meta-paths", methods=["GET"])
def send_contributing_meta_paths():
    contributing_meta_paths = [
      {
        "id": "make",
        "label": "make",
        "value": 551,
        "color": "hsl(131, 70%, 50%)"
      },
      {
        "id": "erlang",
        "label": "erlang",
        "value": 226,
        "color": "hsl(358, 70%, 50%)"
      },
      {
        "id": "c",
        "label": "c",
        "value": 129,
        "color": "hsl(151, 70%, 50%)"
      },
      {
        "id": "php",
        "label": "php",
        "value": 67,
        "color": "hsl(52, 70%, 50%)"
      },
      {
        "id": "java",
        "label": "java",
        "value": 452,
        "color": "hsl(221, 70%, 50%)"
      },
      {
        "id": "stylus",
        "label": "stylus",
        "value": 406,
        "color": "hsl(102, 70%, 50%)"
      },
      {
        "id": "ruby",
        "label": "ruby",
        "value": 433,
        "color": "hsl(341, 70%, 50%)"
      }
    ]

    return jsonify({'contributing_meta_paths': contributing_meta_paths})


# TODO: If functionality "meta-paths for node set A and B" will be written in Java, team alpha will need this information in Java
@app.route("/set-edge-types", methods=["POST"])
def receive_edge_types():
    """
    Receives the node and edge types which are selected (types which are active) on the "Config" page.
    """

    # TODO: Check if necessary information is in request object
    if not request.json:
        abort(400)

    edge_types = request.get_json()
    session['selected_edge_types'] = edge_types
    return 'OK'


# TODO: If functionality "meta-paths for node set A and B" will be written in Java, team alpha will need this information in Java
@app.route("/set-node-types", methods=["POST"])
def receive_node_types():
    """
    Receives the node and edge types which are selected (types which are active) on the "Config" page.
    """

    # TODO: Check if necessary information is in request object
    if not request.json:
        abort(400)

    node_types = request.get_json()
    session['selected_node_types'] = node_types
    return 'OK'


@app.route("/get-edge-types", methods=["GET"])
def send_edge_types():
    """
    Returns the available edge types for the "Config" page
    """
    return jsonify(session['selected_edge_types'])


@app.route("/get-node-types", methods=["GET"])
def send_node_types():
    """
    Returns the available node types for the "Config" page
    """
    return jsonify(session['selected_node_types'])


def build_selection(types):
    return [(element, True) for element in types]


@app.route("/next-meta-paths/<int:batch_size>", methods=["GET"])
def send_next_metapaths_to_rate(batch_size):
    """
        Returns the next `batchsize` meta-paths to rate.

        Metapaths are formatted like this:
        {'id': 3,
        'metapath': ['Phenotype', 'HAS', 'Association', 'HAS', 'SNP', 'HAS', 'Phenotype'],
        'rating': 0.5}
        """

    next_metapaths, is_last_batch = session['active_learning_algorithm'].get_next(batch_size=batch_size)
    for i in range(len(next_metapaths)):
        next_metapaths[i]['metapath'] = next_metapaths[i]['metapath'].as_list()
    paths = {'meta_paths': next_metapaths,
             'next_batch_available': not is_last_batch}
    if "time" in session.keys():
        session['time_old'] = session['time']
    session['time'] = datetime.datetime.now()
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
    """
    Receives the rated meta-paths.

    Meta-paths are formated like this:
    {'id': 3,
    'metapath': ['Phenotype', 'HAS', 'Association', 'HAS', 'SNP', 'HAS', 'Phenotype'],
    'rating': 0.75}
    """
    time_results_received = datetime.datetime.now()
    # TODO: Check if necessary information is in request object
    if not request.is_json:
        abort(400)
    rated_metapaths = request.get_json()
    session['active_learning_algorithm'].update(rated_metapaths)
    for datapoint in rated_metapaths:
        if not all(key in datapoint for key in ['id', 'metapath', 'rating']):
            abort(400)  # malformed input
    if "time_old" in session.keys():
        rated_metapaths.append({'time_to_rate': (time_results_received - session['time_old']).total_seconds()})
    else:
        if "time" in session.keys():
            rated_metapaths.append({'time_to_rate': (time_results_received - session['time']).total_seconds()})

    return 'OK'


@app.route("/get-similarity-score", methods=["GET"])
def send_similarity_score():
    """
    TODO: Endpoint needs to request similarity score dynamically at SimilarityScore Class
    """
    similarity_score = SimilarityScore()
    return jsonify({'similarity_score': similarity_score.get_similarity_score()})


# Self defined intents
@ask.intent('ChooseDataset')
def choose_dataset(dataset):
    raise NotImplementedError()


@ask.intent('RateMetapath')
def rate_metapath():
    raise NotImplementedError()


@ask.intent('ExcludeEdgeType')
def exclude_edge_type():
    raise NotImplementedError()


@ask.intent('ExcludeNodeType')
def exclude_node_type():
    raise NotImplementedError()


@ask.intent('ShowMoreMetapaths')
def show_more_metapaths():
    raise NotImplementedError()


@ask.intent('ShowResults')
def show_results():
    raise NotImplementedError()

# Built-in intents
@ask.intent('AMAZON.CancelIntent')
def cancel():
    raise NotImplementedError()


@ask.intent('AMAZON.HelpIntent')
def help():
    raise NotImplementedError()


@ask.intent('AMAZON.StopIntent')
def stop():
    raise NotImplementedError()


@ask.intent('AMAZON.MoreIntent')
def more():
    raise NotImplementedError()


@ask.intent('AMAZON.NavigateHomeIntent')
def navigate_home():
    raise NotImplementedError()


@ask.intent('AMAZON.NavigateSettingsIntent')
def navigate_settings():
    raise NotImplementedError()


@ask.intent('AMAZON.NextIntent')
def next():
    raise NotImplementedError()


@ask.intent('AMAZON.PageUpIntent')
def page_up():
    raise NotImplementedError()


@ask.intent('AMAZON.PageDownIntent')
def page_down():
    raise NotImplementedError()


@ask.intent('AMAZON.PreviousIntent')
def previous():
    raise NotImplementedError()


@ask.intent('AMAZON.ScrollRighIntent')
def scroll_right():
    raise NotImplementedError()


@ask.intent('AMAZON.ScrollDownIntent')
def scroll_down():
    raise NotImplementedError()


@ask.intent('AMAZON.ScrollLeftIntent')
def scroll_left():
    raise NotImplementedError()


@ask.intent('AMAZON.ScrollUpIntent')
def scroll_up():
    raise NotImplementedError()


if __name__ == '__main__':
    app.run(port=API_PORT, threaded=True)
