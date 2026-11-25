import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ScrollView {
    FileDialog {
            id: signalFileDialog

            title: "Load EMG signal data"
            fileMode: FileDialog.OpenFile

            nameFilters: [
                "Signal files (*.csv *.h5 *.hdf5)",
                "CSV files (*.csv)",
                "HDF5 files (*.h5 *.hdf5)",
                "All files (*)"
            ]

            onAccepted: {
                workspace.loadSignalFile(selectedFile)
                phantom.setChannelCount(16)
            }
    }
     FileDialog {
            id: checkpointFileDialog

            title: "Load EMG signal data"
            fileMode: FileDialog.OpenFile

            nameFilters: [
                "Checkpoint files (*.ckpt)",
                "All files (*)"
            ]

            onAccepted: {
                ml.loadcheckpointFile(selectedFile)
            }
    }

    id: panel
    clip: true; contentWidth: availableWidth
    ColumnLayout {
        width: Math.max(0,panel.availableWidth-14); spacing: 12
        Label { text: "ML MODEL"; color: "#dce7ee"; font.bold: true }
        ComboBox {
            objectName: "MLModelSelector"
            Layout.fillWidth: true
            model: ml ? ml.models: []
            currentIndex: ml ? ml.modelIndex : 0
            onActivated: index => ml.setModel(currentText)
        }
        Button { text: "Load HDF5 recording"; onClicked: signalFileDialog.open() }
        Label {text: (workspace && workspace.filename) ? "Loaded file: " + workspace.filename : "No files loaded";  color: "#dce7ee";}
        Button { text: "Load Checkpoint"; onClicked: checkpointFileDialog.open() }
        Label {text: (ml && ml.checkpoint) ? "Loaded file: " + ml.checkpoint : "No files loaded";  color: "#dce7ee";}
    }
}
