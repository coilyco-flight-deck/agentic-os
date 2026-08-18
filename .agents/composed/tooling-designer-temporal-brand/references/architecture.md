# Temporal visual architecture

Typography, scale, page shape, and the state-visualization language, read from
the shipped site and from Temporal's own account of its workflow UI.

## Typefaces

* **Aeonik** - the whole text system. Shipped weights are 100 Thin, 300 Light, 400 Regular, 500 Medium, 700 Bold, 900 Black, each with a matching italic. Body copy sits at 400 and 20px with a 140 percent line height.
* **Aeonik Air** - the 100-weight display cut, declared as a separate family rather than a weight of Aeonik, upright and italic.
* **Noto Sans Mono** - code and machine values, subsetted per script and loaded across the full weight range.

Aeonik is a geometric sans by Mark Bloom and Joe Leadbeater, released through
CoType Foundry in 2021, and it is a paid commercial license for personal and
commercial use alike. There is no free tier and no open substitute that is
metrically compatible.

## Scale

* **Spacing base** - `0.25rem`, so every spacing step is a multiple of 4px.
* **Type ramp** - 0.75, 0.875, 1, 1.125, 1.25, 1.875, 2.25, 3, 3.75 rem. Line height is computed per step and collapses to 1 at the two display sizes.
* **Tracking** - normal at 0em, wide at 0.025em, wider at 0.05em. Letter-spacing is an accent for small uppercase labels rather than a body treatment.
* **Radius** - 0.25, 0.375, 0.5, 0.75 rem. There is no pill and no fully-rounded default, so shapes stay rectangular with softened corners.
* **Containers** - 20, 24, 28, 32, 36, 42, 48, 56, 72, 80 rem. Reading columns land in the 42 to 48 rem band and full-bleed sections use 72 to 80.
* **Motion** - 0.15s default duration on a `cubic-bezier(.4, 0, .2, 1)` ease. Transitions are short enough to read as response rather than animation.
* **Blur** - 8px and 12px only, used for backdrop layers such as the translucent navigation submenu over `#141414d9`.
* **Shadow** - a single soft drop shadow at `0 4px 4px #00000026`. Depth comes from surface value, not from stacked shadows.

## Page architecture

* **Navigation** - a persistent top bar over the dark ground, with grouped submenus on a translucent Space Black panel. Groups are Platform, Use Cases, Resources, plus flat Pricing and Docs, then a trial call to action and log in.
* **Announcement bar** - an optional full-width strip above the navigation, colored per campaign rather than from the palette.
* **Body** - a single column on a dark ground, with sections that flip to the inverse light surface when the content needs to read as document rather than product.
* **Footer** - multi-column link groups plus social icons, closing every page with the same map.

## Article architecture

Read from the new-UI article, which is representative of the blog template.

* **Header block** - category chip, then title, then a metadata row of author, publish date, category, and a reading-duration badge. Topic tags sit below.
* **Body** - a single measured column with generous outer margin and no sidebar. Headings are H2 only, each with an anchor link, and the article moves from heading straight to prose without an H3 tier.
* **Progression** - the section order is a difficulty ramp. The new-UI article runs Compact, then Timeline, then Full History, so the reader meets the simplest view first and each later view adds detail to a shape already learned.
* **Figures** - product screenshots inline within their section, full-width to the text column and unframed, numbered per section.
* **Emphasis** - bold marks the term being defined on first use, which does the work a glossary would.
* **Close** - a share row, a related-posts module of two, a product call to action, then the global footer.
* **Rhetoric** - open by naming the tension in the problem rather than the product, develop by defining vocabulary before showing screens, close on how to turn the thing on and how to send feedback.

## The state-visualization language

Temporal's workflow views separate state into five channels, each answering one
question. This is the transferable part.

* **Dots** - one dot is one event, and position carries sequence.
* **Lines** - a line connects events. Thick line means event group in the compact view, thin line means detail in the full history view and also connects back to the main workflow line. A dashed line animating forward means pending.
* **Icons** - category only. The set is Activity, Child Workflow, Command, Local Activity, Marker, Signal, Timer, Update, Workflow.
* **Colors** - status first, category only as a secondary echo. Red is failure, dashed red is retrying, dashed purple is pending, green is completion. Color is meant to jump out as what happened.
* **Liveness** - the view updates in real time as events arrive, and pending activities render attached to their activity rather than in a separate region.

Two structural moves are worth borrowing beyond the visuals. The first is the
Event Group, a named collection of related raw events that the interface treats
as one unit so the reader is not asked to reassemble it. The second is offering
three fixed views over the same data at increasing resolution rather than one
configurable view, which lets each view be tuned instead of compromised.

Themes ship as Day and Night across all pages, and the new views were released
behind a Labs Mode toggle before becoming default.
