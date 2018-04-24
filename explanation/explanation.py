from typing import List
from util.config import BASELINE_MODE
import numpy as np
from api.neo4j_own import Neo4j
import logging


class Explanation:
	"""
	Computes similar nodes based on both node sets and their occurring meta-paths with belonging
	domain and structural value.
	"""

	@staticmethod
	def get_similar_nodes():
		"""
		:return: Array of dictionaries, that hold a 1-neighborhood query and properties about
				 k-similar nodes regarding both node sets
		TODO: Return similar nodes based on graph embeddings. Build 1-neighborhood query and read property of node
			  dynamically based on Node-ID
		"""
		similar_nodes = [
			{
				"cypher_query": "MATCH (n) RETURN n LIMIT 1",
				"properties": {
					"name": "Node A",
					"label": "Node Type A"
				}
			},
			{
				"cypher_query": "MATCH (n) RETURN n LIMIT 1",
				"properties": {
					"name": "Node B",
					"label": "Node Type B"
				}
			},
			{
				"cypher_query": "MATCH (n) RETURN n LIMIT 1",
				"properties": {
					"name": "Node C",
					"label": "Node Type A"
				}
			},
			{
				"name": "Node D",
				"cypher_query": "MATCH (n) RETURN n LIMIT 1",
				"properties": {
					"name": "Node D",
					"label": "Node Type B"
				}
			}
		]

		return similar_nodes


class SimilarityScore:
	"""
	Computes similarity score between the two node sets.
	Computes contribution of each meta-path to overall similarity score
	"""

	meta_paths = None
	meta_paths_top_k = None
	similarity_score = 0
	algorithm_type = None
	get_complete_rating = None
	dataset = None
	sum_structural_values = 0
	start_node_ids = []
	end_node_ids = []
	similarity_scores = []
	contributing_meta_paths = []
	explained_meta_paths_top_k = []

	def __init__(self, get_complete_rating, dataset, start_node_ids, end_node_ids, algorithm_type=BASELINE_MODE):
		self.algorithm_type = algorithm_type
		self.get_complete_rating = get_complete_rating
		self.dataset = dataset
		self.start_node_ids = start_node_ids
		self.end_node_ids = end_node_ids
		self.logger = logging.getLogger('MetaExp.{}'.format(self.__class__.__name__))

	def __getstate__(self):
		# Copy the object's state from self.__dict__ which contains
		# all our instance attributes.
		d = dict(self.__dict__)
		# Remove the unpicklable entries.
		del d['logger']
		return d

	def __setstate__(self, d):
		self.__dict__.update(d)
		self.logger = logging.getLogger('MetaExp.{}'.format(__class__.__name__))

	def refresh(self):
		self.meta_paths = self.get_complete_rating()

		self.compute_similarity_score()
		self.compute_top_k_contributing_meta_paths(5)
		self.compute_contributing_meta_paths()
		self.logger.debug("CONTRIBUTING METAPATHS!!!!! {}".format(self.contributing_meta_paths))

		return True

	def compute_similarity_score(self):
		"""
		Computes a sum of a linear combination of structural and domain value
		over all meta-paths. First simplified, not experimentally tested baseline.
		:return: similarity score between both node sets as float
		"""
		structural_values = np.array([mp.get_structural_value() for mp in self.meta_paths])
		domain_values = np.array([mp['domain_value'] for mp in self.meta_paths])
		domain_values = self.apply_rescaling(domain_values)
		self.sum_structural_values = np.sum(structural_values)

		self.similarity_scores = structural_values * domain_values

		self.similarity_score = np.sum(self.similarity_scores) / len(self.similarity_scores)

	@staticmethod
	def apply_rescaling(input_array):
		min_value = np.amin(input_array)
		max_value = np.amax(input_array)
		range_of_values = max_value - min_value
		input_array = input_array + range_of_values

		return input_array

	@staticmethod
	def apply_soft_max(input_array: List[float]) -> List[float]:
		return np.exp(input_array) / np.sum(np.exp(input_array))

	@staticmethod
	def apply_low_pass_filtering(input_array: List[float], filter_rate: int) -> List[float]:
		return np.argsort(input_array)[-filter_rate:]

	def get_normalized_structural_value(self, structural_value: float) -> List[float]:
		return structural_value / self.sum_structural_values

	def compute_top_k_contributing_meta_paths(self, k: int):
		self.similarity_scores = self.apply_soft_max(self.similarity_scores)
		meta_paths_top_k_idx = np.argsort(self.similarity_scores)[-k:]
		self.explained_meta_paths_top_k = []
		for i in meta_paths_top_k_idx:
			self.meta_paths[i]['similarity_score'] = self.similarity_scores[i]
			self.explained_meta_paths_top_k.append(self.meta_paths[i])

	def construct_query(self, query_mp, node_type_count, limit):
		start_ids = '[' + ','.join(map(str, self.start_node_ids)) + ']'
		end_ids = '[' + ','.join(map(str, self.end_node_ids)) + ']'
		return "MATCH p = {} " \
				"WHERE ID(n0) in {} and ID(n{}) in {} " \
				"RETURN p LIMIT {}".format(query_mp, start_ids, node_type_count - 1, end_ids, limit)

	def compute_contributing_meta_paths(self):
		self.contributing_meta_paths = []

		for i, mp in enumerate(self.explained_meta_paths_top_k):
			mp_info = {
				'id': mp['id'],
				'label': "Meta-Path " + str(mp['id']),
				'value': round(mp['similarity_score'] * 100, 2),
				'color': 'hsl({}, 70%, 50%)'.format(np.random.rand() * 255),
				'similarity_score': mp['similarity_score'],
				'structural_value': int(mp['structural_value']),
				'metapath': mp['metapath'].get_representation('UI'),
				'instance_query': self.construct_query(mp['metapath'].get_representation('UI'),
													   mp['metapath'].number_node_types(), 5)
			}
			self.contributing_meta_paths.append(mp_info)

		contribution_ranking_idx = np.argsort(np.array([mp['similarity_score'] for mp in self.contributing_meta_paths]))[::-1]

		for i in contribution_ranking_idx:
			rank, = np.where(contribution_ranking_idx == i)
			rank = int(rank[0] + 1)
			self.contributing_meta_paths[i]['contribution_ranking'] = rank

		contrib_mp_sim_score_sum = np.sum(np.array([mp['similarity_score'] for mp in self.contributing_meta_paths]))
		other_mp_sim_score = 1.0 - contrib_mp_sim_score_sum

		contrib_mp_struct_sum = np.sum(np.array([mp.get_structural_value() for mp in self.contributing_meta_paths]))
		top_k_mp_struct_sum = np.sum(np.array([mp.get_structural_value() for mp in self.meta_paths]))
		other_mp_struct_score = top_k_mp_struct_sum - contrib_mp_struct_sum

		other_mps_info = {
			'id': 0,
			'label': "Others",
			'value': int(other_mp_sim_score * 100),
			'color': 'hsl({}, 70%, 50%)'.format(np.random.rand() * 255),
			'similarity_score': other_mp_sim_score,
			'structural_value': int(other_mp_struct_score),
			'metapath': 'Seen on Explore Page',
			'instance_query': 'RETURN 1',
			'contribution_ranking': 0
		}

		self.contributing_meta_paths = [other_mps_info] + self.contributing_meta_paths

	def get_similarity_score(self) -> float:
		"""
		:return: similarity score between both node sets as float
		"""

		return round(self.similarity_score, 2)

	def get_contributing_meta_path_by_id(self, meta_path_id: int):
		meta_path = None

		for mp in self.contributing_meta_paths:
			if mp['id'] == meta_path_id:
				meta_path = mp
				break

		return meta_path

	def get_contributing_meta_path(self, meta_path_id: int) -> dict:
		"""
		:param meta_path_id: Integer, that is a unique identifier for a meta-path
		:return: Dictionary, that holds detailed information about the belonging meta-path
		TODO: Take structural value depending on given meta_path. Compute contribution information dynamically
		"""
		meta_path = self.get_contributing_meta_path_by_id(meta_path_id)
		meta_path_info = {
			"id": meta_path['id'],
			"name": "Meta-Path " + str(meta_path['id']),
			"structural_value": meta_path['structural_value'],
			"contribution_ranking": meta_path['contribution_ranking'],
			"contribution_value": round(meta_path['similarity_score']*100, 2),
			"meta_path": meta_path['metapath'],
			"instance_query": meta_path['instance_query']
		}

		return meta_path_info

	def get_contributing_meta_paths(self) -> List[dict]:
		"""
		:return: List of dictionaries, that hold necessary information for a pie chart visualization
				 about k-most contributing meta-paths to overall similarity score
		"""

		return self.contributing_meta_paths[::-1]
