import unittest


from AnyQt.QtCore import Qt

from orangewidget.tests.base import WidgetTest

from Orange.data import Table
from Orange.widgets.widget import AttributeList

from orangecontrib.explain.modeling.scoringsheet import ScoringSheetLearner
from orangecontrib.explain.widgets.owscoringsheetviewer import OWScoringSheetViewer


class TestOWScoringSheetViewer(WidgetTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.heart = Table("heart_disease")
        cls.scoring_sheet_learner = ScoringSheetLearner(20, 5, 5, None)
        cls.scoring_sheet_model = cls.scoring_sheet_learner(cls.heart)

    def setUp(self):
        self.widget = self.create_widget(OWScoringSheetViewer)

    def test_no_classifier_input(self):
        coef_table = self.widget.coefficient_table
        risk_slider = self.widget.risk_slider
        class_combo = self.widget.class_combo

        self.assertEqual(coef_table.rowCount(), 0)
        self.assertEqual(risk_slider.slider.value(), 0)
        self.assertEqual(class_combo.count(), 0)

    # def test_no_classifier_output(self):
    #     self.assertIsNone(self.get_output(self.widget.Outputs.features))

    def test_classifier_output(self):
        self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)
        output = self.get_output(self.widget.Outputs.features)
        self.assertIsInstance(output, AttributeList)
        self.assertEqual(len(output), self.scoring_sheet_model.num_decision_params)

    def test_table_population_on_model_input(self):
        self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)
        table = self.widget.coefficient_table
        self.assertEqual(table.rowCount(), self.scoring_sheet_learner.num_decision_params)

        for column in range(table.columnCount()):
            for row in range(table.rowCount()):
                self.assertIsNotNone(table.item(row, column))

    def test_slider_population_on_model_input(self):
        self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)
        slider = self.widget.risk_slider
        self.assertIsNotNone(slider.points)
        self.assertIsNotNone(slider.probabilities)
        self.assertEqual(len(slider.points), len(slider.probabilities))

    def test_collected_points_update_on_checkbox_toggle(self):
        self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)
        coef_table = self.widget.coefficient_table
        
        # Get the items in the first row of the table
        checkbox_item = coef_table.item(0, 2)
        collected_points_item = coef_table.item(0, 3)
        attribute_points_item = coef_table.item(0, 1)

        # Check if the "Collected Points" value is "0" before changing the checkbox
        self.assertEqual(collected_points_item.text(), "0")

        # Directly change the checkbox state to Checked
        checkbox_item.setCheckState(Qt.Checked)

        # Re-fetch the items (because the old item was replaced by a new one)
        collected_points_item = coef_table.item(0, 3)

        # Check if the "Collected Points" value for that attribute is now the same as its coefficient
        self.assertEqual(collected_points_item.text(), attribute_points_item.text())

        # Directly change the checkbox state to Unchecked
        checkbox_item.setCheckState(Qt.Unchecked)

        # Re-fetch the items again
        collected_points_item = coef_table.item(0, 3)

        # Check if the "Collected Points" value is "0" again
        self.assertEqual(collected_points_item.text(), "0")


    def test_slider_update_on_checkbox_toggle(self):
        self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)

        coef_table = self.widget.coefficient_table
        risk_slider = self.widget.risk_slider
        risk_slider_points = risk_slider.points

        # Get the items in the first row of the table
        checkbox_item = coef_table.item(0, 2)
        attribute_points_item = coef_table.item(0, 1)

        # Check if the slider value is "0" before changing the checkbox
        self.assertEqual(risk_slider.slider.value(), risk_slider_points.index(0))

        # Directly change the checkbox state to Checked
        checkbox_item.setCheckState(Qt.Checked)

        # Re-fetch the items after change
        attribute_points_item = coef_table.item(0, 1)

        # Check if the slider value is now the same as the attribute's coefficient
        self.assertEqual(risk_slider.slider.value(), risk_slider_points.index(float(attribute_points_item.text())))

        # Directly change the checkbox state to Unchecked
        checkbox_item.setCheckState(Qt.Unchecked)

        # Check if the slider value is "0" again
        self.assertEqual(risk_slider.slider.value(), risk_slider_points.index(0))

    def test_target_class_change(self):
        self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)
        self.class_combo = self.widget.class_combo

        # Check if the values of the combobox "match" the domain
        self.assertEqual(self.class_combo.count(), len(self.scoring_sheet_model.domain.class_var.values))
        for i in range(self.class_combo.count()):
            self.assertEqual(self.class_combo.itemText(i), self.scoring_sheet_model.domain.class_var.values[i])

        old_coefficients = self.widget.coefficients.copy()
        old_all_scores = self.widget.all_scores.copy()
        old_all_risks = self.widget.all_risks.copy()

        # Change the target class to the second class
        self.class_combo.setCurrentIndex(1)
        self.widget._class_combo_changed()

        # Check if the coefficients, scores, and risks have changed
        self.assertNotEqual(old_coefficients, self.widget.coefficients)
        self.assertNotEqual(old_all_scores, self.widget.all_scores)
        self.assertNotEqual(old_all_risks, self.widget.all_risks)



    # def test_collected_points_update_on_checkbox_toggle_gui(self):
    #     self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)
    #     self.wait_until_finished()
    #     coef_table = self.widget.coefficient_table
        
    #     # Get the items in the first row of the table
    #     checkbox_item = coef_table.item(0, 2)

    #     # Simulate checking the checkbox in the first row using GUI interaction
    #     QTest.mouseClick(coef_table.viewport(), Qt.LeftButton, pos=coef_table.visualItemRect(checkbox_item).center())
        
    #     # Re-fetch the items after interaction
    #     collected_points_item = coef_table.item(0, 3)
    #     attribute_points_item = coef_table.item(0, 1)

    #     # Check if the "Collected Points" value for that attribute is now the same as its coefficient
    #     self.assertEqual(collected_points_item.text(), attribute_points_item.text())

    #     # Simulate unchecking the checkbox in the first row using GUI interaction
    #     QTest.mouseClick(coef_table.viewport(), Qt.LeftButton, pos=coef_table.visualItemRect(checkbox_item).center())

    #     # Re-fetch the items after interaction
    #     collected_points_item = coef_table.item(0, 3)

    #     # Check if the "Collected Points" value is "0" again
    #     self.assertEqual(collected_points_item.text(), "0")


    # def test_slider_update_on_checkbox_toggle_gui(self):
    #     self.send_signal(self.widget.Inputs.classifier, self.scoring_sheet_model)
    #     self.wait_until_finished()

    #     coef_table = self.widget.coefficient_table
    #     risk_slider = self.widget.risk_slider
    #     risk_slider_points = risk_slider.points

    #     # Get the items in the first row of the table
    #     checkbox_item = coef_table.item(0, 2)
    #     attribute_points_item = coef_table.item(0, 1)

    #     # Check if the slider value is "0" before clicking the checkbox
    #     self.assertEqual(risk_slider.slider.value(), risk_slider_points.index(0))

    #     # Simulate checking the checkbox in the first row using GUI interaction
    #     QTest.mouseClick(coef_table.viewport(), Qt.LeftButton, pos=coef_table.visualItemRect(checkbox_item).center())

    #     # Re-fetch the items after interaction
    #     attribute_points_item = coef_table.item(0, 1)

    #     # Check if the slider value is now the same as the attribute's coefficient
    #     self.assertEqual(risk_slider.slider.value(), risk_slider_points.index(float(attribute_points_item.text())))

    #     # Simulate unchecking the checkbox in the first row using GUI interaction
    #     QTest.mouseClick(coef_table.viewport(), Qt.LeftButton, pos=coef_table.visualItemRect(checkbox_item).center())

    #     # Check if the slider value is "0" again
    #     self.assertEqual(risk_slider.slider.value(), risk_slider_points.index(0))


if __name__ == "__main__":
    unittest.main()
