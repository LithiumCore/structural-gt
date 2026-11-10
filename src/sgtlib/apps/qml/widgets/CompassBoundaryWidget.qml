import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: compassBoundary
    spacing: 3

    function parameter(id) {
        return graphController.get_compass_parameter(id)
    }

    function field(id, value) {
        graphController.set_compass_parameter(id, value)
    }

    Label {
        text: "Boundary coordinates (inclusive)"
        color: Theme.blue
        font.pixelSize: 10
    }

    RowLayout {
        Label { text: "Axis"; color: Theme.text; font.pixelSize: 10 }
        TextField {
            objectName: "compass_boundary_axis"
            text: compassBoundary.parameter("compass_boundary_axis")
            Layout.preferredWidth: 45
            font.pixelSize: 10
            onEditingFinished: compassBoundary.field("compass_boundary_axis", text)
        }
        Label { text: "0=x/z, 1=y, 2=z"; color: Theme.gray; font.pixelSize: 9 }
    }

    RowLayout {
        Label { text: "Source"; color: Theme.text; font.pixelSize: 10; Layout.preferredWidth: 50 }
        TextField {
            objectName: "compass_source_min"
            text: compassBoundary.parameter("compass_source_min")
            placeholderText: "min"
            Layout.preferredWidth: 65
            font.pixelSize: 10
            onEditingFinished: compassBoundary.field("compass_source_min", text)
        }
        TextField {
            objectName: "compass_source_max"
            text: compassBoundary.parameter("compass_source_max")
            placeholderText: "max"
            Layout.preferredWidth: 65
            font.pixelSize: 10
            onEditingFinished: compassBoundary.field("compass_source_max", text)
        }
    }

    RowLayout {
        Label { text: "Target"; color: Theme.text; font.pixelSize: 10; Layout.preferredWidth: 50 }
        TextField {
            objectName: "compass_target_min"
            text: compassBoundary.parameter("compass_target_min")
            placeholderText: "min"
            Layout.preferredWidth: 65
            font.pixelSize: 10
            onEditingFinished: compassBoundary.field("compass_target_min", text)
        }
        TextField {
            objectName: "compass_target_max"
            text: compassBoundary.parameter("compass_target_max")
            placeholderText: "max"
            Layout.preferredWidth: 65
            font.pixelSize: 10
            onEditingFinished: compassBoundary.field("compass_target_max", text)
        }
    }

    RowLayout {
        Label { text: "R_j"; color: Theme.text; font.pixelSize: 10; Layout.preferredWidth: 50 }
        TextField {
            objectName: "compass_r_j"
            text: compassBoundary.parameter("compass_r_j")
            placeholderText: "optional"
            Layout.preferredWidth: 65
            font.pixelSize: 10
            onEditingFinished: compassBoundary.field("compass_r_j", text)
        }
    }
}
