// file: rM-paper-tablet.json.qml
pragma Singleton
import QtQuick
QtObject {
  id: root
  property int dividerSize : 2
  property int handleSize : 32
  property int iconSize : 40
  property int indicatorSize : 16
  property int indicatorToolButton : 12
  property int notchHeight : 18
  property int progressBarLargeSize : 40
  property int progressBarSmallSize : 16
  property int tooltipHeight : 185
  property int tooltipWidth : 730
  property int underlineSize : 2
  property var a11y: QtObject {
    property var body: QtObject {
      property var lg: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var md: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var md_low: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.1
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var md_strong: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Bold
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var sm: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 32
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
    }
    property var caption: QtObject {
      property var md: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 28
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
    }
    property var label: QtObject {
      property var lg_strong: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Bold
        property int letterSpacing : 0
        property real lineHeight : 1.55
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var lg_subtle: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Medium
        property int letterSpacing : 0
        property real lineHeight : 1.55
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var md: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 32
        property int fontWeight : Font.Medium
        property int letterSpacing : 0
        property real lineHeight : 1.49
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var sm_strong: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 28
        property int fontWeight : Font.Bold
        property int letterSpacing : 0
        property real lineHeight : 1.56
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var sm_strong_low: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 28
        property int fontWeight : Font.Bold
        property int letterSpacing : 0
        property int lineHeight : 34
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var sm_subtle: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 28
        property int fontWeight : Font.Medium
        property int letterSpacing : 0
        property real lineHeight : 1.56
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var sm_subtle_low: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 28
        property int fontWeight : Font.Medium
        property int letterSpacing : 0
        property int lineHeight : 34
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var xl_strong: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 44
        property int fontWeight : Font.Bold
        property int letterSpacing : 0
        property real lineHeight : 1.55
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var xl_subtle: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 44
        property int fontWeight : Font.Medium
        property int letterSpacing : 0
        property real lineHeight : 1.55
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
    }
    property var list: QtObject {
      property var lg: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 24
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var lg_compact: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 16
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var md: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 16
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
    }
    property var title: QtObject {
      property var lg: QtObject {
        property string fontFamily : "reMarkable Serif Small"
        property int fontSize : 54
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.25
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var md: QtObject {
        property string fontFamily : "reMarkable Sans"
        property int fontSize : 36
        property int fontWeight : Font.Bold
        property int letterSpacing : 0
        property real lineHeight : 1.5
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var md_alt: QtObject {
        property string fontFamily : "reMarkable Serif Small"
        property int fontSize : 48
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.25
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var x2l: QtObject {
        property string fontFamily : "reMarkable Serif Small"
        property int fontSize : 84
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property real lineHeight : 1.1
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
      property var xl: QtObject {
        property string fontFamily : "reMarkable Serif Small"
        property int fontSize : 68
        property int fontWeight : Font.Normal
        property int letterSpacing : 0
        property int lineHeight : 85
        property int paragraphSpacing : 0
        property int textCase : Font.MixedCase
        property bool textDecoration : false
      }
    }
  }
  property var body: QtObject {
    property var lg: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 36
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var md: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 28
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var md_low: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 28
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.1
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var md_strong: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 28
      property int fontWeight : Font.Bold
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var sm: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 25
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var sm_hidden: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 42
      property int fontWeight : Font.Bold
      property int letterSpacing : 4
      property real lineHeight : 1.5
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
  }
  property var borderWidth: QtObject {
    property int idle : 2
    property int thick : 4
  }
  property var caption: QtObject {
    property var md: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 22
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property int lineHeight : 32
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
  }
  property var divider: QtObject {
    property color color : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
    property var style : "solid"
    property int width : 2
  }
  property var divider_inverted: QtObject {
    property color color : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
    property var style : "solid"
    property int width : 2
  }
  property var focus: QtObject {
    property color inFocus : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
    property color inFocus_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
    property var offset: QtObject {
      property int medium : 8
      property int small : -4
    }
  }
  property var interaction: QtObject {
    property var bg: QtObject {
      property color idle : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color default_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color disabled : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color disabled_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color selected : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color selected_alt : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color selected_alt_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color selected_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
    }
    property var border: QtObject {
      property color idle : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color default_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color disabled : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color disabled_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color selected : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color selected_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
    }
    property var icon: QtObject {
      property color idle : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color default_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color disabled : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#959595")) : Qt.color("#959595")
      property color disabled_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#3b3b3b")) : Qt.color("#3b3b3b")
      property color selected : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color selected_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
    }
    property var text: QtObject {
      property color idle : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color default_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color disabled : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#959595")) : Qt.color("#959595")
      property color disabled_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#3b3b3b")) : Qt.color("#3b3b3b")
      property color selected : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color selected_alt : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color selected_alt_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color selected_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
    }
  }
  property var idle: QtObject {
    property var bg: QtObject {
      property color primary : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color primary_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color secondary : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color secondary_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color tertiary : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color tertiary_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
    }
    property var border: QtObject {
      property color primary : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color primary_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color secondary : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color secondary_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
    }
    property var text: QtObject {
      property color primary : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color primary_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
      property color secondary : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
      property color secondary_inv : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
    }
  }
  property var label: QtObject {
    property var lg_strong: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 28
      property int fontWeight : Font.Bold
      property int letterSpacing : 0
      property real lineHeight : 1.56
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var lg_subtle: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 28
      property int fontWeight : Font.Medium
      property int letterSpacing : 0
      property real lineHeight : 1.56
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var md: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 25
      property int fontWeight : Font.Medium
      property int letterSpacing : 0
      property real lineHeight : 1.58
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var sm_strong: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 22
      property int fontWeight : Font.Bold
      property int letterSpacing : 0
      property real lineHeight : 1.44
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var sm_strong_low: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 22
      property int fontWeight : Font.Bold
      property int letterSpacing : 0
      property real lineHeight : 1.18
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var sm_subtle: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 22
      property int fontWeight : Font.Medium
      property int letterSpacing : 0
      property real lineHeight : 1.44
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var sm_subtle_low: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 22
      property int fontWeight : Font.Medium
      property int letterSpacing : 0
      property real lineHeight : 1.18
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var xl_strong: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 36
      property int fontWeight : Font.Bold
      property int letterSpacing : 0
      property real lineHeight : 1.56
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var xl_subtle: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 36
      property int fontWeight : Font.Medium
      property int letterSpacing : 0
      property real lineHeight : 1.56
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
  }
  property var lineHeight: QtObject {
    property var label: QtObject {
      property real large : 1.56
      property real medium : 1.58
      property real small : 1.44
    }
  }
  property var list: QtObject {
    property var lg: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 36
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 24
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var lg_compact: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 36
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 16
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var md: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 28
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 16
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
  }
  property var longpress: QtObject {
    property var offset: QtObject {
      property int small : -4
    }
  }
  property var margin: QtObject {
    property var landscape: QtObject {
      property var horizontal: QtObject {
        property int large : 176
        property int medium : 117
        property int medium_static : 32
        property int none : 0
        property int small : 59
        property int small_static : 16
        property int x2large : 351
        property int x3large : 468
        property int xlarge : 234
      }
      property var vertical: QtObject {
        property int large : 132
        property int medium : 88
        property int medium_static : 32
        property int none : 0
        property int small : 44
        property int small_static : 16
        property int x2large : 263
        property int x3large : 351
        property int xlarge : 176
      }
    }
    property var portrait: QtObject {
      property var horizontal: QtObject {
        property int large : 132
        property int medium : 88
        property int medium_static : 32
        property int none : 0
        property int small : 44
        property int small_static : 16
        property int x2large : 263
        property int x3large : 351
        property int xlarge : 176
      }
      property var vertical: QtObject {
        property int large : 176
        property int medium : 117
        property int medium_static : 32
        property int none : 0
        property int small : 59
        property int small_static : 16
        property int x2large : 351
        property int x3large : 468
        property int xlarge : 234
      }
    }
  }
  property var optionalBorder: QtObject {
    property color color : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#000000")) : Qt.color("#000000")
    property var style : "solid"
    property int width : 2
  }
  property var optionalBorder_inverted: QtObject {
    property color color : Settings.usingDebugColors ? Settings.convertColor(Qt.color("#ffffff")) : Qt.color("#ffffff")
    property var style : "solid"
    property int width : 2
  }
  property var padding: QtObject {
    property int large : 32
    property int medium : 24
    property int none : 0
    property int small : 16
    property int small_alt : 16
    property int x2small : 4
    property int x3small : 2
    property int xlarge : 40
    property int xlarge_alt : 64
    property int xsmall : 8
  }
  property var radius: QtObject {
    property int large : 16
    property int max : 79992
    property int medium : 8
    property int none : 0
    property int small : 0
  }
  property var sizing: QtObject {
    property int large : 32
    property int medium : 24
    property int small : 16
    property int x2large : 48
    property int x3large : 64
    property int x4large : 80
    property int x5large : 120
    property int xlarge : 40
    property int xsmall : 8
  }
  property var spacing: QtObject {
    property int large : 40
    property int medium : 24
    property int none : 0
    property int small : 16
    property int x2large : 160
    property int x2small : 4
    property int x3small : 2
    property int xlarge : 80
    property int xsmall : 8
  }
  property var title: QtObject {
    property var lg: QtObject {
      property string fontFamily : "reMarkable Serif Small"
      property int fontSize : 48
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.25
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var md: QtObject {
      property string fontFamily : "reMarkable Sans"
      property int fontSize : 28
      property int fontWeight : Font.Bold
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var md_alt: QtObject {
      property string fontFamily : "reMarkable Serif Small"
      property int fontSize : 42
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property real lineHeight : 1.5
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var x2l: QtObject {
      property string fontFamily : "reMarkable Serif Small"
      property int fontSize : 84
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property int lineHeight : 92
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
    property var xl: QtObject {
      property string fontFamily : "reMarkable Serif Small"
      property int fontSize : 68
      property int fontWeight : Font.Normal
      property int letterSpacing : 0
      property int lineHeight : 85
      property int paragraphSpacing : 0
      property int textCase : Font.MixedCase
      property bool textDecoration : false
    }
  }
  property var variable: QtObject {
    property int deviceHeight : 1872
    property int deviceWidth : 1404
    property bool enoughHorizontalSpace : true
    property bool enoughVerticalSpace : true
    property bool isPaper : true
    property string tokens : "paperTablet"
    property var controlsHeight: QtObject {
      property int large : 112
      property int medium : 96
      property int small : 80
      property int xsmall : 56
    }
    property var device: QtObject {
      property var deviceHeight: QtObject {
        property int landscape : 1404
        property int portrait : 1872
      }
      property var deviceWidth: QtObject {
        property int landscape : 1872
        property int portrait : 1404
      }
    }
    property var iconSize: QtObject {
      property int large : 64
      property int medium : 48
      property int small : 32
    }
    property var margins: QtObject {
      property var _Large: QtObject {
        property var landscape: QtObject {
          property int horizontal : 176
          property int horizontalSidebar : 530
          property int vertical : 132
        }
        property var portrait: QtObject {
          property int horizontal : 132
          property int horizontalSidebar : 486
          property int vertical : 176
        }
      }
      property var _Medium: QtObject {
        property var landscape: QtObject {
          property int horizontal : 117
          property int horizontalSidebar : 471
          property int vertical : 88
        }
        property var portrait: QtObject {
          property int horizontal : 88
          property int horizontalSidebar : 442
          property int vertical : 117
        }
      }
      property var _Small: QtObject {
        property var landscape: QtObject {
          property int horizontal : 59
          property int horizontalSidebar : 413
          property int vertical : 44
        }
        property var portrait: QtObject {
          property int horizontal : 44
          property int horizontalSidebar : 398
          property int vertical : 59
        }
      }
      property var _X2Large: QtObject {
        property var landscape: QtObject {
          property int horizontal : 351
          property int horizontalSidebar : 705
          property int vertical : 263
        }
        property var portrait: QtObject {
          property int horizontal : 263
          property int horizontalSidebar : 617
          property int vertical : 351
        }
      }
      property var _X3Large: QtObject {
        property var landscape: QtObject {
          property int horizontal : 468
          property int horizontalSidebar : 822
          property int vertical : 351
        }
        property var portrait: QtObject {
          property int horizontal : 351
          property int horizontalSidebar : 705
          property int vertical : 468
        }
      }
      property var _XLarge: QtObject {
        property var landscape: QtObject {
          property int horizontal : 234
          property int horizontalSidebar : 588
          property int vertical : 176
        }
        property var portrait: QtObject {
          property int horizontal : 176
          property int horizontalSidebar : 530
          property int vertical : 234
        }
      }
    }
    property var platform: QtObject {
      property var padding: QtObject {
        property int large : 32
        property int medium : 24
        property int none : 0
        property int small : 16
        property int x2large : 64
        property int x2small : 4
        property int x3large : 96
        property int x3small : 2
        property int xlarge : 48
        property int xsmall : 8
      }
      property var spacing: QtObject {
        property int large : 32
        property int medium : 24
        property int none : 0
        property int small : 16
        property int x2large : 64
        property int x2small : 4
        property int x3large : 96
        property int x3small : 2
        property int x5large : 128
        property int x6large : 160
        property int xlarge : 48
        property int xsmall : 8
      }
    }
    property var typography: QtObject {
      property var caption: QtObject {
        property var md: QtObject {
          property int fontSize : 22
          property int lineHeight : 32
          property var a11y: QtObject {
            property int fontSize : 22
            property int lineHeight : 42
          }
        }
      }
      property var label: QtObject {
        property var sm_strong_low: QtObject {
          property var a11y: QtObject {
            property int fontSize : 28
            property int lineHeight : 34
          }
        }
      }
      property var title: QtObject {
        property var x2l: QtObject {
          property int fontSize : 84
          property int lineHeight : 92
          property var a11y: QtObject {
            property int fontSize : 84
            property int lineHeight : 92
          }
        }
        property var xl: QtObject {
          property int fontSize : 68
          property int lineHeight : 85
          property var a11y: QtObject {
            property int fontSize : 68
            property int lineHeight : 85
          }
        }
      }
    }
  }
}