import QtQuick
import ark.tokens as ArkTokens

/** \addtogroup controls
 *  @{
 */

/*!

Styled text 

\image html client-Typography.qml.png Client
\image html paperTablet-Typography.qml.png paperTablet

### Usage example
\code
    ArkControls.Caption {
        text: "Caption"
    }
\endcode

*/
Typography {
    id: root
    typography: Details.pathTokens((root.accessibility ? "a11y." : "") + "caption.md")
}
/** @}*/
