import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: panel
    clip: true; contentWidth: availableWidth
    ColumnLayout {
        width: Math.max(0,panel.availableWidth-14); spacing: 12
        Label { text: hand ? hand.status : ""; color: "#52dfcc"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Label { text: "CAD ARTICULATION PROTOTYPE"; color: "#dce7ee"; font.bold: true }
        Label { text: "20 inferred hinges · 19 mapped controller channels. Hinge axes come from CAD bearing surfaces. Part grouping, travel limits, mass, collision proxies and servo gains are provisional."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Label { text: "Manual testing · no gesture inference\nThe supplied CAD pose is the zero reference."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        RowLayout {
            Button { text: "CAD rest"; enabled: hand && hand.ready; onClicked: hand.setPose('rest') }
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
            text: hand && hand.joints.length && jointChoice.currentIndex >= 0 ? "Simulated angle: " + hand.joints[jointChoice.currentIndex].position.toFixed(1) + "°\nTarget: " + hand.joints[jointChoice.currentIndex].target.toFixed(1) + "°" : "Loading joints…"
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
        Label { text: "Thumb middle is an extra CAD hinge candidate without a med01 channel. Verify its real mechanism before coupling or commanding hardware. Self-collision is disabled until rigid ownership is reviewed."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Label { text: "The Qt viewport draws actual MuJoCo body poses; sliders drive position actuators, not direct geometry animation."; color: "#9db1c2"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
}
