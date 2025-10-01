# Layered SVG Generation via Context-Aware Prompting

This note explains how to extend the AI Context Framework so that text-generation
sessions can also request layered SVG artwork that is easy to post-process.
The overall idea is to treat every SVG asset as contextual knowledge, expose
that knowledge inside prompts, and let the language model describe how to reuse
and compose the pieces when new imagery is required.

## Asset Library Requirements

To keep the generated artwork editable after the fact, organise the SVG library
with the following conventions:

1. **Semantic Grouping** – Store related shapes inside `<g>` elements whose
   `id` attributes are human-readable (e.g. `hero_character/body`), so that the
   model can refer to them by name.
2. **Layer Metadata** – Add JSON or YAML sidecar files that describe the visual
   purpose of each group ("foreground character", "background gradient", etc.).
   This metadata can be ingested alongside the raw SVG markup when building the
   context packet.
3. **Reusable Palette Tokens** – Encode colours and gradients as CSS variables
   or named `<defs>` entries so that the model can remix palettes without
   editing literal hex codes.
4. **Fine-Grained Bounding Boxes** – When possible, pre-compute simple bounding
   box coordinates for key elements and store them inside the metadata so that
   downstream tooling can reposition layers with minimal geometry work.

## Context Map Structure

When you prepare a generation run, attach the SVG metadata to the context map
under a dedicated channel (e.g. `visual_assets`). Each entry should contain:

- A concise natural-language summary of the asset and its intended use.
- The path to the SVG file (or an inlined subset of its markup if the file is
  small).
- Optional references to palette tokens, font choices, and reusable backgrounds.

During prompt construction, point the model to the relevant entries by name, and
explain how the asset descriptions map to layers inside the final composition.

## Prompting Pattern

In the task prompt, request the model to output a JSON (or another structured)
plan that lists the layers to compose. For example:

```jsonc
{
  "canvas": { "width": 1920, "height": 1080 },
  "layers": [
    { "source": "characters/hero.svg#pose-1", "transform": "scale(1.1) translate(40, -20)" },
    { "source": "backgrounds/cityscape.svg#layer-base", "opacity": 0.85 },
    { "source": "effects/sun_glow.svg", "blend": "screen" }
  ]
}
```

Because the model is operating on textual context, it will not rasterise the
final artwork; instead, it will suggest which pre-existing SVG fragments to
compose, along with any transformations. A thin automation layer can then apply
these instructions with a deterministic SVG manipulation library (such as
`cairosvg`, `svgpathtools`, or browser-side DOM APIs).

## Benefits

- **Editability** – Each layer remains an SVG group, so designers can tweak the
  shapes in vector tools without recreating the entire illustration.
- **Consistency** – Palettes, iconography, and proportions stay aligned with
  existing branding guidelines because all assets originate from a controlled
  library.
- **Traceability** – The prompt output doubles as a build manifest, making it
  easy to track which assets were combined and how they were transformed.

## Limitations and Mitigations

- **Library Coverage** – The approach only works if the asset library already
  contains suitable components. Fill gaps by commissioning new base assets or
  by adding a "fallback" layer type that can be generated on the fly.
- **Prompt Budget** – Large SVG files can exhaust context length. Use summaries
  and only expose the relevant fragments when constructing the context map.
- **Geometric Precision** – Free-form text instructions may need validation.
  Couple the generation step with lightweight rules or a post-processing script
  that verifies bounds and naming before committing the composed SVG.

With these pieces in place, the framework can extend the same context-driven
workflow it uses for text to orchestrate layered, editable SVG artwork.
