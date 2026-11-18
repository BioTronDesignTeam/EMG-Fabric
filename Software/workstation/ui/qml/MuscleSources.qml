import QtQuick
import QtQuick3D

Node {
    Repeater3D {
        model: phantom ? phantom.sourceMarkers.length : 0
        delegate: Node {
            id: sourcePair
            required property int index
            property var marker: phantom.sourceMarkers[index]
            property bool selected: phantom.selectedSource === index
            x: marker.xMm
            z: marker.yMm
            Model {
                source: "#Cylinder"
                y: (marker.positiveZMm+marker.negativeZMm)/2
                scale: Qt.vector3d(.009, (marker.positiveZMm-marker.negativeZMm)/100, .009)
                materials: PrincipledMaterial { baseColor: selected ? "#f8f4db" : "#798da1"; lighting: PrincipledMaterial.NoLighting }
            }
            Repeater3D {
                model: 2
                delegate: Model {
                    required property int index
                    property bool positive: index === 1
                    source: "#Sphere"
                    objectName: "musclePole" + (sourcePair.index*2+index)
                    pickable: true
                    y: positive ? sourcePair.marker.positiveZMm : sourcePair.marker.negativeZMm
                    scale: Qt.vector3d(sourcePair.selected ? .055 : .043, sourcePair.selected ? .055 : .043, sourcePair.selected ? .055 : .043)
                    materials: PrincipledMaterial { baseColor: positive ? "#ffae55" : "#ae9bff"; lighting: PrincipledMaterial.NoLighting }
                }
            }
        }
    }
}
