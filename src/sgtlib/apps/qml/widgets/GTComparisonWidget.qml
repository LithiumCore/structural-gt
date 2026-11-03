pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Theme 1.0

Item {
    id: comparisonTable
    Layout.preferredWidth: parent.width - 10
    Layout.preferredHeight: graphComparisonModel.rowCount() * 66 + 44
    Layout.leftMargin: 5

    function displayValue(rowIndex, columnIndex) {
        const value = graphComparisonModel.data(
            graphComparisonModel.index(rowIndex, columnIndex), Qt.DisplayRole
        )
        if (typeof value === "number") {
            if (!Number.isFinite(value))
                return "Undefined"
            return Number.isInteger(value) ? value.toString() : Number(value.toPrecision(5)).toString()
        }
        return value
    }

    Column {
        width: parent.width

        Row {
            width: parent.width
            height: 38
            Repeater {
                model: ["Metric", "Dickson", "COMPASS", "Abs. Δ", "Rel. Δ %"]
                delegate: Rectangle {
                    id: headerCell
                    required property var modelData
                    width: comparisonTable.width / 5
                    height: 38
                    color: Theme.lightGray
                    Text {
                        anchors.fill: parent
                        anchors.margins: 2
                        text: headerCell.modelData
                        wrapMode: Text.Wrap
                        font.pixelSize: 9
                        font.bold: true
                        color: Theme.darkGray
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        Repeater {
            model: graphComparisonModel.rowCount()
            delegate: Row {
                id: comparisonRow
                required property int modelData
                width: comparisonTable.width
                height: 66
                Repeater {
                    model: 5
                    delegate: Rectangle {
                        id: valueCell
                        required property int index
                        width: comparisonTable.width / 5
                        height: 66
                        color: comparisonRow.rowIndex % 2 === 0 ? Theme.smokeWhite : Theme.white
                        Text {
                            anchors.fill: parent
                            anchors.margins: 3
                            text: comparisonTable.displayValue(comparisonRow.rowIndex, valueCell.index)
                            wrapMode: Text.Wrap
                            font.pixelSize: 8
                            color: Theme.darkGray
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
                property int rowIndex: modelData
            }
        }
    }
}
