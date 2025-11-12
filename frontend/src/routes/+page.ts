import type { Load } from '@sveltejs/kit';

export const load: Load = async ({ fetch }) => {
	const resp = await fetch('/api/counter');

	if (!resp.ok) {
		return { error: true, counter: 0 };
	}

	const data = await resp.json();
	return { error: false, counter: data.counter };
};
