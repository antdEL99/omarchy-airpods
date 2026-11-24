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
  readonly property color fg: root.bar ? root.bar.foreground : Commons.Color.foreground
  readonly property string ff: root.bar ? root.bar.fontFamily : Style.font.family
  function lvl(k) { return batteryEntry(k).level }
  function statusText() { return !running ? strings.t("status.off") : !connected ? strings.t("status.disconnected") : strings.t("status.connected") }


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
    id: iconRoot
    property real size: Style.bar.iconSize
    property color tint: root.barForeground
    width: size
    height: size
    Item {
      width: 24
      height: 24
      scale: parent.width / 24
      anchors.centerIn: parent
      Shape {
        anchors.fill: parent
        ShapePath {
          fillColor: iconRoot.tint
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

        Item {
          width: column.width
          implicitHeight: titleL.implicitHeight
          Label { id: titleL; text: "AirPods Pro 3"; font.bold: true; font.pixelSize: Style.font.title }
          Label { text: root.statusText(); opacity: 0.6; anchors.right: parent.right; anchors.baseline: titleL.baseline }
        }
        Row {
          id: cells
          width: column.width
          spacing: Style.space(10)
          Repeater {
            model: ["left", "right", "case"]
            delegate: Column {
              required property string modelData
              width: (cells.width - cells.spacing * 2) / 3
              spacing: Style.space(4)
              Label {
                text: root.lvl(modelData) < 0 ? "—" : Commons.I18n.formatNumber(root.lvl(modelData)) + "%"
                font.pixelSize: Style.font.display
                font.bold: true
              }
              Rectangle {
                width: parent.width; height: Style.space(3); radius: height / 2
                color: Qt.rgba(root.fg.r, root.fg.g, root.fg.b, 0.15)
                Rectangle {
                  width: parent.width * Math.max(0, root.lvl(modelData)) / 100; height: parent.height; radius: parent.radius
                  color: root.batteryEntry(modelData).charging === true ? Commons.Color.accent : root.fg
                }
              }
              Label {
                text: strings.t("battery." + modelData) + (root.batteryEntry(modelData).charging === true ? " · " + strings.t("charging") : "")
                opacity: 0.6
                font.pixelSize: Style.font.caption
                width: parent.width
                elide: Text.ElideRight
              }
            }
          }
        }
        PanelSeparator { foreground: root.fg }
        Repeater {
          model: root.modes
          delegate: Button {
            required property string modelData
            required property int index
            width: column.width
            leftAlign: true
            text: strings.t("mode." + modelData)
            selected: root.mode === modelData
            hasCursor: root.cursorActive && root.cursorIndex === index
            foreground: root.fg
            fontFamily: root.ff
            enabled: root.connected && !setProc.running
            opacity: enabled ? 1 : 0.45
            onHovered: function(on) { if (on) { root.cursorActive = true; root.cursorIndex = index } }
            onClicked: root.sendMode(modelData)
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
