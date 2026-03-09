import sys
import unittest
from PyQt5.QtWidgets import QApplication
from taelss_gui import MainWindow

app = QApplication(sys.argv)

class TestTAELSSGUI(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()

    def test_window_title(self):
        self.assertEqual(self.window.windowTitle(), "TAELCO Skin&Stringer Analysis Software - TAELSS_v1.0")

    def test_buttons_exist(self):
        expected_buttons = [
            "Read Model",
            "Show Model",
            "Select Results",
            "Show Materials",
            "Show Rivets",
            "Show Structural Properties",
            "Run Analysis",
            "Show Results"
        ]
        for btn_name in expected_buttons:
            self.assertIn(btn_name, self.window.button_dict)

    def test_initial_state(self):
        self.assertIsNone(self.window.model_file)
        self.assertIsNone(self.window.bdf)
        self.assertIsNone(self.window.result_folder)
        self.assertIsNone(self.window.material_file)
        self.assertIsNone(self.window.rivet_file)
        self.assertIsNone(self.window.structural_file)

if __name__ == "__main__":
    unittest.main()
