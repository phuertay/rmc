import QtQuick
import ark.tokens as ArkTokens

/** \addtogroup controls
 *  @{
 */

/*!

Text styled as title

### Usage example
\code
    ArkControls.Title {
        type: ArkControls.Title.Large
        text: "Title Large"
    }
\endcode

*/
Typography {
    id: root
    /// \ref Type. Default is Medium
    property int type: Title.Type.Medium

    /*!
       Title style

        - Medium
        - MediumAlt
        - Large
        - XLarge,
        - X2Large
    */
    enum Type {
        Medium, //< Values for text style
        MediumAlt,
        Large,
        XLarge,
        X2Large
        
    }

    // rest is private and should not be changed
    typography: Details.pathTokens((root.accessibility ? "a11y." : "") + ["title.md", "title.md_alt", "title.lg", "title.xl", "title.x2l"][root.type])
}


/** @}*/
