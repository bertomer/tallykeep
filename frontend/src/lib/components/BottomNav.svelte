<!--
  BottomNav — three-tab bottom navigation bar (ADR-0019).

  Tabs: Home | Security Health | Activity
  Active tab controlled by `active` prop.
  Security Health tab shows a red pill badge when criticalCount > 0 (critical-only per ADR-0019).
-->
<script lang="ts">
  import Icon from './Icon.svelte';

  let {
    active = 'home',
    criticalCount = 0,
  }: {
    active?: 'home' | 'security' | 'activity';
    criticalCount?: number;
  } = $props();

  const tabs = [
    { id: 'home',     label: 'Home',     icon: 'home',     href: '/home' },
    { id: 'security', label: 'Security', icon: 'bell',     href: '/security-health' },
    { id: 'activity', label: 'Activity', icon: 'activity', href: '/activity' },
  ] as const;
</script>

<nav class="bottom-nav" aria-label="Main navigation">
  {#each tabs as tab (tab.id)}
    {@const isActive = active === tab.id}
    <a
      href={tab.href}
      class="nav-tab"
      class:active={isActive}
      aria-current={isActive ? 'page' : undefined}
    >
      {#if tab.id === 'security'}
        <span class="bell-wrap">
          <Icon name="bell" size={22} />
          {#if criticalCount > 0}
            <span class="nav-badge" aria-label="{criticalCount} critical security item{criticalCount === 1 ? '' : 's'}">{criticalCount}</span>
          {/if}
        </span>
      {:else}
        <Icon name={tab.icon} size={22} />
      {/if}
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
    color: var(--color-primary-strong);
    font-weight: var(--font-weight-semibold);
    position: relative;
  }
  .nav-tab.active::before {
    content: '';
    position: absolute;
    top: 0;
    left: 20%;
    right: 20%;
    height: 2px;
    background: var(--color-primary);
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
  }
  .tab-label {
    font-size: 10px;
    letter-spacing: 0.01em;
  }

  /* Bell wrapper allows absolute-positioned badge */
  .bell-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
  }

  /* Red pill badge — critical items only, per ADR-0019 */
  .nav-badge {
    position: absolute;
    top: -4px;
    right: -8px;
    min-width: 16px;
    height: 16px;
    padding: 0 4px;
    border-radius: var(--radius-pill);
    background: var(--color-danger);
    color: #ffffff;
    font-size: 10px;
    font-weight: var(--font-weight-semibold);
    font-family: var(--font-sans);
    line-height: 16px;
    text-align: center;
    box-sizing: border-box;
    border: 1.5px solid var(--color-surface);
    pointer-events: none;
  }
</style>
