from Orange.data import Table
from Orange.base import Model
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.concurrent import TaskState, ConcurrentWidgetMixin
from Orange.widgets.widget import Msg
from Orange.widgets import gui
from Orange.widgets.settings import Setting

from AnyQt.QtWidgets import QFormLayout, QLabel
from AnyQt.QtCore import Qt

from orangecontrib.explain.modeling.scoringsheet import ScoringSheetLearner

class ScoringSheetRunner:
    @staticmethod
    def run(
        learner: ScoringSheetLearner, data: Table, state: TaskState
    ) -> Model:
        if data is None:
            return None
        state.set_status("Learning...")
        model = learner(data)
        return model


class OWScoringSheet(OWBaseLearner, ConcurrentWidgetMixin):
    name = 'Scoring Sheet'
    description = "A fast and explainable classifier."
    # icon = "icons/ScoringSheet.svg"
    # priority = 90

    LEARNER = ScoringSheetLearner

    class Inputs(OWBaseLearner.Inputs):
        pass

    class Outputs(OWBaseLearner.Outputs):
        pass

    class Information(OWBaseLearner.Information):
        ignored_preprocessors = Msg(
            "This widget has a very specific preprocessing which could be affected by the inputed preprocessor. "
        )


    # Preprocessing
    num_attr_after_selection = Setting(20)

    # Scoring Sheet Settings
    num_decision_params = Setting(5)
    max_points_per_param = Setting(5)
    custom_features_checkbox = Setting(False)
    num_input_features = Setting(1)

    # Warning messages
    class Information(OWBaseLearner.Information):
        custom_number_of_input_features_used = Msg(
            "If the number of input features used is too low for the number of decision parameters, \n"
            "the number of decision parameters will be adjusted to fit the model.")

    def __init__(self):
        ConcurrentWidgetMixin.__init__(self)
        OWBaseLearner.__init__(self)

    def add_main_layout(self):
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)

        gui.widgetBox(self.controlArea, True, orientation=form)

        form.addRow(
            QLabel(
                "<span style='font-weight:bold;'>"
                "Preprocessing"
                "</span>"
            )
        )

        form.addRow(
            "Number of Attributes After Feature Selection:",
            gui.spin(
                None,
                self,
                "num_attr_after_selection",
                minv=1,
                maxv=100,
                step=1,
                orientation=Qt.Horizontal,
                alignment=Qt.AlignRight,
                callback=self.settings_changed,
            ),
        )

        form.addRow(
            QLabel(
                "<span style='font-weight:bold;'>"
                "Model Parameters"
                "</span>"
            )
        )

        form.addRow(
            "Maximum Number of Decision Parameters:",
            gui.spin(
                None,
                self,
                "num_decision_params",
                minv=1,
                maxv=50,
                step=1,
                orientation=Qt.Horizontal,
                alignment=Qt.AlignRight,
                callback=self.settings_changed,
            ),
        )

        form.addRow(
            "Maximum Points per Decision Parameter:",
            gui.spin(
                None,
                self,
                "max_points_per_param",
                minv=1,
                maxv=100,
                step=1,
                orientation=Qt.Horizontal,
                alignment=Qt.AlignRight,
                callback=self.settings_changed,
            ),
        )

        form.addRow(
            gui.checkBox(
                None,
                self,
                "custom_features_checkbox",
                label="Custom number of input features",
                callback=[self.settings_changed, self.custom_input_features]
            ),
        )

        self.custom_features_label = QLabel("Number of Input Features Used:")
        self.custom_features = gui.spin(
                None,
                self,
                "num_input_features",
                minv=1,
                maxv=50,
                step=1,
                orientation=Qt.Horizontal,
                alignment=Qt.AlignRight,
                callback=self.settings_changed,
        )

        form.addRow(self.custom_features_label, self.custom_features)
        self.custom_input_features()


    def custom_input_features(self):
        """
        Enable or disable the custom input features spinbox based on the value of the custom_features_checkbox.
        Also, add or remove the Information message about the number of input features.
        """
        self.custom_features.setEnabled(self.custom_features_checkbox)
        if self.custom_features_checkbox:
            self.Information.custom_number_of_input_features_used()
        else:
            self.Information.custom_number_of_input_features_used.clear()
        self.apply()


    @Inputs.data
    def set_data(self, data):
        self.cancel()
        super().set_data(data)

    @Inputs.preprocessor
    def set_preprocessor(self, preprocessor):
        self.cancel()
        super().set_preprocessor(preprocessor)

    def create_learner(self):
        return self.LEARNER(
            num_attr_after_selection=self.num_attr_after_selection,
            num_decision_params=self.num_decision_params,
            max_points_per_param=self.max_points_per_param,
            num_input_features=self.num_input_features if self.custom_features_checkbox else None,
        )
    
    def update_model(self):
        self.cancel()
        self.show_fitting_failed(None)
        self.model = None
        if self.data is not None:
            self.start(ScoringSheetRunner.run, self.learner, self.data)
        else:
            self.Outputs.model.send(None)
    
    def get_learner_parameters(self):
        return (
            self.num_decision_params,
            self.max_points_per_param,
            self.num_input_features,
        )
    
    def on_partial_result(self, _):
        pass

    def on_done(self, result: Model):
        assert isinstance(result, Model) or result is None
        self.model = result
        self.Outputs.model.send(result)

    def on_exception(self, ex):
        self.cancel()
        self.Outputs.model.send(None)
        if isinstance(ex, BaseException):
            self.show_fitting_failed(ex)

    def onDeleteWidget(self):
        self.shutdown()
        super().onDeleteWidget()


if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(OWScoringSheet).run()