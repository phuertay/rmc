import QtQuick
import ark.tokens as ArkTokens

/** \addtogroup details
 *  @{
 */
/*!

Text styled with typography tokens

\image html client-Typography.qml.png client
\image html paperTablet-Typography.qml.png paperTablet

\note
This is a base for all typography components and should not be used directly

*/
Text {
    id: root

    /// typography tokens
    required property var typography

    /// Default accessibility depends on ArkTokens.Settings.accessibility
    property bool accessibility: ArkTokens.Settings.accessibility

    // rest is private
    property var tokens: root.accessibility ? (ArkTokens.Style.a11y ?? ArkTokens.Style) : ArkTokens.Style

    font {
        capitalization: root.typography.textCase
        family: root.typography.fontFamily
        letterSpacing: root.typography.letterSpacing
        pixelSize: root.typography.fontSize
        weight: root.typography.fontWeight
    }
    lineHeightMode: Text.FixedHeight
    lineHeight: {
        if (root.typography.lineHeight >= root.typography.fontSize) {
            return root.typography.lineHeight
        }
        return Math.round(root.typography.fontSize * root.typography.lineHeight)
    }
    verticalAlignment: Text.AlignVCenter
}
/** @}*/
