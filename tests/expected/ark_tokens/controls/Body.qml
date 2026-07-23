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
    ArkControls.Body {
        type: ArkControls.Body.MediumStrong
        text: "Body Text"
    }
\endcode
*/
Typography {
    id: root

    /// Use \ref Type to change text size and weight. Default is Medium
    property var type: Body.Type.Medium

    /*!
       Body types

        - Medium
        - MediumLow
        - MediumStrong
        - Small
        - Large
    */
    enum Type {
        Medium, //< Values for text style
        MediumLow,
        MediumStrong,
        Small,
        Large
    }

    typography: Details.pathTokens((root.accessibility ? "a11y." : "") + ["body.md", "body.md_low", "body.md_strong", "body.sm", "body.lg"][root.type])
}
/** @}*/
