<!--
  Icon — thin wrapper providing a stable consumer API.

  Usage: <Icon name="home" size={24} class="..." />

  Action / nav icons are inlined here with a TODO referencing the upcoming brand
  iconography iteration (per brand/README.md "next brand work is iconography
  beyond the brand mark + Holding icons"). When that iteration ships SVGs to
  brand/identity/, swap the inline paths to imports with zero consumer-side changes.

  Icons stored as inner SVG HTML strings to support multi-element glyphs (e.g.
  bell has two paths; gear has a circle + path). {@html} is safe here — all
  strings are static, hardcoded constants, never user-supplied content.

  PROCESS.md §2.4 consumer discipline: no hardcoded color values in this file.
  Icon fills use currentColor so the caller controls color via CSS.
-->
<script lang="ts">
  type IconName =
    | 'home' | 'activity' | 'holdings' | 'more'
    | 'cycle' | 'add' | 'add-circle' | 'chevron-right'
    | 'check' | 'biometric' | 'passphrase' | 'warn'
    | 'bell' | 'gear';

  let {
    name,
    size = 24,
    class: className = '',
  }: {
    name: IconName;
    size?: number;
    class?: string;
  } = $props();

  // TODO(brand-iconography): replace inline paths with imports from brand/identity/
  // once that iteration ships the icon set.
  const icons: Record<IconName, string> = {
    home:            '<path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H5a1 1 0 01-1-1V9.5z M9 21V12h6v9"/>',
    activity:        '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    holdings:        '<path d="M2 5h20v14H2zM2 9h20M6 5v14M12 5v14"/>',
    more:            '<path d="M5 12h.01M12 12h.01M19 12h.01"/>',
    cycle:           '<path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>',
    add:             '<path d="M12 5v14M5 12h14"/>',
    'add-circle':    '<path d="M12 2a10 10 0 100 20 10 10 0 000-20zM12 7v10M7 12h10"/>',
    'chevron-right': '<path d="M9 6l6 6-6 6"/>',
    check:           '<path d="M20 6L9 17l-5-5"/>',
    biometric:       '<path d="M12 4C8 4 5 7 5 11c0 3 1.5 5.5 4 7M19 11c0-3.9-3.1-7-7-7M8 11a4 4 0 008 0M12 11v3"/>',
    passphrase:      '<path d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>',
    warn:            '<path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>',
    // Bell: body path + clapper arc. Two sub-paths in the same element.
    bell:            '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    // Gear: inner circle + outer cog teeth path.
    gear:            '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  };
</script>

<svg
  xmlns="http://www.w3.org/2000/svg"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.75"
  stroke-linecap="round"
  stroke-linejoin="round"
  class={className}
  aria-hidden="true"
>
  {@html icons[name]}
</svg>
