import { createCn } from "cn/config"

// Arrendi's type scale (see app/globals.css). Without this, the merge takes
// `text-body` for a color and drops it when a text color follows.
const FONT_SIZES = [
  "figure",
  "title-onboarding",
  "title",
  "title-back",
  "kpi",
  "body",
  "section",
  "support",
  "badge",
]

export const cn = createCn({
  extend: { classGroups: { "font-size": [{ text: FONT_SIZES }] } },
})
