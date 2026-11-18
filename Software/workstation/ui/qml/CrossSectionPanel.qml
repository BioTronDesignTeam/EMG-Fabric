import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick3D

Rectangle {
    id: section
    color: "#111c28"
    border.color: "#334454"
    property bool current: phantom && phantom.sectionMetrics.axial === phantom.sectionAxial && phantom.sectionMetrics.source === phantom.selectedSource
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 10; spacing: 4
        RowLayout {
            Layout.fillWidth: true
            Label { text: "FEA CROSS-SECTION"; color: "#dce7ee"; font.bold: true; font.pixelSize: 11 }
            Item { Layout.fillWidth: true }
            ComboBox {
                Layout.preferredWidth: 104
                model: ["Source 1", "Source 2", "Source 3", "Source 4"]
                currentIndex: phantom ? phantom.selectedSource : 0
                onActivated: index => phantom.selectSource(index)
            }
            Button { text: "×"; onClicked: phantom.showSection(false) }
        }
        RowLayout {
            Label { text: "z: " + (phantom ? phantom.sectionAxial.toFixed(1) : "15.0") + " mm"; color: "#a9bdcd"; font.pixelSize: 11; Layout.preferredWidth: 82 }
            Slider {
                objectName: "sectionPositionSlider"
                Layout.fillWidth: true
                from: -120; to: 120; value: phantom ? phantom.sectionAxial : 15
                onMoved: phantom.setSectionAxial(value)
            }
        }
        View3D {
            id: sliceView
            objectName: "crossSectionScene"
            Layout.fillWidth: true; Layout.fillHeight: true
            camera: sliceCamera
            environment: SceneEnvironment { clearColor: "#111c28"; backgroundMode: SceneEnvironment.Color; antialiasingMode: SceneEnvironment.MSAA }
            OrthographicCamera {
                id: sliceCamera
                position: Qt.vector3d(0, 200, 0)
                eulerRotation.x: -90
                horizontalMagnification: Math.max(0.1, Math.min(sliceView.width, sliceView.height)/(2.2*(phantom ? phantom.anatomy.radius : 37.8)))
                verticalMagnification: horizontalMagnification
            }
            Model {
                geometry: phantom ? phantom.sectionGeometry : null
                materials: PrincipledMaterial { vertexColorsEnabled: true; lighting: PrincipledMaterial.NoLighting; cullMode: Material.NoCulling }
            }
            Model {
                geometry: phantom ? phantom.sectionOutlines : null
                materials: PrincipledMaterial { baseColor: "#293844"; lighting: PrincipledMaterial.NoLighting; cullMode: Material.NoCulling }
            }
            Repeater {
                model: phantom ? phantom.sourceMarkers.length : 0
                delegate: Item {
                    required property int index
                    property var marker: phantom.sourceMarkers[index]
                    property bool positivePlane: Math.abs(phantom.sectionAxial-marker.positiveZMm) <= .5
                    property bool negativePlane: Math.abs(phantom.sectionAxial-marker.negativeZMm) <= .5
                    property bool selected: phantom.selectedSource === index
                    objectName: "sliceSource" + index
                    x: sliceView.width/2+marker.xMm*sliceCamera.horizontalMagnification-width/2
                    y: sliceView.height/2-marker.yMm*sliceCamera.verticalMagnification-height/2
                    width: 19; height: 19
                    Rectangle {
                        anchors.fill: parent; radius: width/2
                        color: parent.positivePlane ? "#ffae55" : parent.negativePlane ? "#ae9bff" : "transparent"
                        border.width: parent.selected ? 2 : 1
                        border.color: parent.selected ? "#32f0d0" : "#536a7c"
                    }
                    Text {
                        anchors.centerIn: parent
                        text: index+1
                        color: positivePlane || negativePlane ? "#17222d" : "#294558"
                        font.bold: true; font.pixelSize: 11
                    }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onClicked: phantom.selectSource(index)
                        ToolTip.visible: containsMouse
                        ToolTip.text: marker.label + " · centers at z=" + marker.negativeZMm + " / +" + marker.positiveZMm + " mm. Marker shows source center, not electrode size."
                    }
                }
            }
        }
        Label {
            text: !section.current ? (phantom && phantom.sectionMetrics.error ? phantom.sectionMetrics.error : "Updating slice…") : "Potential: " + phantom.sectionMetrics.min + " to " + phantom.sectionMetrics.max + " mV"
            color: "#a9bdcd"; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap
        }
        Rectangle {
            Layout.fillWidth: true; height: 7
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#1f66f2" } GradientStop { position: .5; color: "#d6dee6" } GradientStop { position: 1; color: "#f23d2e" } }
        }
        Label { text: "Sources 1–4: + orange / − violet near ±15 mm; hollow = axial projection. Markers show distributed-source centers."; color: "#a9bdcd"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Label {
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            text: section.current ? "Scale ±" + phantom.sectionMetrics.scale + " mV · 1 µA source\nBone / muscle / skin boundaries · +x right, +y up" : "Exact tetrahedral interpolation · fixed volume scale"
            color: "#829aaa"; font.pixelSize: 10
        }
    }
}
