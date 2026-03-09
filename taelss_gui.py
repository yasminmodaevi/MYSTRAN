import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
                             QWidget, QFileDialog, QTextEdit, QMenuBar, QMenu, QAction, QGroupBox)
from PyQt5.QtCore import Qt
from pynastran.bdf.bdf import BDF
from pynastran.op2.op2 import OP2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TAELCO Skin&Stringer Analysis Software - TAELSS_v1.0")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create text box for displaying data (left side)
        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        main_layout.addWidget(self.text_box, stretch=3)

        # Create button layout (right side)
        right_panel = QGroupBox("Controls")
        button_layout = QVBoxLayout(right_panel)
        buttons = [
            "Read Model",
            "Show Model",
            "Select Results",
            "Show Materials",
            "Show Rivets",
            "Show Structural Properties",
            "Run Analysis",
            "Show Results"
        ]

        self.button_dict = {}
        for btn_name in buttons:
            btn = QPushButton(btn_name)
            btn.clicked.connect(getattr(self, f"on_{btn_name.replace(' ', '_').lower()}"))
            button_layout.addWidget(btn)
            self.button_dict[btn_name] = btn

        button_layout.addStretch()

        # Add button layout to main layout
        main_layout.addWidget(right_panel, stretch=1)

        # Create menu bar
        self.create_menu_bar()

        # Store file paths and data
        self.model_file = None
        self.bdf = None
        self.result_folder = None
        self.material_file = None
        self.rivet_file = None
        self.structural_file = None

    def create_menu_bar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('Open Model', self.on_read_model)
        file_menu.addAction('Save Model', self.on_save_model)
        file_menu.addAction('Show Model', self.on_show_model)
        file_menu.addAction('Open Material Data', self.on_open_material_data)
        file_menu.addAction('Open Rivet Data', self.on_open_rivet_data)
        file_menu.addAction('Open Geometrical Inputs', self.on_open_geometrical_inputs)
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close)

        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        # Add actions as needed

        # View menu
        view_menu = menubar.addMenu('View')
        # Add actions as needed

        # Tool menu
        tool_menu = menubar.addMenu('Tool')
        # Add actions as needed

        # Help menu
        help_menu = menubar.addMenu('Help')
        # Add actions as needed

    def on_read_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Model File", "",
            "Model Files (*.bdf *.dat *.SDB);;All Files (*)"
        )
        if file_path:
            try:
                self.bdf = BDF()
                self.bdf.read_bdf(file_path)
                self.model_file = file_path
                self.text_box.append(f"Selected model file: {os.path.basename(file_path)}")
                self.text_box.append(f"Full path: {file_path}")
                self.text_box.append(f"Model loaded successfully. Nodes: {len(self.bdf.nodes)}")
            except Exception as e:
                self.text_box.append(f"Error reading model: {str(e)}")

    def on_show_model(self):
        if not self.bdf:
            self.text_box.append("No model loaded. Please select a model first.")
            return

        try:
            # This would open the model in PyNastran viewer
            self.text_box.append(f"Showing model: {os.path.basename(self.model_file)}")
            # In a real implementation, you would use PyNastran's GUI viewer here
            # For now, we'll just display summary information
            self.text_box.append(f"Model Summary: {self.bdf.get_bdf_stats()}")
        except Exception as e:
            self.text_box.append(f"Error showing model summary: {str(e)}")

    def on_select_results(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Results Folder")
        if folder_path:
            self.result_folder = folder_path
            self.text_box.append(f"Selected results folder: {folder_path}")

    def on_show_materials(self):
        file_path = self.open_text_file("Material Data", "*.txt *.dat *.csv")
        if file_path:
            self.material_file = file_path

    def on_show_rivets(self):
        file_path = self.open_text_file("Rivet Data", "*.txt *.dat *.csv")
        if file_path:
            self.rivet_file = file_path

    def on_show_structural_properties(self):
        file_path = self.open_text_file("Structural Properties", "*.txt *.dat *.csv")
        if file_path:
            self.structural_file = file_path

    def open_text_file(self, title, filter_str):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {title}", "",
            f"{title} Files ({filter_str});;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                self.text_box.append(f"Showing {title}: {os.path.basename(file_path)}")
                self.text_box.append("="*50)
                self.text_box.append(content[:1000] + "..." if len(content) > 1000 else content)
                self.text_box.append("="*50)
                return file_path
            except Exception as e:
                self.text_box.append(f"Error reading {title}: {str(e)}")
        return None

    def on_run_analysis(self):
        self.text_box.append("Running analysis...")
        missing_files = []
        if not self.model_file: missing_files.append("Model File")
        if not self.material_file: missing_files.append("Material File")
        if not self.rivet_file: missing_files.append("Rivet File")
        if not self.structural_file: missing_files.append("Structural File")

        if missing_files:
            self.text_box.append(f"Cannot run analysis. Missing: {', '.join(missing_files)}")
            return

        self.text_box.append("All required inputs are present.")
        self.text_box.append("Analysis started... (Stub)")
        # In a real app, this might call an external solver like MYSTRAN or a internal solver logic.
        self.text_box.append("Analysis complete.")

    def on_show_results(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Results File", self.result_folder or "",
            "OP2 Files (*.op2);;All Files (*)"
        )
        if file_path:
            try:
                op2 = OP2()
                op2.read_op2(file_path)
                self.text_box.append(f"Loaded results: {os.path.basename(file_path)}")
                self.text_box.append(f"Available results: {op2.get_op2_stats()}")
            except Exception as e:
                self.text_box.append(f"Error loading results: {str(e)}")

    def on_save_model(self):
        if not self.bdf:
            self.text_box.append("No model loaded to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Model File", "",
            "Model Files (*.bdf *.dat *.SDB);;All Files (*)"
        )
        if file_path:
            try:
                self.bdf.write_bdf(file_path)
                self.text_box.append(f"Model saved to: {file_path}")
            except Exception as e:
                self.text_box.append(f"Error saving model: {str(e)}")

    def on_open_material_data(self):
        self.on_show_materials()

    def on_open_rivet_data(self):
        self.on_show_rivets()

    def on_open_geometrical_inputs(self):
        self.on_show_structural_properties()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
