<script lang="ts">
  let { type, size = 32 }: { type: string; size?: number } = $props();
</script>

{#if type === 'account'}
  <svg width={size} height={size} viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect x="4" y="50" width="56" height="6" fill="#9c9388"/>
    <rect x="12" y="22" width="8" height="28" fill="#9c9388"/>
    <rect x="28" y="22" width="8" height="28" fill="#9c9388"/>
    <rect x="44" y="22" width="8" height="28" fill="#9c9388"/>
    <rect x="4" y="20" width="56" height="2" fill="#9c9388"/>
    <polygon points="32,4 4,20 60,20" fill="#9c9388"/>
    <polygon points="32,8 12,20 52,20" fill="#7d7568" opacity="0.35"/>
  </svg>
{:else if type === 'purse'}
  <svg width={size} height={size} viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M 22 28 Q 12 30 8 42 L 8 54 Q 8 60 14 60 L 50 60 Q 56 60 56 54 L 56 42 Q 52 30 42 28 Z" fill="#80452f"/>
    <ellipse cx="32" cy="24" rx="11" ry="2" fill="#3a1a10"/>
    <path d="M 22 28 Q 24 14 28 24 Q 30 16 32 24 Q 34 16 36 24 Q 40 14 42 28 Z" fill="#80452f"/>
    <ellipse cx="32" cy="28" rx="13" ry="3" fill="#b89968"/>
    <path d="M 21 27 L 24 29 M 25 27 L 28 29 M 29 27 L 32 29 M 33 27 L 36 29 M 37 27 L 40 29 M 41 27 L 44 29" stroke="#8a6e3e" stroke-width="0.7" opacity="0.85" fill="none" stroke-linecap="round"/>
    <path d="M 44 27 Q 50 32 52 38" stroke="#b89968" stroke-width="2" fill="none" stroke-linecap="round"/>
    <circle cx="52" cy="38" r="2.2" fill="#b89968"/>
    <ellipse cx="22" cy="44" rx="3.5" ry="8" fill="#9a5a40" opacity="0.5"/>
    <path d="M 22 38 L 22 56" stroke="#5e2f1f" stroke-width="0.7" opacity="0.35" fill="none"/>
    <path d="M 42 38 L 42 56" stroke="#5e2f1f" stroke-width="0.7" opacity="0.35" fill="none"/>
    <line x1="32" y1="32" x2="32" y2="58" stroke="#5e2f1f" stroke-width="0.5" opacity="0.25"/>
  </svg>
{:else if type === 'strongbox'}
  <svg width={size} height={size} viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect x="10" y="30" width="44" height="24" fill="#4a4d4f"/>
    <path d="M 10 30 L 10 22 Q 32 16 54 22 L 54 30 Z" fill="#4a4d4f"/>
    <rect x="8" y="28" width="48" height="3" fill="#6a6a6a"/>
    <rect x="28" y="34" width="8" height="10" fill="#6a6a6a"/>
    <circle cx="32" cy="38" r="1.5" fill="#1a1a1a"/>
    <rect x="31" y="39" width="2" height="3" fill="#1a1a1a"/>
    <rect x="8" y="50" width="6" height="4" fill="#6a6a6a"/>
    <rect x="50" y="50" width="6" height="4" fill="#6a6a6a"/>
    <circle cx="14" cy="33" r="1" fill="#6a6a6a"/>
    <circle cx="32" cy="25" r="1" fill="#6a6a6a"/>
    <circle cx="50" cy="33" r="1" fill="#6a6a6a"/>
  </svg>
{:else if type === 'vault'}
  <svg width={size} height={size} viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect x="4" y="4" width="56" height="56" rx="4" fill="#5c6470"/>
    <circle cx="32" cy="32" r="22" fill="#7a8189"/>
    <circle cx="32" cy="32" r="22" fill="none" stroke="#b89968" stroke-width="2.5"/>
    <line x1="32" y1="32" x2="12" y2="32" stroke="#5c6470" stroke-width="3.5" stroke-linecap="round"/>
    <line x1="32" y1="32" x2="42" y2="14.68" stroke="#5c6470" stroke-width="3.5" stroke-linecap="round"/>
    <line x1="32" y1="32" x2="42" y2="49.32" stroke="#5c6470" stroke-width="3.5" stroke-linecap="round"/>
    <line x1="12" y1="29" x2="12" y2="35" stroke="#5c6470" stroke-width="3" stroke-linecap="round"/>
    <line x1="39.4" y1="13.18" x2="44.6" y2="16.18" stroke="#5c6470" stroke-width="3" stroke-linecap="round"/>
    <line x1="39.4" y1="50.82" x2="44.6" y2="47.82" stroke="#5c6470" stroke-width="3" stroke-linecap="round"/>
    <line x1="32" y1="28" x2="32" y2="20" stroke="#5c6470" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="28.54" y1="30" x2="21.6" y2="26" stroke="#5c6470" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="28.54" y1="34" x2="21.6" y2="38" stroke="#5c6470" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="32" y1="36" x2="32" y2="44" stroke="#5c6470" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="35.46" y1="34" x2="42.4" y2="38" stroke="#5c6470" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="35.46" y1="30" x2="42.4" y2="26" stroke="#5c6470" stroke-width="1.5" stroke-linecap="round"/>
    <circle cx="32" cy="32" r="4" fill="#b89968"/>
    <circle cx="10" cy="10" r="1.5" fill="#3e4650"/>
    <circle cx="54" cy="10" r="1.5" fill="#3e4650"/>
    <circle cx="10" cy="54" r="1.5" fill="#3e4650"/>
    <circle cx="54" cy="54" r="1.5" fill="#3e4650"/>
  </svg>
{/if}
