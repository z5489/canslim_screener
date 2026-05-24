# Responsive Web & Mobile UI/UX Optimization Skill

This skill provides mandatory instructions for optimizing React and Tailwind CSS components for BOTH desktop monitors and mobile devices. 

**CRITICAL RULE:** Whenever you are instructed to optimize a UI for mobile, you MUST simultaneously evaluate and protect the desktop layout. A change that fixes mobile but breaks desktop (or vice versa) is considered a complete failure.

## 1. Holistic Responsive Layouts
- **Test Across Breakpoints:** When adding mobile classes (like `flex-col` or `flex-wrap`), always add the corresponding desktop class (e.g., `md:flex-row`, `xl:flex-nowrap`) to ensure the desktop layout is explicitly preserved.
- **Prevent Stretching on Desktop:** Flex items with `flex-1` can stretch infinitely on wide desktop monitors if a sibling container wraps or shrinks. Always cap wide inputs or search bars with `max-w-md` or `max-w-lg` to prevent absurd proportions.
- **Graceful Wrapping:** Use `flex-wrap` carefully. If wrapping is only needed for small screens, limit it with `flex-wrap xl:flex-nowrap` so desktop users get a clean, single-line view.

## 2. Optimizing Data Tables for All Screens
- **Avoid Screen Cutoffs:** Desktop users might not realize horizontal scrolling is required if the scrollbar is hidden at the bottom of a tall page.
- **Scrollable Frames:** Wrap wide tables in a vertically scrollable frame (`max-h-[70vh] overflow-auto`). This guarantees that both the vertical and horizontal scrollbars are always visible on the screen.
- **Sticky Headers & Columns:** Make table headers sticky (`sticky top-0 z-30`) and key identifier columns sticky (`sticky left-0 z-40`) so users never lose their context while scrolling.
- **Intrinsic vs Fixed Widths:** For tables with many columns, prevent stretching columns (like a long string in a "Focus" column) by enforcing a `max-w` and using `truncate`. This ensures all columns can fit on standard desktop monitors without needing horizontal scrolling whenever possible.
- **Compact Data Padding:** If a table has 10+ columns, use tighter padding (`px-2.5` or `px-3` instead of `px-4`) to maximize data density on desktop screens.

## 3. Touch Targets & Spacing
- Ensure all interactive elements (buttons, selects, inputs) have sufficient padding (e.g., `py-2.5 px-4`) to serve as comfortable touch targets for fingers on mobile.
- Use responsive spacing gaps (e.g., `gap-3 md:gap-4`) to maintain tight, clean looks on mobile while opening up comfortably on desktop.

Execute these principles rigorously whenever working on the frontend to ensure a premium, faultless experience on every device.
