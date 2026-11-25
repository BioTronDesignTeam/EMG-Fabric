import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick3D

Rectangle {
    id: frame
    objectName: robot ? "robotViewport" : "phantomViewport"
    property string title: ""
    property bool robot: false
    property bool fieldVisible: false
    property bool sourcesVisible: true
    property real orbitYaw: -22
    property real orbitPitch: -12
    property real distance: robot ? 650 : 440
    signal robotSelected()
    signal electrodeSelected()
    radius: 10; color: "#111b26"; border.color: "#2a3a49"
    clip: true
    View3D {
        id: scene
        objectName: frame.robot ? "robotScene" : "phantomScene"
        camera: orbitCamera
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: parent.top; anchors.bottom: sectionPanel.visible ? sectionPanel.top : parent.bottom
        anchors.margins: 1
        environment: SceneEnvironment { clearColor: "#111b26"; backgroundMode: SceneEnvironment.Color; antialiasingMode: SceneEnvironment.MSAA }
        Node {
            eulerRotation: Qt.vector3d(frame.orbitPitch, frame.orbitYaw, 0)
            PerspectiveCamera { id: orbitCamera; z: frame.distance; clipNear: 1; clipFar: 2000 }
        }
        DirectionalLight { eulerRotation: Qt.vector3d(-35, -30, 0); brightness: 1.2 }
        DirectionalLight { eulerRotation: Qt.vector3d(30, 150, 0); brightness: 0.6; color: "#64c6d4" }
        Model {
            source: "#Rectangle"; y: frame.robot ? -230 : -120; eulerRotation.x: -90; scale: Qt.vector3d(5, 5, 1)
            materials: PrincipledMaterial { baseColor: "#1c2c38"; roughness: 0.9 }
        }
        Node {
            visible: !frame.robot
            Model {
                visible: frame.fieldVisible
                objectName: "phantomSurface"
                pickable: true
                geometry: phantom ? phantom.geometry : null
                materials: PrincipledMaterial {
                    vertexColorsEnabled: true
                    roughness: 0.8
                    cullMode: Material.NoCulling
                }
            }
            Model {
                visible: !frame.fieldVisible
                geometry: phantom ? phantom.boneGeometry : null
                materials: PrincipledMaterial { baseColor: "#e8dfbd"; roughness: .8; cullMode: Material.NoCulling }
            }
            Model {
                visible: !frame.fieldVisible
                geometry: phantom ? phantom.muscleGeometry : null
                materials: PrincipledMaterial { baseColor: "#a84e50"; roughness: .85; cullMode: Material.NoCulling }
            }
            Model {
                visible: !frame.fieldVisible
                geometry: phantom ? phantom.skinGeometry : null
                materials: PrincipledMaterial { baseColor: "#d5a583"; roughness: .9; cullMode: Material.NoCulling }
            }
            Repeater3D {
                model: phantom ? phantom.channelCount*2 : 8
                delegate: Model {
                    required property int index
                    property real theta: ((phantom ? phantom.angle : 0) + Math.floor(index/2)*360/(phantom ? phantom.channelCount : 4)) * Math.PI/180
                    objectName: "electrode" + index
                    pickable: true
                    source: "#Sphere"
                    x: Math.cos(theta) * (phantom ? phantom.anatomy.radius : 37.8)
                    z: Math.sin(theta) * (phantom ? phantom.anatomy.radius : 37.8)
                    y: (phantom ? phantom.axial : 0) + (index%2 === 0 ? -1 : 1) * (phantom ? phantom.spacing : 20)/2
                    scale: Qt.vector3d(.065, .065, .065)
                    materials: PrincipledMaterial { baseColor: index%2 === 0 ? "#53f1d8" : "#f4d571"; roughness: .3 }
                }
            }
        }
        Model {
            visible: !frame.robot && phantom && phantom.sectionVisible
            source: "#Cube"
            y: phantom ? phantom.sectionAxial : 15
            scale: Qt.vector3d((phantom ? phantom.anatomy.radius : 37.8)*.023, .005, (phantom ? phantom.anatomy.radius : 37.8)*.023)
            materials: PrincipledMaterial { baseColor: "#52dfcc"; opacity: .25; alphaMode: PrincipledMaterial.Blend; lighting: PrincipledMaterial.NoLighting }
        }
        Node {
            visible: frame.robot
            // Align Shadow's forearm base and upright axis with the Bionic viewport pose.
            position: hand && hand.modelIndex === 1 ? Qt.vector3d(-5,-207,-23) : Qt.vector3d(-5,82,-106)
            eulerRotation.x: -90
            Node {
                eulerRotation.y: hand && hand.modelIndex === 1 ? -90 : 0
                Repeater3D {
                    model: frame.robot && hand ? hand.bodies : []
                    delegate: Model {
                        required property int index
                        required property var modelData
                        property var bodyPose: hand.poses.length > index ? hand.poses[index] : null
                        objectName: "robotBody_" + modelData.name
                        geometry: modelData.geometry
                        position: bodyPose ? bodyPose.position : Qt.vector3d(0,0,0)
                        rotation: bodyPose ? bodyPose.rotation : Qt.quaternion(1,0,0,0)
                        materials: PrincipledMaterial { baseColor: "#bbcbd7"; metalness: .35; roughness: .6; cullMode: Material.NoCulling }
                    }
                }
            }
        }
    }
    // A transparent second pass keeps buried source centers visible through
    // opaque tissue, without moving them onto the skin or altering the field.
    View3D {
        id: sourceOverlay
        objectName: "internalSourceOverlay"
        visible: !frame.robot && frame.sourcesVisible
        anchors.fill: scene
        camera: sourceCamera
        environment: SceneEnvironment { backgroundMode: SceneEnvironment.Transparent; antialiasingMode: SceneEnvironment.MSAA }
        Node {
            eulerRotation: Qt.vector3d(frame.orbitPitch, frame.orbitYaw, 0)
            PerspectiveCamera { id: sourceCamera; z: frame.distance; clipNear: 1; clipFar: 2000 }
        }
        MuscleSources {}
    }
    Repeater {
        model: !frame.robot && frame.sourcesVisible && phantom ? phantom.sourceMarkers.length : 0
        delegate: Label {
            required property int index
            property var marker: phantom.sourceMarkers[index]
            property vector3d projected: {
                frame.orbitYaw; frame.orbitPitch; frame.distance; sourceOverlay.width; sourceOverlay.height
                return sourceOverlay.mapFrom3DScene(Qt.vector3d(marker.xMm, 0, marker.yMm))
            }
            x: scene.x+projected.x+(marker.xMm >= 0 ? 8 : -22)
            y: scene.y+projected.y+[-18,-35,12,28][index]
            leftPadding: 2; rightPadding: 2
            background: Rectangle { color: "#172430"; radius: 2; opacity: .85 }
            text: marker.label
            font.pixelSize: 10; font.bold: true
            color: phantom.selectedSource === index ? "#ffffff" : "#b6c7d5"
        }
    }
    MouseArea {
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: parent.top; anchors.bottom: sectionPanel.visible ? sectionPanel.top : parent.bottom
        property real lastX
        property real lastY
        property int draggingElectrode: -1
        onPressed: mouse => {
            lastX = mouse.x; lastY = mouse.y
            draggingElectrode = -1
            let foreground = !frame.robot ? scene.pick(mouse.x-1, mouse.y-1).objectHit : null
            if (!frame.robot && frame.sourcesVisible && phantom && !(foreground && foreground.objectName.startsWith("electrode"))) {
                let sourceHit = sourceOverlay.pick(mouse.x-1, mouse.y-1)
                if (sourceHit.objectHit && sourceHit.objectHit.objectName.startsWith("musclePole")) {
                    phantom.selectSource(Math.floor(parseInt(sourceHit.objectHit.objectName.substring(10))/2))
                    return
                }
            }
            if (!frame.robot && phantom && phantom.ready) {
                let hit = scene.pick(mouse.x-1, mouse.y-1)
                if (hit.objectHit && hit.objectHit.objectName.startsWith("electrode")) {
                    draggingElectrode = parseInt(hit.objectHit.objectName.substring(9))
                    // Open the inspector with the button; keep the viewport stable during drag.
                }
            }
        }
        onReleased: draggingElectrode = -1
        onPositionChanged: mouse => {
            if (pressed && draggingElectrode >= 0) {
                // Analytic cylinder hit avoids mesh-wide picking on every move,
                // and also works through the anatomy cutaway.
                let a = scene.mapTo3DScene(Qt.vector3d(mouse.x-1, mouse.y-1, 0))
                let b = scene.mapTo3DScene(Qt.vector3d(mouse.x-1, mouse.y-1, 1000))
                let dx = b.x-a.x, dy = b.y-a.y, dz = b.z-a.z
                let radius = phantom.anatomy.radius
                let A = dx*dx+dz*dz, B = 2*(a.x*dx+a.z*dz)
                let C = a.x*a.x+a.z*a.z-radius*radius
                let disc = B*B-4*A*C
                if (disc >= 0 && A > 1e-9) {
                    let t = (-B-Math.sqrt(disc))/(2*A)
                    let y = a.y+t*dy
                    if (t >= 0 && Math.abs(y) <= phantom.anatomy.length/2) {
                        let pair = Math.floor(draggingElectrode/2)
                        let offset = (draggingElectrode%2 === 0 ? -1 : 1) * phantom.spacing/2
                        phantom.place(Math.atan2(a.z+t*dz, a.x+t*dx)*180/Math.PI-pair*360/phantom.channelCount, y-offset, phantom.spacing)
                    }
                }
            } else if (pressed) {
                frame.orbitYaw += (mouse.x - lastX) * 0.4
                frame.orbitPitch = Math.max(-80, Math.min(80, frame.orbitPitch + (mouse.y - lastY) * 0.4))
                lastX = mouse.x; lastY = mouse.y
            }
        }
        onWheel: wheel => frame.distance = Math.max(250, Math.min(750, frame.distance - wheel.angleDelta.y * 0.4))
    }
    Column {
        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 16; spacing: 5
        Label { text: frame.title; color: "#e4edf3"; font.pixelSize: 16; font.bold: true }
        Label { text: frame.robot ? "MUJOCO PHYSICS · CAD JOINT PROTOTYPE" : (frame.fieldVisible ? "3D ELECTRICAL FEM · UNIT-SOURCE POTENTIAL" : "BONE CORE · MUSCLE · SKIN / CUTAWAY"); color: "#829aaa"; font.pixelSize: 10 }
    }
    CheckBox {
        visible: !frame.robot
        anchors.top: parent.top; anchors.topMargin: 58
        anchors.left: parent.left; anchors.leftMargin: 12
        checked: frame.sourcesVisible
        onToggled: frame.sourcesVisible = checked
        palette.windowText: "#b8cbd9"
        text: "Internal sources · X-ray    + orange / − violet"
        font.pixelSize: 10
    }
    Row {
        visible: !frame.robot
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 14
        spacing: 5
        Button { objectName: "crossSectionToggle"; text: "Slice"; highlighted: phantom && phantom.sectionVisible; onClicked: phantom.showSection(!phantom.sectionVisible) }
        Button { text: frame.fieldVisible ? "Show anatomy" : "Show FEA field"; onClicked: frame.fieldVisible = !frame.fieldVisible }
    }
    CrossSectionPanel {
        id: sectionPanel
        visible: !frame.robot && phantom && phantom.sectionVisible
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: Math.min(310, frame.height*0.52)
    }
    Button {
        visible: !frame.robot
        anchors.bottom: sectionPanel.visible ? sectionPanel.top : parent.bottom; anchors.left: parent.left; anchors.margins: 14
        text: "◎  Inspect electrode pair"; onClicked: frame.electrodeSelected()
    }
    Button {
        visible: frame.robot
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 14
        text: "Joint controls"; onClicked: frame.robotSelected()
    }
    Row {
        visible: frame.robot
        anchors.left: parent.left; anchors.top: parent.top; anchors.leftMargin: 14; anchors.topMargin: 58
        spacing: 5
        Button { text: hand && hand.modelIndex === 0 ? "CAD rest" : "Rest"; enabled: hand && hand.ready; onClicked: hand.setPose('rest') }
        Button { text: "Flex test"; objectName: frame.robot ? "robotFlexButton" : ""; enabled: hand && hand.ready; onClicked: hand.setPose('flex') }
        Button { text: "Spread"; enabled: hand && hand.ready; onClicked: hand.setPose('spread') }
    }
    Label {
        visible: frame.robot
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 16
        text: hand ? hand.status + " · " + hand.stepHz + " Hz\nManual control · " + hand.joints.length + " channels\nGesture inference: not connected" : "Loading MuJoCo…"
        color: "#a4bbc9"; font.pixelSize: 11; lineHeight: 1.5
    }
    Button {
        anchors.bottom: sectionPanel.visible ? sectionPanel.top : parent.bottom; anchors.right: parent.right; anchors.margins: 14
        text: "Reset view"
        onClicked: { frame.orbitYaw = -22; frame.orbitPitch = -12; frame.distance = frame.robot ? 650 : 440 }
    }
}
