# Lenny Lens Design Notes

## Design intent

Lenny Lens should feel like a research workspace, not a novelty chatbot. The visual hierarchy gives the answer room to read, makes citations easy to inspect, and keeps a generated artifact visible without forcing a new tab.

## Information architecture

- **Left rail:** Start a new research thread, recover previous sessions, and inspect active model state.
- **Main workspace:** Conversation, evidence receipt, individual sources, and artifact creation controls.
- **Right pane:** Markdown/HTML artifact rendering, safe download, and visible sandbox status.

## Key interaction states

| State | User-visible treatment |
| --- | --- |
| Initial session | A concise explanation and three practical research prompts |
| Thinking/retrieval | Composer locks with a clear “Researching” state |
| Successful answer | Markdown answer, source cards, expandable evidence receipt, artifact actions |
| Missing source support | Direct acknowledgement, no decorative source list, suggested refinement |
| Provider unavailable | Provider rail status and structured visible error; no implied cloud fallback |
| Artifact open | Persistent split pane on desktop, full-screen safe viewer on mobile |

## Visual system

The interface uses a calm off-white canvas, a dark research rail, and restrained indigo for interaction and model status. Fraunces gives conclusions and section headings a deliberate editorial character; DM Sans maintains readability in dense evidence areas; DM Mono is reserved for system metadata.

This combination makes the product feel like a trusted research instrument rather than a generic AI interface.

## Responsive behavior

- Wide screens: three-column research, chat, and artifact workspace.
- Medium screens: narrower but persistent artifact panel.
- Small screens: sidebar disappears and artifact viewer becomes a focused full-screen layer.
- All action targets retain keyboard focus and readable contrast.

## Accessibility

- Semantic `main`, `aside`, `nav`, `article`, `section`, `header`, and `footer` landmarks.
- Visible focus rings and buttons with labels/tooltips.
- Source links use descriptive episode and guest labels, rather than unnamed URLs.
- Error uses `role="alert"`; conversation uses polite live region.
- The viewer iframe has a title, and markdown does not rely on color alone for meaning.

## Security as UX

Artifact safety is stated in the viewer rather than hidden. “Sandboxed preview” gives the evaluator and user a clear explanation for why scripts and outside URLs do not work in artifacts.
