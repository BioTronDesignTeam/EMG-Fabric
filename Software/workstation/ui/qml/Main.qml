import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Workstation 1.0

ApplicationWindow {
    id: root
    visible: true
    width: 1440; height: 940
    minimumWidth: 1080; minimumHeight: 720
    title: "EMG Fabric · Biomedical Robotics Workstation"
    color: "#0c1118"
    property string panel: ""
    property string selected: "Electrode array"
    property bool expanded: false
    palette.window: "#111923"
    palette.button: "#202d3a"
    palette.buttonText: "#dce7ee"
    palette.text: "#dce7ee"
    palette.base: "#182330"
    palette.highlight: "#36bcaf"
    font.family: "Arial"
    font.pixelSize: 13

    component Caption: Label { color: "#8fa4b5"; font.pixelSize: 11 }
    component Action: Button { implicitHeight: 34; }


    ColumnLayout {
        anchors.fill: parent; spacing: 1
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 66; color: "#151e29"
            RowLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 18
                Label { text: "◈"; color: "#4cdbcc"; font.pixelSize: 28 }
                Column {
                    Label { text: "EMG FABRIC"; color: "#edf5fa"; font.bold: true; font.letterSpacing: 2 }
                    Caption { text: "BIOMEDICAL ROBOTICS WORKSTATION" }
                }
                Rectangle { width: 1; Layout.fillHeight: true; color: "#2a3948" }
                ComboBox { model: ["FEA phantom · " + (phantom ? phantom.channelCount : 4) + " channels"]; Layout.preferredWidth: 230 }
                Caption { text: "●  SIMULATED"; color: "#4cdbcc" }
                Item { Layout.fillWidth: true }
                Caption { text: "2 kSPS / CH   ·   DISPLAY 30 Hz" }
                Action { text: (workspace && workspace.running) ? "Ⅱ  Pause" : "▶  Resume"; onClicked: workspace.toggleRunning() }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 1
            Rectangle {
                Layout.preferredWidth: 64; Layout.fillHeight: true; color: "#121b25"
                Column {
                    anchors.top: parent.top; anchors.topMargin: 18; width: parent.width; spacing: 12
                    Repeater {
                        model: [{icon:"◉", name:"Phantom"}, {icon:"∿", name:"Signals"}, {icon:"♧", name:"Robot"}, {icon:"◇", name:"ML"}, {icon:"▤", name:"Hardware"}, {icon:"⚙", name:"Settings"}]
                        delegate: Button {
                            required property var modelData
                            width: 58; height: 52; anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.icon; font.pixelSize: 24
                            highlighted: root.panel === modelData.name
                            ToolTip.visible: hovered; ToolTip.text: modelData.name
                            onClicked: root.panel = root.panel === modelData.name ? "" : modelData.name
                        }
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 16; spacing: 12
                RowLayout {
                    Label { text: "Simulation workspace"; color: "#e3edf4"; font.pixelSize: 20; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Caption { text: "ELECTRICAL FEA  /  SYNTHETIC SOURCES" }
                }
                RowLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                    SceneViewport { Layout.fillWidth: true; Layout.fillHeight: true; title: "Digital forearm"; onElectrodeSelected: { root.selected = "Electrode array"; root.panel = "Phantom" } }
                    SceneViewport { Layout.fillWidth: true; Layout.fillHeight: true; robot: true; title: "Bionic hand"; onRobotSelected: root.panel = "Robot" }
                }
                RowLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                    Rectangle{
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.expanded ? 300 : 176
                        color: "#141e29"; radius: 10; border.color: "#283746"
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 180 } }
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 6
                            RowLayout {
                                Label { text: "SIGNAL MONITOR"; color: "#d5e4ed"; font.bold: true; font.pixelSize: 11 }
                                Caption { text: (phantom ? phantom.channelCount : 4) + " CHANNELS  ·  FEA-DERIVED  ·  2 s WINDOW  ·  ±0.025 mV" }
                                Item { Layout.fillWidth: true }
                                Action { text: root.expanded ? "Collapse ↓" : "Expand ↑"; onClicked: root.expanded = !root.expanded }
                            }
                            ScrollView {
                                id: signalScroll
                                Layout.fillWidth: true; Layout.fillHeight: true
                                clip: true
                                contentWidth: availableWidth
                                contentHeight: Math.max(availableHeight, (phantom ? phantom.channelCount : 4)*28)
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                Row {
                                    width: signalScroll.availableWidth
                                    height: signalScroll.contentHeight
                                    Column {
                                        width: 48; height: parent.height
                                        Repeater {
                                            model: phantom ? phantom.channelCount : 4
                                            Caption {
                                                required property int index
                                                width: 48; height: signalScroll.contentHeight/(phantom ? phantom.channelCount : 4)
                                                text: "CH " + String(index+1).padStart(2,"0")
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }
                                    SignalPlot {
                                        objectName: "emgPlot"
                                        width: parent.width-48; height: parent.height; clip: true
                                        channelCount: phantom ? phantom.channelCount : 4
                                    }
                                }
                            }
                            Caption { visible: root.expanded; text: "FEA-derived synthetic waveform · filtering, spectrum, recording and export arrive in the signal-processing milestone." }
                        }
                    }
                    Rectangle{
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.expanded ? 300 : 176
                        color: "#141e29"; radius: 10; border.color: "#283746"
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 180 } }
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 6
                            RowLayout {
                                Label { text: "LABEL MONITOR"; color: "#d5e4ed"; font.bold: true; font.pixelSize: 11 }
                                Caption { text: (20) + " CHANNELS  ·  2 s WINDOW  ·  ±2 rads" }
                                Item { Layout.fillWidth: true }
                                Action { text: root.expanded ? "Collapse ↓" : "Expand ↑"; onClicked: root.expanded = !root.expanded }
                            }
                            ScrollView {
                                id: labelScroll
                                Layout.fillWidth: true; Layout.fillHeight: true
                                clip: true
                                contentWidth: availableWidth
                                contentHeight: Math.max(availableHeight, (20)*28)
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                Row {
                                    width: labelScroll.availableWidth
                                    height: labelScroll.contentHeight
                                    Column {
                                        width: 48; height: parent.height
                                        Repeater {
                                            model: 20
                                            Caption {
                                                required property int index
                                                width: 48; height: labelScroll.contentHeight/20
                                                text: "CH " + String(index+1).padStart(2,"0")
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }
                                    SignalPlot {
                                        objectName: "signalPlot"
                                        data_type: "joint_angles"
                                        width: parent.width-48; height: parent.height; clip: true
                                        channelCount: 20
                                    }
                                }
                            }
                            Caption { visible: root.expanded; text: "FEA-derived synthetic waveform · filtering, spectrum, recording and export arrive in the signal-processing milestone." }
                        }
                    }
                }
            }
            Rectangle {
                Layout.preferredWidth: root.panel === "" ? 0 : 320
                Layout.fillHeight: true; color: "#151f2b"; clip: true
                Behavior on Layout.preferredWidth { NumberAnimation { duration: 160 } }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 16
                    RowLayout {
                        Label { text: root.panel; color: "#e6eff5"; font.pixelSize: 20; Layout.fillWidth: true }
                        Action { text: "×"; onClicked: root.panel = "" }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#2b3947" }
                    Label { text: root.panel === "Phantom" ? root.selected : root.panel === "Robot" ? "MuJoCo joint controls" : root.panel === "Signals" ? "Acquisition source" : root.panel === "ML" ? "Model pipeline" : root.panel === "Hardware" ? "Device diagnostics" : "Workspace settings"; color: "#4cdbcc"; font.bold: true }
                    Label {
                        visible: root.panel !== "Phantom" && root.panel !== "Robot"
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; color: "#a9bac8"; lineHeight: 1.4
                        text: root.panel === "Signals" 
                            ? (phantom ? phantom.channelCount : 4) + " FEA-derived synthetic channels sampled at 2,000 samples per second. The monitor displays the latest two seconds. Scroll to inspect all channels. Pause controls the active acquisition source." 
                            : root.panel === "ML" 
                            ? "Select Model, load dataset and checkpoints. " 
                            : root.panel === "Hardware" 
                            ? "Source: software simulation\n\nSTM32: disconnected\nADS1291 / ADS1299: unavailable\nSPI / DMA: unavailable\nJitter / CRC / packet loss: unmeasured\nSerial / BLE: disconnected" 
                            : "Dark workspace theme\n\nDrag either scene to orbit. Use the mouse wheel to zoom. Both scenes remain visible when tools open."
                    }
                    Action { visible: root.panel === "Signals"; text: (workspace && workspace.running) ? "Pause acquisition" : "Resume acquisition"; onClicked: workspace.toggleRunning() }
                    Button { objectName: "useSyntheticSourceButton"; visible: root.panel === "Signals"; text: "Use synthetic data"; onClicked: workspace.useSyntheticSource() }
                    RobotPanel { visible: root.panel === "Robot"; Layout.fillWidth: true; Layout.fillHeight: true }
                    PhantomPanel { visible: root.panel === "Phantom"; Layout.fillWidth: true; Layout.fillHeight: true }
                    ML { visible: root.panel === "ML"; Layout.fillWidth: true; Layout.fillHeight: true }
                    Item { visible: root.panel !== "Phantom" && root.panel !== "Robot"; Layout.fillHeight: true }
                    Caption { visible: root.panel !== "Phantom" && root.panel !== "Robot"; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "ELECTRICAL PHANTOM\nFEA-derived data · illustrative anatomy\nNo hardware measurements" }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true; height: 26; color: "#121b25"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                Caption { text: (workspace && workspace.running) ? "●  Synthetic acquisition running" : "Ⅱ  Acquisition paused"; color: "#4cdbcc" }
                Item { Layout.fillWidth: true }
                Caption { text: (hand ? hand.status : "Physics loading") + "    |    Inference: not connected" }
            }
        }
    }
}
