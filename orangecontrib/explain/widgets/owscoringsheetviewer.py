from Orange.widgets import gui
from Orange.widgets.settings import ContextSetting
from Orange.widgets.widget import Input, Output, OWWidget, AttributeList, Msg
from Orange.data import Table
from Orange.classification import Model

from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QSlider, QLabel,
    QVBoxLayout, QWidget, QHBoxLayout, QGridLayout
)
from PyQt5.QtCore import Qt

from orangecontrib.explain.modeling.scoringsheet import ScoringSheetModel

from fasterrisk.utils import get_support_indices, get_all_product_booleans

import numpy as np





class ScoringSheetTable(QTableWidget):

    def __init__(self, main_widget, parent=None):
        """
        Initialize the ScoringSheetTable. It sets the column headers and connects the itemChanged signal
        to the handle_item_changed method.
        """
        super().__init__(parent)
        self.main_widget = main_widget
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['Attribute Name', 'Attribute Points', 'Selected', 'Collected Points'])
        self.itemChanged.connect(self.handle_item_changed)

    def populate_table(self, attributes, coefficients):
        """
        Populates the table with the given attributes and coefficients. It creates a row for each attribute and
        populates the first two columns with the attribute name and coefficient respectively. The third column
        contains a checkbox that allows the user to select the attribute. The fourth column contains the points
        collected for the attribute. Initially, the fourth column is set to 0 for all attributes.
        """
        self.setRowCount(len(attributes))
        for i, (attr, coef) in enumerate(zip(attributes, coefficients)):
            self.setItem(i, 0, QTableWidgetItem(attr))
            self.setItem(i, 1, QTableWidgetItem(str(coef)))

            checkbox = QTableWidgetItem()
            checkbox.setCheckState(Qt.Unchecked)
            self.setItem(i, 2, checkbox)

            self.setItem(i, 3, QTableWidgetItem('0'))

    def handle_item_changed(self, item):
        """
        Handles the change in the state of the checkbox. If the checkbox is checked, the points collected for the
        corresponding attribute is set to the coefficient. If the checkbox is unchecked, the points collected for
        the corresponding attribute is set to 0. It also updates the slider value.
        """
        if item.column() == 2:
            self.blockSignals(True)
            row = item.row()
            if item.checkState() == Qt.Checked:
                self.setItem(row, 3, QTableWidgetItem(self.item(row, 1).text()))
            else:
                self.setItem(row, 3, QTableWidgetItem('0'))
            self.blockSignals(False)
            self.main_widget._update_slider_value()





class RiskSlider(QWidget):
    def __init__(self, points, probabilities, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        # Container for the point labels above the slider
        self.points_container = QWidget(self)
        self.points_layout = QHBoxLayout(self.points_container)
        self.layout.addWidget(self.points_container)

        # Container for the point and probability labels
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setEnabled(False)
        self.layout.addWidget(self.slider)

        # Container for probability labels under the slider
        self.probabilities_container = QWidget(self)
        self.prob_layout = QHBoxLayout(self.probabilities_container)
        self.layout.addWidget(self.probabilities_container)
        
        self.setLayout(self.layout)

        self.points = points
        self.probabilities = probabilities
        self.setup_slider()

    def setup_slider(self):
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(self.points) - 1 if self.points else 0)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setTickInterval(1)  # Set tick interval

        # Clear existing widgets in the points layout
        for i in reversed(range(self.points_layout.count())):
            widget = self.points_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add point labels above the slider for each point
        for i, point in enumerate(self.points):
            label = QLabel(str(point) if self.points else "")
            label.setAlignment(Qt.AlignCenter)
            self.points_layout.addWidget(label)
            if i != len(self.points) - 1:
                self.points_layout.addStretch()


        # Clear existing widgets in the probabilities layout
        for i in reversed(range(self.prob_layout.count())): 
            widget = self.prob_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add probability labels under the slider for each point
        for i, point in enumerate(self.points):
            label = QLabel(str(round(self.probabilities[i], 1)) + "%" if self.probabilities else "")
            label.setAlignment(Qt.AlignCenter)
            self.prob_layout.addWidget(label)
            if i != len(self.points) - 1:
                self.prob_layout.addStretch()  # Add stretch between labels to space them out

    def move_to_value(self, value):
        """
        Moves the slider to the position representing the closest point to the given value. If there are no points,
        the method simply returns without making any changes.
        """
        if not self.points:
            return
        closest_point_index = min(range(len(self.points)), key=lambda i: abs(self.points[i]-value))
        self.slider.setValue(closest_point_index)





class OWScoringSheetViewer(OWWidget):
    """
    Allows visualization of the scoring sheet model.
    """
    name = "Scoring Sheet Viewer"
    description = "Visualize the scoring sheet model."
    # icon = "icons/ScoringSheetViewer.svg"
    # priority = 90

    class Inputs:
        classifier = Input("Classifier", Model)
        data = Input("Data", Table)

    class Outputs:
        features = Output("Features", AttributeList)

    target_class_index = ContextSetting(0)
    class Error(OWWidget.Error):
        invalid_classifier = Msg("Scoring Sheet Viewer only accepts a Scoring Sheet model.")

    def __init__(self):
        super().__init__()
        self.data = None
        self.classifier = None
        self.coefficients = None
        self.attributes = None
        self.all_scores = None
        self.all_risks = None
        self.domain = None
        self.old_target_class_index = self.target_class_index

        # Control Area Layout
        grid = QGridLayout()
        self.class_combo = gui.comboBox(
            None, self, "target_class_index", callback=self._class_combo_changed
        )
        grid.addWidget(QLabel("Target class:"), 0, 0)
        grid.addWidget(self.class_combo, 0, 1)
        gui.widgetBox(self.controlArea, orientation=grid)
        self.controlArea.layout().addStretch()

        # Main Area Layout
        self.coefficient_table = ScoringSheetTable(main_widget=self, parent=self)
        gui.widgetBox(self.mainArea).layout().addWidget(self.coefficient_table)

        self.risk_slider = RiskSlider([], [], self)
        gui.widgetBox(self.mainArea).layout().addWidget(self.risk_slider)


    # GUI Methods -------------------------------------------------------------------------------------

    def _populate_interface(self):
        """Populate the scoring sheet based on extracted data."""
        if self.attributes and self.coefficients:
            self.coefficient_table.populate_table(self.attributes, self.coefficients)
            
            # Update points and probabilities in the custom slider
            self.risk_slider.points = self.all_scores
            self.risk_slider.probabilities = self.all_risks
            self.risk_slider.setup_slider()

    def _update_slider_value(self):
        """
        This method is called when the user changes the state of the checkbox in the coefficient table.
        It updates the slider value to reflect the total points collected.
        """
        if not self.coefficient_table:
            return
        total_coefficient = sum(
            float(self.coefficient_table.item(row, 3).text()) 
            for row in range(self.coefficient_table.rowCount())
            if self.coefficient_table.item(row, 3)  # Check if the item exists
        )
        self.risk_slider.move_to_value(total_coefficient)

    def _update_controls(self):
        """
        This method is called when the user changes the classifier or the target class.
        It updates the interface components based on the extracted data.
        """
        self._populate_interface()
        self._update_slider_value()
        self.class_combo.clear()
        if self.domain is not None:
            values = self.domain.class_vars[0].values
            if values:
                self.class_combo.addItems(values)
                self.class_combo.setCurrentIndex(self.target_class_index)


    def _class_combo_changed(self):
        """
        This method is called when the user changes the target class.
        It updates the interface components based on the selected class.
        """
        self.target_class_index = self.class_combo.currentIndex()
        if self.target_class_index == self.old_target_class_index:
            return
        self.old_target_class_index = self.target_class_index
        self._adjust_for_target_class()
        self._update_controls()
    

    def _adjust_for_target_class(self):
        """
        Adjusts the coefficients, scores, and risks for the negative/positive class.
        This allows user to select the target class and see the corresponding coefficients, scores, and risks.
        """
        # Negate the coefficients
        self.coefficients = [-coef for coef in self.coefficients]
        # Negate the scores
        self.all_scores = [-score for score in self.all_scores]
        self.all_scores.sort()
        # Adjust the risks
        self.all_risks = [100 - risk for risk in self.all_risks]
        self.all_risks.sort()


    # Input Methods -----------------------------------------------------------------------------------


    def _extract_data_from_model(self, classifier):
        """
        Extracts the attributes, non-zero coefficients, all possible 
        scores, and corresponding probabilities from the model.
        """
        model = classifier.model

        # 1. Extracting attributes and non-zero coefficients
        nonzero_indices = get_support_indices(model.coefficients)
        attributes = [model.featureNames[i] for i in nonzero_indices]
        coefficients = [int(model.coefficients[i]) for i in nonzero_indices]
        
        # 2. Extracting possible points and corresponding probabilities
        len_nonzero_indices = len(nonzero_indices)
        # If we have less than 10 attributes, we can calculate all the possible combinations of scores.
        if len_nonzero_indices <= 10:
            all_product_booleans = get_all_product_booleans(len_nonzero_indices)
            all_scores = all_product_booleans.dot(model.coefficients[nonzero_indices])
            all_scores = np.unique(all_scores)
        # If there are more than 10 non-zero coefficients, calculating all possible combinations of scores 
        # might be computationally intensive. Instead, the method calculates all possible scores from the 
        # training dataset (X_train) and then picks some quantile points (in this case, a maximum of 20) to represent the possible scores.
        else:
            all_scores = model.X_train.dot(model.coefficients)
            all_scores = np.unique(all_scores)
            quantile_len = min(20, len(all_scores))
            quantile_points = np.asarray(range(1, 1+quantile_len)) / quantile_len
            all_scores = np.quantile(all_scores, quantile_points, method = "closest_observation")

        all_scaled_scores = (model.intercept + all_scores) / model.multiplier
        all_risks = 1 / (1 + np.exp(-all_scaled_scores))
        
        self.attributes = attributes
        self.coefficients = coefficients
        self.all_scores = all_scores.tolist()
        self.all_risks = (all_risks * 100).tolist()
        self.domain = classifier.domain

    def _is_valid_classifier(self, classifier):
        """Check if the classifier is a valid ScoringSheetModel."""
        if not isinstance(classifier, ScoringSheetModel):
            self.Error.invalid_classifier()
            return False
        return True

    def _clear_classifier_data(self):
        """Clear classifier data and associated interface components."""
        self.coefficients = None
        self.attributes = None
        self.all_scores = None
        self.all_risks = None
        self.classifier = None
        self.Outputs.features.send(None)


    @Inputs.classifier
    def set_classifier(self, classifier):
        if not classifier or not self._is_valid_classifier(classifier):
            self._clear_classifier_data()
            return

        self.classifier = classifier
        self._extract_data_from_model(classifier)
        self._update_controls()

    @Inputs.data #TODO: make this better
    def set_data(self, data):
        # self.closeContext()
        self.data = data
        self.Outputs.features.send(None)


if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    from Orange.data import Table
    from orangecontrib.explain.modeling.scoringsheet import ScoringSheetLearner
    data = Table("heart_disease")
    learner = ScoringSheetLearner(20, 5, 5, None)
    model = learner(data)
    WidgetPreview(OWScoringSheetViewer).run(set_classifier = model)

        
        

        