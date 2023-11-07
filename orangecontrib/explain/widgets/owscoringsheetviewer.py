from Orange.widgets import gui
from Orange.widgets.settings import ContextSetting
from Orange.widgets.widget import Input, Output, OWWidget, AttributeList, Msg
from Orange.data import Table
from Orange.classification import Model
from PyQt5 import QtGui

from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QSlider, QLabel, QVBoxLayout,
    QHBoxLayout, QWidget, QGridLayout, QStyle, QToolTip, QStyleOptionSlider
)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QFontMetrics

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
        
        # Resize columns to fit the contents
        self.resize_columns_to_contents()

    def resize_columns_to_contents(self):
        """
        Resize each column to fit the content.
        """
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)

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
        self.layout = QHBoxLayout(self)

        # Set the margins for the layout
        self.leftMargin = 20
        self.topMargin = 20
        self.rightMargin = 20
        self.bottomMargin = 20
        self.layout.setContentsMargins(self.leftMargin, self.topMargin, self.rightMargin, self.bottomMargin)

        # Setup the labels
        self.setup_labels()

        # Create the slider
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setEnabled(False)
        self.layout.addWidget(self.slider)

        self.points = points
        self.probabilities = probabilities
        self.setup_slider()

        # Set the margin for drawing text
        self.textMargin = 1

        # This is needed to show the tooltip when the mouse is over the slider thumb
        self.slider.installEventFilter(self)
        self.setMouseTracking(True)
        self.target_class = None

    def setup_labels(self):
        """
        Set up the labels for the slider. 
        It creates a vertical layout for the labels and adds it to the main layout.
        It is only called once when the widget is initialized.
        """
        # Create the labels for the slider
        self.label_layout = QVBoxLayout()
        # Add the label for the points "Points:"
        self.points_label = QLabel("<b>Total:</b>")
        self.label_layout.addWidget(self.points_label)
        # Add stretch to the label layout
        self.label_layout.addSpacing(23)
        # Add the label for the probability "Probability:"
        self.probability_label = QLabel("<b>Probabilities (%):</b>")
        self.label_layout.addWidget(self.probability_label)
        self.layout.addLayout(self.label_layout)
        # Add a spacer
        self.layout.addSpacing(28)

    def setup_slider(self):
        """
        Set up the slider with the given points and probabilities. 
        It sets the minimum and maximum values (of the indexes for the ticks) of the slider.
        It is called when the points and probabilities are updated.
        """
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(self.points) - 1 if self.points else 0)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setTickInterval(1)  # Set tick interval

    def move_to_value(self, value):
        """
        Move the slider to the closest tick mark to the given value.
        """
        if not self.points:
            return
        closest_point_index = min(range(len(self.points)), key=lambda i: abs(self.points[i]-value))
        self.slider.setValue(closest_point_index)

    def paintEvent(self, event):
        """
        Paint the point and probabilitie labels above and below the tick marks respectively.
        """
        super().paintEvent(event)

        if not self.points:
            return

        painter = QPainter(self)
        fm = QFontMetrics(painter.font())

        for i, point in enumerate(self.points):
            # Calculate the x position of the tick mark
            x_pos = QStyle.sliderPositionFromValue(self.slider.minimum(),
                                                self.slider.maximum(), i, 
                                                self.slider.width()) + self.slider.x()

            # Draw the point label above the tick mark
            point_str = str(point)
            point_rect = fm.boundingRect(point_str)
            point_x = int(x_pos - point_rect.width() / 2)
            point_y = int(self.slider.y() - self.textMargin - point_rect.height())
            painter.drawText(QRect(point_x, point_y, point_rect.width(), point_rect.height()), Qt.AlignCenter, point_str)

            # Draw the probability label below the tick mark
            prob_str = str(round(self.probabilities[i], 1)) + "%"
            prob_rect = fm.boundingRect(prob_str)
            prob_x = int(x_pos - prob_rect.width() / 2)
            prob_y = int(self.slider.y() + self.slider.height() + self.textMargin)
            painter.drawText(QRect(prob_x, prob_y, prob_rect.width(), prob_rect.height()), Qt.AlignCenter, prob_str)

        painter.end()

    def eventFilter(self, watched, event):
        """
        Event filter to intercept hover events on the slider.
        This is needed to show the tooltip when the mouse is over the slider thumb.
        """
        if watched == self.slider and isinstance(event, QtGui.QHoverEvent):
            # Handle the hover event when it's over the slider
            self.handle_hover_event(event.pos())
            return True
        else:
            # Call the base class method to continue default event processing
            return super().eventFilter(watched, event)

    def handle_hover_event(self, pos):
        """
        Handle hover events for the slider. Display the tooltip when the mouse is over the slider thumb.
        """
        thumbRect = self.get_thumb_rect()  # This is a method from QSlider that gives you the thumb rect
        if thumbRect.contains(pos):
            value = self.slider.value()
            points = self.points[value]
            probability = self.probabilities[value]
            tooltip = str(
                f"<b>Target Class: {self.target_class}</b>\n "
                f"<hr style='margin: 0px; padding: 0px; border: 0px; height: 1px; background-color: #000000'>"
                f"<b>Points:</b> {int(points)}<br>"
                f"<b>Probability:</b> {probability:.1f}%"
            )
            QToolTip.showText(self.slider.mapToGlobal(pos), tooltip)
        else:
            QToolTip.hideText()


    def get_thumb_rect(self):
        """
        Get the rectangle of the slider thumb.
        """
        opt = QStyleOptionSlider()
        self.slider.initStyleOption(opt)

        style = self.slider.style()

        # Get the area of the slider that contains the handle
        handle_rect = style.subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self.slider)

        # Calculate the position and size of the thumb
        thumb_x = handle_rect.x()
        thumb_y = handle_rect.y()
        thumb_width = handle_rect.width()
        thumb_height = handle_rect.height()

        return QRect(thumb_x, thumb_y, thumb_width, thumb_height)




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
            self.risk_slider.target_class = f"{self.domain.class_vars[0].name} = {self.domain.class_vars[0].values[self.target_class_index]}"
            self.risk_slider.setup_slider()
            self.risk_slider.update()

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
        self.all_scores = [-score if score != 0 else score for score in self.all_scores]
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