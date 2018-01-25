import unittest
from domain_scoring.domain_scoring import DomainScoring
from util.ranking_graph import RankingGraph
from util.datastructures import MetaPath

class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.ds = DomainScoring()

        self.ranking_graph = RankingGraph()
        self.ranking_graph.transitive_closures = lambda: [["A", "B", "C"], ["B", "C"]]
        self.ranking_graph.all_nodes = lambda: ["A", "B", "C"]

    def test_all_pairs(self):
        list = [1, 2, 3]
        all_pairs = [(1, 2), (1, 3), (2, 3)]
        all_pairs_inverse = [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]


        self.assertEqual(all_pairs, self.ds._all_pairs(list))
        self.assertEqual(all_pairs_inverse, self.ds._all_pairs(list, True))

    def test_extract_features_labels(self):


        self.assertEqual(
            ([("A", "B"), ("B", "A"), ("A", "C"), ("C", "A"), ("B", "C"), ("C", "B")], [0, 1, 0, 1, 0, 1]),
            self.ds._extract_features_labels(self.ranking_graph))

    def test_fit_vectorizer(self):
        self.assertIsNone(self.ds._fit_vectorizer(self.ranking_graph))


    def test_preprocess(self):
        expected = [[0, 0, 1, 1, 0, 0]]

        metapaths = [
            MetaPath(["C"]),
            MetaPath(["A"])
        ]

        metapaths_tuples = [(metapaths[0], metapaths[1])]

        self.ds._fit_vectorizer(self.ranking_graph)
        self.assertEqual(expected, self.ds._preprocess(metapaths_tuples))

    def test_fit(self):
        self.assertIsNone(self.ds.fit(self.ranking_graph))



if __name__ == '__main__':
    unittest.main()
