<!--
  WordmarkIcony — the "tally[Y]keep" wordmark with embedded icon.

  SVG paths mirror brand/identity/wordmark-icony.svg. Paint layers use
  .mark-wood / .mark-grain / .mark-carving / .mark-text class hooks so the
  active palette (tokens.css --brand-mark-* vars) drives the colors without
  hardcoded fills (PROCESS.md §2.4 consumer discipline).

  viewBox 0 0 450 145 matches the v2 source SVG (specs/brand/identity/wordmark-icony.svg).
  The v1 source was 0 0 460 145; tightened in Brand T14 to crop trailing right-side
  padding so the wordmark centers correctly in a fixed-width container.

  Static rendering only — the dynamic-mark (tap-to-regenerate-grain) behavior
  is deferred to future_iterations.md "Dynamic brand mark on first-touch surfaces".
-->
<script lang="ts">
  let { width = 280, class: className = '' }: { width?: number; class?: string } = $props();
</script>

<svg
  class="wordmark-icony {className}"
  style="width: {width}px; height: auto; display: block;"
  viewBox="0 0 450 145"
  xmlns="http://www.w3.org/2000/svg"
  aria-label="tallykeep"
  role="img"
>
  <text
    x="0"
    y="92"
    font-family="Manrope, system-ui, sans-serif"
    font-weight="600"
    font-size="92"
    letter-spacing="-2"
    class="mark-text"
  >tall</text>

  <!-- The Y-icon, scaled and positioned between "tall" and "keep" -->
  <svg x="143" y="42" width="76" height="84" viewBox="36.43 27.79 131.9 146.43">
    <defs>
      <clipPath id="wm-stock-clip">
        <path d="M 168.33 42.19 L 54.27 174.22 L 36.43 139.77 L 54.47 118.86 L 65.07 128.02 L 151.67 27.81 Z" />
      </clipPath>
      <clipPath id="wm-foil-clip">
        <polygon points="40.68,42.21 79.68,87.21 96.32,72.79 57.32,27.79" />
      </clipPath>
    </defs>
    <!-- Stock body -->
    <path
      d="M 168.33 42.19 L 54.27 174.22 L 36.43 139.77 L 54.47 118.86 L 65.07 128.02 L 151.67 27.81 Z"
      class="mark-wood"
    />
    <!-- Foil body -->
    <polygon
      points="40.68,42.21 79.68,87.21 96.32,72.79 57.32,27.79"
      class="mark-wood"
    />
    <!-- Grain stripes -->
    <g class="mark-grain" stroke-width="1.4" stroke-linecap="butt" opacity="0.6">
      <line x1="163.79" y1="38.27" x2="46.07" y2="174.53" clip-path="url(#wm-stock-clip)" />
      <line x1="156.22" y1="31.73" x2="38.50" y2="167.99" clip-path="url(#wm-stock-clip)" />
      <line x1="45.22" y1="38.27" x2="84.52" y2="83.64" clip-path="url(#wm-foil-clip)" />
      <line x1="52.78" y1="31.73" x2="92.08" y2="77.09" clip-path="url(#wm-foil-clip)" />
    </g>
    <!-- Carvings (hanging hole + notch set) -->
    <circle cx="53.76" cy="147.31" r="2.8" class="mark-carving" />
    <polygon points="-3,12 3,12 2,5 -2,5"     class="mark-carving" transform="translate(147 50) rotate(130.82)" />
    <polygon points="-4,12 4,12 2,4 -2,4"     class="mark-carving" transform="translate(140 58) rotate(130.82)" />
    <polygon points="-3,12 3,12 2,5 -2,5"     class="mark-carving" transform="translate(133 66) rotate(130.82)" />
    <polygon points="-3,-12 3,-12 2,-5 -2,-5"  class="mark-carving" transform="translate(62 50)  rotate(49.18)" />
    <polygon points="-4,-12 4,-12 2,-4 -2,-4"  class="mark-carving" transform="translate(69 58)  rotate(49.18)" />
    <polygon points="-3,-12 3,-12 2,-5 -2,-5"  class="mark-carving" transform="translate(76 66)  rotate(49.18)" />
  </svg>

  <text
    x="228"
    y="92"
    font-family="Manrope, system-ui, sans-serif"
    font-weight="600"
    font-size="92"
    letter-spacing="-2"
    class="mark-text"
  >keep</text>
</svg>
