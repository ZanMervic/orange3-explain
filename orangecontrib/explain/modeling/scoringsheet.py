import numpy as np
from fasterrisk.fasterrisk import RiskScoreOptimizer, RiskScoreClassifier

from Orange.base import Learner, Model
from Orange.data import Table, Storage
from Orange.preprocess import Discretize, Impute, Continuize, SelectBestFeatures
from Orange.preprocess.discretize import Binning
from Orange.preprocess.score import ReliefF


def _change_class_var_values(y):
        """
        Changes the class variable values from 0 and 1 to -1 and 1 or vice versa.
        """
        return np.where(y == 0, -1, np.where(y == -1, 0, y))


class ScoringSheetModel(Model):
    def __init__(self, model):
        self.model = model
        super().__init__()

    def predict_storage(self, table):
        if not isinstance(table, Storage):
            raise TypeError("Data is not a subclass of Orange.data.Storage.")

        y_pred = _change_class_var_values(self.model.predict(table.X))
        y_prob = self.model.predict_prob(table.X)

        scores = np.hstack(((1-y_prob).reshape(-1,1), y_prob.reshape(-1,1)))
        return y_pred, scores




class ScoringSheetLearner(Learner):

    __returns__ = ScoringSheetModel

    preprocessors = [Discretize(method=Binning()), Impute(), Continuize(), SelectBestFeatures(method=ReliefF(), k=20)]
    feature_to_group = None
    def __init__(self, num_attr_after_selection, num_decision_params, max_points_per_param, num_input_features):
        self.num_attr_after_selection = num_attr_after_selection
        self.num_decision_params = num_decision_params
        self.max_points_per_param = max_points_per_param
        self.num_input_features = num_input_features
        super().__init__()

    def fit_storage(self, table):
        if not isinstance(table, Storage):
            raise TypeError("Data is not a subclass of Orange.data.Storage.")
        
        if self.num_input_features is not None:
            self._generate_feature_group_index(table)
        
        X, y, w = table.X, table.Y, table.W if table.has_weights() else None
        learner = RiskScoreOptimizer(
            X=X,
            y=_change_class_var_values(y),
            k=self.num_decision_params,
            select_top_m=1,
            lb=-self.max_points_per_param,
            ub=self.max_points_per_param,
            group_sparsity = self.num_input_features,
            featureIndex_to_groupIndex = self.feature_to_group,
        )
        learner.optimize()
        multipliers, intercepts, coefficients = learner.get_models()

        model = RiskScoreClassifier(
            multiplier=multipliers[0],
            intercept=intercepts[0],
            coefficients=coefficients[0],
            featureNames=[attribute.name for attribute in table.domain.attributes]
        )

        return ScoringSheetModel(model)




    def _generate_feature_group_index(self, table):
        """
        Returns a feature index to group index mapping. The group index is used to group binarized features
        that belong to the same original feature.
        """
        original_feature_names = [attribute.compute_value.variable.name for attribute in table.domain.attributes]
        feature_to_group_index = {feature: idx for idx, feature in enumerate(set(original_feature_names))}
        feature_to_group = [feature_to_group_index[feature] for feature in original_feature_names]
        self.feature_to_group = feature_to_group


if __name__ == "__main__":
    learner = ScoringSheetLearner(20, 5, 10, None)
    # table = Table("https://datasets.biolab.si/core/adult.tab")s
    table = Table("https://datasets.biolab.si/core/heart_disease.tab")
    model = learner(table)
    model(table)