<!--
  BottomNav — four-tab bottom navigation bar.

  Tabs: Home | Activity | Holdings | More
  Active tab controlled by `active` prop. Disabled tabs (e.g. Activity when empty)
  are greyed out and non-interactive until their iteration ships.

  Tab set is not locked — sharpens with the Settings + Activity iterations
  (per next_iteration.md pre-bagged decisions).
-->
<script lang="ts">
  import Icon from './Icon.svelte';

  let {
    active = 'home',
    activityDisabled = false,
    holdingsDisabled = false,
  }: {
    active?: 'home' | 'activity' | 'holdings' | 'more';
    activityDisabled?: boolean;
    holdingsDisabled?: boolean;
  } = $props();

  const tabs = [
    { id: 'home',      label: 'Home',     icon: 'home'     },
    { id: 'activity',  label: 'Activity', icon: 'activity' },
    { id: 'holdings',  label: 'Holdings', icon: 'holdings' },
    { id: 'more',      label: 'More',     icon: 'more'     },
  ] as const;

  function isDisabled(id: string): boolean {
    if (id === 'activity') return activityDisabled;
    if (id === 'holdings') return holdingsDisabled;
    return false;
  }

  function href(id: string): string {
    if (id === 'home') return '/home';
    if (id === 'more') return '/more';
    return '#'; // placeholder until those iterations ship
  }
</script>

<nav class="bottom-nav" aria-label="Main navigation">
  {#each tabs as tab (tab.id)}
    {@const disabled = isDisabled(tab.id)}
    {@const isActive = active === tab.id}
    <a
      href={href(tab.id)}
      class="nav-tab"
      class:active={isActive}
      class:disabled
      aria-current={isActive ? 'page' : undefined}
      aria-disabled={disabled}
      tabindex={disabled ? -1 : 0}
    >
      <Icon name={tab.icon} size={22} />
      <span class="tab-label">{tab.label}</span>
    </a>
  {/each}
</nav>

<style>
  .bottom-nav {
    position: fixed;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: var(--mobile-viewport-width);
    height: var(--mobile-bottom-nav);
    background: var(--color-surface);
    border-top: 1px solid var(--color-border);
    display: flex;
    align-items: stretch;
    z-index: 100;
    padding-bottom: env(safe-area-inset-bottom, 0);
  }
  .nav-tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    color: var(--color-text-dim);
    text-decoration: none;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
    transition: color 0.1s;
  }
  .nav-tab.active {
    color: var(--color-primary);
  }
  .nav-tab.disabled {
    pointer-events: none;
    opacity: 0.35;
  }
  .tab-label {
    font-size: 10px;
    letter-spacing: 0.01em;
  }
</style>
