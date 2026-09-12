import QtQuick
QtObject {
 id: root
 property string title
 property int contentWidth
 property int contentHeight
 property bool modal
 property bool frameless
 property bool isOpened: true
 property int acceptCount: 0
 property Item contentItem

 signal opened()
 function accept() { acceptCount += 1 }
 function close() {}
}
