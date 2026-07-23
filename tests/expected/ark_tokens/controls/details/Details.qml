// file: Details.qml
pragma Singleton
import QtQuick
import ark.tokens as ArkTokens

QtObject {
    function isProperlyConnected(state) {
        if (state == undefined)
            return false;
        for (var p in state) {
            if (typeof state[p] == "undefined") {
                return false;
            }
        }
        return true;
    }

    function isDevice() {
        return ArkTokens.Style.variable.isPaper;
    }

    function isBlack(c) {
        return (c == "#000000" || c == "#00000000" || c == "black")
    }

    function iconButtonType(foregroundColor, backgroundColor) {
        return foregroundColor < backgroundColor ? ArkTokens.IconButton.primary_inverted  : ArkTokens.IconButton.primary;
    }

    function colorFix(item, fill) {
        if (isDevice()) {
            if (!!item.fill) {
                if ([
                    ArkTokens.Style.grayscale.gray._200,
                    ArkTokens.Style.grayscale.gray._400,
                    ArkTokens.Style.grayscale.gray._500,
                    ArkTokens.Style.grayscale.gray._700
                    ].includes(item.fill)) {
                    let o = {}
                    for (var it in item) {
                        o[it] = item[it];
                    }
                    if (isBlack(fill)) {
                        o.fill = deviceWhite;
                        o.dither = deviceDitherInverted;
                    } else {
                        o.fill = deviceBlack;
                        o.dither = deviceDither;
                    }
                    return o;
                }
            }
        }
        return item;
    }

    property string iconsFamily: "icomoon"
    property color deviceBlack: "#000000"
    property color deviceWhite: "#ffffff"
    property string deviceDither: "qrc:/ark/colors/dither"
    property string deviceDitherInverted: "qrc:/ark/colors/dither_inverted"

    function overlaySource(backgroundColor) {
        if (isDevice()) {
            if (isBlack(backgroundColor)) {
                return deviceDitherInverted;
            }
            return deviceDither;
        }
        return "";
    }

    function pathTokens(path) {
        let t = path.split('.').reduce((acc, c) => acc && acc[c], ArkTokens.Style);
        if (!t) {
            console.log("ERROR: platformTokens do not contain [", path, "]");
        }
        return t;
    }
}
