<!--
  Root redirect — determines the entry point based on auth state.
  Not paired → /onboarding/connect
  Paired but not unlocked → /unlock
  Paired and unlocked → /home
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';
  import { preferences } from '$lib/stores/preferences.svelte';

  onMount(async () => {
    await Promise.all([auth.load(), preferences.load()]);

    if (!auth.isPaired) {
      goto('/onboarding/connect');
    } else if (!auth.unlocked) {
      goto('/unlock');
    } else {
      goto('/home');
    }
  });
</script>
<!-- blank while redirecting -->
