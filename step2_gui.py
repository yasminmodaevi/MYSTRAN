from qtpy import QtWidgets, QtCore

class BucklingGUI(QtWidgets.QMainWindow):
    # Signals to communicate with the controller
    run_analysis_signal = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plate Buckling Analysis Tool")
        self.resize(1000, 800)

        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QtWidgets.QHBoxLayout(main_widget)

        # Left Panel: Inputs
        self.input_panel = QtWidgets.QWidget()
        self.input_panel.setFixedWidth(350)
        self.input_layout = QtWidgets.QVBoxLayout(self.input_panel)
        self.main_layout.addWidget(self.input_panel)

        # Geometry Inputs
        geo_group = QtWidgets.QGroupBox("Geometry")
        geo_layout = QtWidgets.QFormLayout(geo_group)
        self.length_input = QtWidgets.QLineEdit("1000.0")
        self.height_input = QtWidgets.QLineEdit("1000.0")
        self.thick_input = QtWidgets.QLineEdit("10.0")
        geo_layout.addRow("Length (X-dir):", self.length_input)
        geo_layout.addRow("Height (Y-dir):", self.height_input)
        geo_layout.addRow("Thickness:", self.thick_input)
        self.input_layout.addWidget(geo_group)

        # Hole Inputs (up to 3)
        hole_group = QtWidgets.QGroupBox("Holes (X, Y, Diameter)")
        hole_layout = QtWidgets.QVBoxLayout(hole_group)
        self.holes_inputs = []
        for i in range(3):
            h_layout = QtWidgets.QHBoxLayout()
            x_in = QtWidgets.QLineEdit("500.0" if i==0 else "0.0")
            y_in = QtWidgets.QLineEdit("500.0" if i==0 else "0.0")
            d_in = QtWidgets.QLineEdit("200.0" if i==0 else "0.0")
            h_layout.addWidget(x_in)
            h_layout.addWidget(y_in)
            h_layout.addWidget(d_in)
            hole_layout.addLayout(h_layout)
            self.holes_inputs.append((x_in, y_in, d_in))
        self.input_layout.addWidget(hole_group)

        # Material Inputs
        mat_group = QtWidgets.QGroupBox("Material")
        mat_layout = QtWidgets.QFormLayout(mat_group)
        self.e_input = QtWidgets.QLineEdit("210000.0") # MPa
        self.nu_input = QtWidgets.QLineEdit("0.3")
        mat_layout.addRow("Young's Modulus (E):", self.e_input)
        mat_layout.addRow("Poisson's Ratio (nu):", self.nu_input)
        self.input_layout.addWidget(mat_group)

        # Mesh & Springs
        mesh_group = QtWidgets.QGroupBox("Mesh & Springs")
        mesh_layout = QtWidgets.QFormLayout(mesh_group)
        self.elem_size_input = QtWidgets.QLineEdit("50.0")
        self.spring_k_input = QtWidgets.QLineEdit("100.0")
        self.num_modes_input = QtWidgets.QLineEdit("5")
        mesh_layout.addRow("Element Size:", self.elem_size_input)
        mesh_layout.addRow("Spring Coeff (k):", self.spring_k_input)
        mesh_layout.addRow("Number of Modes:", self.num_modes_input)
        self.input_layout.addWidget(mesh_group)

        # Loading
        load_group = QtWidgets.QGroupBox("Loading (N/mm)")
        load_layout = QtWidgets.QFormLayout(load_group)
        self.load_x_input = QtWidgets.QLineEdit("-1.0") # Compression
        load_layout.addRow("Right Edge Load (Nx):", self.load_x_input)
        self.input_layout.addWidget(load_group)

        # Run Button
        self.run_btn = QtWidgets.QPushButton("Run Buckling Analysis")
        self.run_btn.clicked.connect(self.emit_run_signal)
        self.input_layout.addWidget(self.run_btn)

        self.input_layout.addStretch()

        # Right Panel: Visualization (placeholder for BucklingViewer)
        self.viz_container = QtWidgets.QStackedWidget()
        self.main_layout.addWidget(self.viz_container)

        # Output Log / Results
        self.results_panel = QtWidgets.QTextEdit()
        self.results_panel.setReadOnly(True)
        self.results_panel.setMaximumHeight(150)
        self.input_layout.addWidget(self.results_panel)

    def emit_run_signal(self):
        try:
            holes = []
            for xi, yi, di in self.holes_inputs:
                if float(di.text()) > 0:
                    holes.append((float(xi.text()), float(yi.text()), float(di.text())))

            data = {
                'length': float(self.length_input.text()),
                'height': float(self.height_input.text()),
                'thickness': float(self.thick_input.text()),
                'holes': holes,
                'E': float(self.e_input.text()),
                'nu': float(self.nu_input.text()),
                'elem_size': float(self.elem_size_input.text()),
                'spring_k': float(self.spring_k_input.text()),
                'num_modes': int(self.num_modes_input.text()),
                'load_x': float(self.load_x_input.text())
            }
            self.run_analysis_signal.emit(data)
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, "Input Error", f"Invalid input values: {e}")

    def log_message(self, message):
        self.results_panel.append(message)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    gui = BucklingGUI()
    gui.show()
    # app.exec()
