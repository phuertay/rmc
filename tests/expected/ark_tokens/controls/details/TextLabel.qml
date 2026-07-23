import QtQuick
import ark.tokens as ArkTokens

/** \addtogroup details
 *  @{
 */
/*!

Text styled with component text style (typography and color)

\note
This is a base for all text labels and should not be used directly

*/
Typography {
    id: root
    property var labelStyle
    typography: labelStyle?.typography ?? ArkTokens.Style.label.md
    color: labelStyle?.fill ?? "red"

    // Only Text with renderType of Text.NativeRendering can disable antialiasing.
    // We assume that if component does want to turn off antialiasing all its labels should comply
    Binding on renderType {
        when: !antialiasing
        value: Text.NativeRendering
    }
}
/** @}*/
