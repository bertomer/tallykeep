<!--
  Icon — thin wrapper providing a stable consumer API.

  Usage: <Icon name="home" size={24} class="..." />

  Action / nav icons (home, activity, holdings, more, cycle, add) are inlined here
  with a TODO referencing the upcoming brand iconography iteration (per brand/README.md
  "next brand work is iconography beyond the brand mark + Holding icons").
  When that iteration ships SVGs to brand/identity/, swap the inline paths to imports
  with zero consumer-side changes.

  PROCESS.md §2.4 consumer discipline: no hardcoded color values in this file.
  Icon fills use currentColor so the caller controls color via CSS.
-->
<script lang="ts">
  type IconName =
    | 'home' | 'activity' | 'holdings' | 'more'
    | 'cycle' | 'add' | 'add-circle' | 'chevron-right'
    | 'check' | 'biometric' | 'passphrase' | 'warn';

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
  const paths: Record<IconName, string> = {
    home: 'M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H5a1 1 0 01-1-1V9.5z M9 21V12h6v9',
    activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
    holdings: 'M2 5h20v14H2zM2 9h20M6 5v14M12 5v14',
    more: 'M5 12h.01M12 12h.01M19 12h.01',
    cycle: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
    add: 'M12 5v14M5 12h14',
    'add-circle': 'M12 2a10 10 0 100 20 10 10 0 000-20zM12 7v10M7 12h10',
    'chevron-right': 'M9 6l6 6-6 6',
    check: 'M20 6L9 17l-5-5',
    biometric: 'M12 4C8 4 5 7 5 11c0 3 1.5 5.5 4 7M19 11c0-3.9-3.1-7-7-7M8 11a4 4 0 008 0M12 11v3',
    passphrase: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z',
    warn: 'M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z',
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
  <path d={paths[name]} />
</svg>
