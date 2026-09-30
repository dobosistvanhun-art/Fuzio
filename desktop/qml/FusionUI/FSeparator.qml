import QtQuick
Rectangle { property bool vertical: false; color: Theme.border
    implicitWidth: vertical ? 1 : 10; implicitHeight: vertical ? 10 : 1 }
