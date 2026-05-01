# tallykeep — frontend

SvelteKit Progressive Web App. The real SvelteKit project is initialized at **M10**;
M0 ships a static placeholder served by nginx so the Compose stack is end-to-end alive.

When M10 lands, this directory is rebuilt as `npm create svelte@latest` output, with
TailwindCSS, a typed API client generated from the backend's OpenAPI, and an SSE consumer.
