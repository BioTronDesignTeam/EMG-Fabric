import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: panel
    clip: true
    contentWidth: availableWidth
    ColumnLayout {
        // Keep the slider's final detent clear of the overlaid scroll bar.
        width: Math.max(0, panel.availableWidth-14)
        spacing: 10
        Label { text: phantom ? phantom.status : ""; color: "#52dfcc"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Label { text: phantom ? "Three-layer human-data preset\nBone core radius: " + phantom.anatomy.boneRadius.toFixed(2) + " mm\nMuscle thickness: " + phantom.anatomy.muscleThickness.toFixed(2) + " mm\nSkin thickness: " + phantom.anatomy.skinThickness.toFixed(2) + " mm\nOuter radius: " + phantom.anatomy.radius.toFixed(2) + " mm\nModeled segment: 240 mm (chosen)" : ""; color: "#9db1c2"; font.pixelSize: 11; lineHeight: 1.4 }
        Label { text: "Iivarinen et al., N=11 adults. The single bone core preserves combined radius/ulna area; muscle thickness is derived from the circular approximation. Subcutaneous fat is omitted for this three-layer model."; color: "#9db1c2"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
        Label { text: '<a href="https://doi.org/10.1111/j.1600-0846.2012.00652.x">Human imaging source · Table 1</a>'; onLinkActivated: link => Qt.openUrlExternally(link); linkColor: "#52dfcc"; font.pixelSize: 11 }
        Label { text: "ELECTRODE ARRAY"; color: "#dce7ee"; font.bold: true }
        Label { text: "Electrode pairs / channels: " + (phantom ? phantom.channelCount : 4); color: "#dce7ee" }
        Slider {
            objectName: "channelCountSlider"
            Layout.fillWidth: true
            from: 0; to: 3; stepSize: 1; snapMode: Slider.SnapAlways
            value: phantom ? [2,4,8,16].indexOf(phantom.channelCount) : 1
            onMoved: phantom.setChannelCount([2,4,8,16][Math.round(value)])
        }
        RowLayout {
            Layout.fillWidth: true
            Repeater { model: [2,4,8,16]; Label { required property int modelData; text: modelData; color: "#9db1c2"; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter } }
        }
        Label { text: phantom ? phantom.channelCount + " axial bipolar pairs, " + (360/phantom.channelCount).toFixed(1) + "° apart. Each pair produces one signal channel. Drag a marker to rotate the entire equally spaced array." : ""; color: "#9db1c2"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Label { text: "Array angle: " + (phantom ? phantom.angle.toFixed(1) : "0") + "°"; color: "#dce7ee" }
        Slider { Layout.fillWidth: true; from: 0; to: 360; value: phantom ? phantom.angle : 0; onMoved: phantom.place(value, phantom.axial, phantom.spacing) }
        Label { text: "Axial center: " + (phantom ? phantom.axial.toFixed(1) : "0") + " mm"; color: "#dce7ee" }
        Slider { Layout.fillWidth: true; from: phantom ? -120+phantom.spacing/2 : -110; to: phantom ? 120-phantom.spacing/2 : 110; value: phantom ? phantom.axial : 0; onMoved: phantom.place(phantom.angle, value, phantom.spacing) }
        Label { text: "Pair spacing: " + (phantom ? phantom.spacing.toFixed(1) : "20") + " mm"; color: "#dce7ee" }
        Slider { Layout.fillWidth: true; from: 5; to: 50; value: phantom ? phantom.spacing : 20; onMoved: phantom.place(phantom.angle, phantom.axial, value) }
        Label { text: "INTERNAL MUSCLE SOURCES"; color: "#dce7ee"; font.bold: true }
        Label { text: "Four source pairs are drawn inside the muscle with an X-ray overlay. Orange marks + current at z=+15 mm; violet marks − current at z=−15 mm. Click a source to select it. These are centers of distributed Gaussian current regions (σ=9 mm), not physical implanted electrodes."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 11 }
        Label { text: "FIELD SOURCE / CH1 TARGET"; color: "#dce7ee"; font.bold: true }
        ComboBox { Layout.fillWidth: true; model: ["Muscle 1 · 0°", "Muscle 2 · 90°", "Muscle 3 · 180°", "Muscle 4 · 270°"]; currentIndex: phantom ? phantom.selectedSource : 0; onActivated: index => phantom.selectSource(index) }
        Label { text: "The FEA view colors surface voltage for a selected 1 µA muscle dipole, relative to the volume mean: red positive, blue negative, white near zero. It is not the live waveform or mechanical stress."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 11 }
        Label { text: "UNIT-SOURCE FIELD (mV / 1 µA)"; color: "#9db1c2"; font.pixelSize: 10 }
        Rectangle {
            Layout.fillWidth: true; height: 12; radius: 3
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#1f66f2" } GradientStop { position: .5; color: "#d6dee6" } GradientStop { position: 1; color: "#f23d2e" } }
        }
        Label { text: phantom && phantom.ready ? "−" + phantom.metrics.fieldMax + "          0          +" + phantom.metrics.fieldMax : "Solving…"; color: "#9db1c2"; font.pixelSize: 10 }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: "#dce7ee"; lineHeight: 1.4; text: phantom && phantom.ready ? "CH1 sensitivity: " + phantom.metrics.sensitivity + " mV / µA\nCH1 cross-talk power: " + phantom.metrics.crossTalk + "\nNodes: " + phantom.metrics.nodes + " · Tetrahedra: " + phantom.metrics.elements + "\nAssembly + solve: " + phantom.metrics.solveMs + " ms\nRelative residual: " + phantom.metrics.residual : "" }
        Label { text: "Cross-talk assumes equal, independent source power and excludes the selected target. It is a model estimate, independent of activation controls."; color: "#9db1c2"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Label { text: "MUSCLE ACTIVATION"; color: "#dce7ee"; font.bold: true }
        Repeater {
            model: 4
            delegate: ColumnLayout {
                required property int index
                Layout.fillWidth: true; spacing: 0
                Label { text: "Muscle " + (index+1) + " · " + (phantom ? Math.round(phantom.activations[index]*100) : 0) + "%"; color: "#9db1c2" }
                Slider { Layout.fillWidth: true; from: 0; to: 1; value: phantom ? phantom.activations[index] : 0; onMoved: phantom.activate(index, value) }
            }
        }
        Label { text: "LEAD FIELD · mV / µA"; color: "#dce7ee"; font.bold: true }
        Label { text: phantom && phantom.ready ? phantom.metrics.leadField : ""; color: "#9db1c2"; font.pixelSize: 10; font.family: "Menlo"; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
        Label { text: "Illustrative conductivity (S/m): skin 0.20; bone 0.02; muscle transverse 0.12 / axial 0.40. Simplified concentric anatomy, smooth current dipoles, point electrodes; no contact impedance or propagation model. Not calibrated or mesh-converged."; color: "#9db1c2"; wrapMode: Text.WordWrap; font.pixelSize: 11; Layout.fillWidth: true }
    }
}
