import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui

Panel {
  id: root
  moduleName: "antdel.airpods"
  ipcTarget: "antdel.airpods"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  property bool running: false
  property bool connected: false
  property string mode: ""
  property var battery: ({})
  property int cursorIndex: 0
  property bool cursorActive: false
  readonly property var modes: ["anc", "transparency", "adaptive"]

  Commons.Translations {
    id: strings
    directory: Qt.resolvedUrl("i18n")
  }

  FileView {
    path: Quickshell.env("XDG_RUNTIME_DIR") + "/airpods/status.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.load(text())
    onLoadFailed: root.load("")
  }

  Process {
    id: setProc
  }

  function load(raw) {
    running = false
    connected = false
    mode = ""
    battery = {}
    if (!raw) return
    var data
    try { data = JSON.parse(raw) } catch (e) { return }
    if (!data || typeof data !== "object" || Array.isArray(data)) return
    running = true
    connected = data.connected === true
    mode = (typeof data.mode === "string" && modes.indexOf(data.mode) >= 0) ? data.mode : ""
    var bat = {}
    var src = data.battery
    if (src && typeof src === "object" && !Array.isArray(src)) {
      var keys = ["left", "right", "case"]
      for (var j = 0; j < keys.length; j++) {
        var k = keys[j]
        var entry = src[k]
        if (!entry || typeof entry !== "object" || Array.isArray(entry)) continue
        var level = entry.level
        var lvl = (typeof level === "number" && isFinite(level) && level === Math.floor(level) && level >= 0 && level <= 100) ? level : -1
        var charging = (typeof entry.charging === "boolean") ? entry.charging : null
        bat[k] = { level: lvl, charging: charging }
      }
    }
    battery = bat
  }

  function sendMode(m) {
    if (!connected || setProc.running) return
    setProc.command = ["/usr/bin/python3", "-E", "-s", "-B", decodeURIComponent(Qt.resolvedUrl("airpodsd.py").toString().replace("file://", "")), "set", m]
    setProc.running = true
  }

  function batteryEntry(k) {
    var b = battery[k]
    return b ? b : { level: -1, charging: null }
  }

  function batteryText(k) {
    var b = batteryEntry(k)
    if (b.level < 0) return "—"
    var t = Commons.I18n.formatNumber(b.level) + "%"
    if (b.charging === true) t += " " + strings.t("charging")
    return t
  }

  function barLabel() {
    if (!connected) return ""
    var lv = []
    var l = batteryEntry("left").level
    var r = batteryEntry("right").level
    if (l >= 0) lv.push(l)
    if (r >= 0) lv.push(r)
    if (lv.length === 0) return ""
    return Commons.I18n.formatNumber(Math.min.apply(null, lv)) + "%"
  }

  // Icona: MingCute airpods-fill, Apache-2.0
  component IconView: Item {
    width: Style.bar.iconSize
    height: Style.bar.iconSize
    Item {
      width: 24
      height: 24
      scale: parent.width / 24
      anchors.centerIn: parent
      Shape {
        anchors.fill: parent
        ShapePath {
          fillColor: root.barForeground
          strokeWidth: -1
          PathSvg {
            path: "M17 12.973V18c-.05 1.23-1.069 2.178-2.324 1.974a2.01 2.01 0 0 1-1.574-1.342A2 2 0 0 1 13 18V8.5c.072-2.687 2.265-4.768 4.99-4.474a4.5 4.5 0 0 1 2.525 1.133a4.52 4.52 0 0 1 1.459 2.851c.243 2.255-1.289 4.402-3.509 4.886c-.493.108-.964.104-1.465.077m-10 0c-.662.036-1.286.009-1.922-.202c-2.158-.718-3.459-3.016-2.974-5.236a4.5 4.5 0 0 1 1.381-2.376A4.5 4.5 0 0 1 6.01 4.026C8.735 3.732 10.928 5.813 11 8.5V18a2 2 0 0 1-.819 1.614C8.825 20.608 7.065 19.624 7 18Z"
          }
        }
      }
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    iconComponent: Component { IconView {} }
    slotSize: Style.bar.iconSlot * (labelText !== "" ? 2.3 : 1)
    labelText: root.barLabel()
    opacity: root.connected ? 1 : 0.45
    tooltipText: "AirPods Pro 3"
    onPressed: function(b) {
      if (b === Qt.LeftButton) root.toggle()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: panel.loadedContent
    contentWidth: panel.fittedContentWidth(Style.space(340))
    contentHeight: panel.fittedContentHeight(panel.loadedContentHeight)

    content: PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      implicitHeight: column.implicitHeight
      onMoveRequested: function(dx, dy) {
        if (!root.cursorActive) { root.cursorActive = true; return }
        var d = dy !== 0 ? dy : dx
        root.cursorIndex = Math.max(0, Math.min(2, root.cursorIndex + d))
      }
      onActivateRequested: if (root.cursorActive) root.sendMode(root.modes[root.cursorIndex])
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(12)

        Text {
          text: "AirPods Pro 3"
          textFormat: Text.PlainText
          color: root.bar ? root.bar.foreground : "white"
          font.family: root.bar ? root.bar.fontFamily : undefined
          font.pixelSize: Style.font.title
          font.bold: true
          width: parent.width
        }

        Text {
          text: !root.running ? strings.t("status.off")
              : !root.connected ? strings.t("status.disconnected")
              : strings.t("status.connected")
          textFormat: Text.PlainText
          color: {
            var c = root.bar ? root.bar.foreground : Commons.Color.foreground
            return Qt.rgba(c.r, c.g, c.b, 0.6)
          }
          font.family: root.bar ? root.bar.fontFamily : undefined
          font.pixelSize: Style.font.caption
          width: parent.width
        }

        PanelSeparator {
          width: parent.width
          foreground: root.bar ? root.bar.foreground : "white"
        }

        Item {
          width: parent.width
          implicitHeight: leftName.implicitHeight
          Label { id: leftName; text: strings.t("battery.left"); opacity: 0.6 }
          Label { text: root.batteryText("left"); anchors.right: parent.right }
        }
        Item {
          width: parent.width
          implicitHeight: rightName.implicitHeight
          Label { id: rightName; text: strings.t("battery.right"); opacity: 0.6 }
          Label { text: root.batteryText("right"); anchors.right: parent.right }
        }
        Item {
          width: parent.width
          implicitHeight: caseName.implicitHeight
          Label { id: caseName; text: strings.t("battery.case"); opacity: 0.6 }
          Label { text: root.batteryText("case"); anchors.right: parent.right }
        }

        PanelSeparator {
          width: parent.width
          foreground: root.bar ? root.bar.foreground : "white"
        }

        Row {
          width: parent.width
          spacing: Style.space(6)
          Button {
            text: strings.t("mode.anc")
            selected: root.mode === "anc"
            hasCursor: root.cursorActive && root.cursorIndex === 0
            enabled: root.connected && !setProc.running
            opacity: enabled ? 1 : 0.45
            onClicked: root.sendMode("anc")
          }
          Button {
            text: strings.t("mode.transparency")
            selected: root.mode === "transparency"
            hasCursor: root.cursorActive && root.cursorIndex === 1
            enabled: root.connected && !setProc.running
            opacity: enabled ? 1 : 0.45
            onClicked: root.sendMode("transparency")
          }
          Button {
            text: strings.t("mode.adaptive")
            selected: root.mode === "adaptive"
            hasCursor: root.cursorActive && root.cursorIndex === 2
            enabled: root.connected && !setProc.running
            opacity: enabled ? 1 : 0.45
            onClicked: root.sendMode("adaptive")
          }
        }
      }
    }
  }

  component Label: Text {
    textFormat: Text.PlainText
    color: root.bar ? root.bar.foreground : "white"
    font.family: root.bar ? root.bar.fontFamily : undefined
    font.pixelSize: Style.font.bodySmall
  }
}
