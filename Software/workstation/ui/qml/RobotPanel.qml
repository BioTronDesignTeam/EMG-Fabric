import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: panel
    clip: true; contentWidth: availableWidth
    ColumnLayout {
        width: Math.max(0,panel.availableWidth-14); spacing: 12
        Label { text: "HAND MODEL"; color: "#dce7ee"; font.bold: true }
        ComboBox {
            objectName: "robotHandSelector"
            Layout.fillWidth: true
            model: ["Bionic Hand", "Shadow Hand"]
            currentIndex: hand ? hand.modelIndex : 0
            onActivated: index => hand.setModel(index === 0 ? "bionic" : "shadow")
        }
        Label { text: hand ? hand.status : ""; color: "#52dfcc"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Label { text: hand ? hand.modelName.toUpperCase() : "HAND"; color: "#dce7ee"; font.bold: true }
        Label {
            text: hand && hand.modelIndex === 0
                  ? "20 inferred CAD hinges · 19 mapped controller channels. Joint limits, mass, collision proxies and servo gains remain provisional."
                  : "Shadow Hand E3M5 model · 24 joints driven by 20 position actuators, including coupled finger tendons."
            color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap
        }
        Label { text: "Manual testing · no gesture inference\nThe supplied model pose is the zero reference."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        RowLayout {
            Button { text: hand && hand.modelIndex === 0 ? "CAD rest" : "Rest"; enabled: hand && hand.ready; onClicked: hand.setPose('rest') }
            Button { text: "Flex test"; enabled: hand && hand.ready; onClicked: hand.setPose('flex') }
        }
        RowLayout {
            Button { text: "Spread test"; enabled: hand && hand.ready; onClicked: hand.setPose('spread') }
            Button { text: "Reset physics"; onClicked: hand.reset() }
        }
        Label { text: hand ? "Physics: " + hand.stepHz + " Hz\nTime: " + hand.simTime.toFixed(2) + " s\nEnvironment contacts: " + hand.contacts : ""; color: "#9db1c2" }
        Label { text: "JOINT TARGETS"; color: "#dce7ee"; font.bold: true }
        ComboBox {
            id: jointChoice
            objectName: "robotJointSelector"
            Layout.fillWidth: true
            model: hand ? hand.jointLabels : []
        }
        Label {
            Layout.fillWidth: true; wrapMode: Text.WordWrap; color: "#9db1c2"
            text: hand && hand.joints.length && jointChoice.currentIndex >= 0
                  ? "Simulated: " + hand.joints[jointChoice.currentIndex].position.toFixed(1) + hand.joints[jointChoice.currentIndex].unit + "\nTarget: " + hand.joints[jointChoice.currentIndex].target.toFixed(1) + hand.joints[jointChoice.currentIndex].unit
                  : "Loading joints…"
        }
        Slider {
            objectName: "robotJointSlider"
            Layout.fillWidth: true
            enabled: hand && hand.ready && jointChoice.currentIndex >= 0
            from: enabled ? hand.joints[jointChoice.currentIndex].lower : -30
            to: enabled ? hand.joints[jointChoice.currentIndex].upper : 30
            value: enabled ? hand.joints[jointChoice.currentIndex].target : 0
            onMoved: hand.setJointTarget(jointChoice.currentIndex,value)
        }
        Label {
            visible: hand && hand.modelIndex === 0
            text: "Thumb middle is an extra CAD hinge candidate without a med01 channel. Verify its real mechanism before coupling or commanding hardware. Self-collision is disabled until rigid ownership is reviewed."
            color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap
        }
        Label { text: "The Qt viewport draws actual MuJoCo body poses; sliders drive position actuators, not direct geometry animation."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
}
