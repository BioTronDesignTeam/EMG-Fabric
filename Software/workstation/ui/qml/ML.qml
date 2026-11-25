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

    id: panel
    clip: true; contentWidth: availableWidth
    ColumnLayout {
        width: Math.max(0,panel.availableWidth-14); spacing: 12
        Label { text: "ML MODEL"; color: "#dce7ee"; font.bold: true }
        ComboBox {
            objectName: "MLModelSelector"
            Layout.fillWidth: true
            model: ["coughing baby","hydrogen bomb"]
            currentIndex: ml ? ml.modelIndex : 0
            onActivated: index => ml.setModel(index === 0 ? "coughing baby" : "hydrogen bomb")
        }
        Button { text: "Load HDF5 recording"; onClicked: signalFileDialog.open() }
        Button { text: (hand && hand.plot_label) ? "Pause Hand Gesture" : "Resume Hand Gesture"; onClicked: hand.toggleplot()}
    }
}
