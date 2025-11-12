<script>
	import { onMount } from 'svelte';

	// *** IMPOSTA QUESTO ***
	// Metti qui l'IP del tuo Raspberry Pi dove gira il backend Python
	const API_URL = 'http://localhost:8000'; // Esempio

	let logLines = ['Caricamento console...'];
	let stats = {
		status: 'loading...',
		process_ram: '0 MB',
		system_ram: '0 / 0 GB'
	};
	let isLoading = false; // Per evitare click multipli

	// Funzione per inviare comandi (start, stop, restart)
	async function sendAction(action) {
		if (isLoading) return;
		isLoading = true;
		
		try {
			const res = await fetch(`${API_URL}/${action}`, { method: 'POST' });
			const data = await res.json();
			if(data.error) {
				alert(`Errore: ${data.error}`);
			}
			// Aspetta un secondo e poi aggiorna le statistiche
			setTimeout(fetchStats, 1000); 
		} catch (e) {
			console.error(`Errore durante ${action}:`, e);
			alert(`Impossibile contattare il backend: ${e.message}`);
		}
		isLoading = false;
	}

	// Funzione per prendere i log
	async function fetchLogs() {
		try {
			const res = await fetch(`${API_URL}/logs`);
			if (res.ok) {
				logLines = await res.json();
			} else {
				logLines = [`Errore nel caricare i log: ${res.statusText}`];
			}
		} catch (e) {
			logLines = [`Backend non raggiungibile.`];
		}
	}

	// Funzione per prendere le statistiche
	async function fetchStats() {
		try {
			const res = await fetch(`${API_URL}/stats`);
			if (res.ok) {
				stats = await res.json();
			} else {
				stats.status = 'Errore';
			}
		} catch (e) {
			stats.status = 'Offline';
		}
	}

	// Quando il componente viene caricato
	onMount(() => {
		// Carica tutto subito
		fetchLogs();
		fetchStats();

		// Imposta un timer per aggiornare automaticamente i dati ogni 3 secondi
		const interval = setInterval(() => {
			fetchLogs();
			fetchStats();
		}, 3000);

		// Pulisci il timer quando l'utente lascia la pagina
		return () => clearInterval(interval);
	});
</script>

<style>
	:global(body) {
		background-color: #222;
		color: #eee;
		font-family: Arial, sans-serif;
	}
	main {
		display: grid;
		grid-template-columns: 300px 1fr;
		gap: 20px;
		padding: 20px;
		max-width: 1400px;
		margin: auto;
	}
	.sidebar {
		background-color: #333;
		padding: 20px;
		border-radius: 8px;
	}
	.console-wrapper {
		background-color: #111;
		border: 1px solid #444;
		border-radius: 8px;
		padding: 20px;
		height: 70vh;
		overflow-y: auto;
		font-family: 'Courier New', Courier, monospace;
		font-size: 0.9em;
		white-space: pre-wrap;
	}
	.console-wrapper p { margin: 0; padding: 0; line-height: 1.4; }
	button {
		display: block;
		width: 100%;
		padding: 12px;
		font-size: 1em;
		margin-bottom: 10px;
		border: none;
		border-radius: 5px;
		cursor: pointer;
		font-weight: bold;
	}
	.start { background-color: #28a745; color: white; }
	.stop { background-color: #dc3545; color: white; }
	.restart { background-color: #ffc107; color: black; }
	button:disabled { background-color: #777; cursor: not-allowed; }

	.stats { margin-top: 20px; }
	.stats p {
		background-color: #444;
		padding: 10px;
		border-radius: 5px;
		display: flex;
		justify-content: space-between;
        margin-bottom: 8px;
	}
	.stats span { font-weight: bold; }
	.status-Online { color: #28a745; }
	.status-Offline { color: #dc3545; }
</style>

<main>
	<aside class="sidebar">
		<h2>Controlli</h2>
		<button class="start" on:click={() => sendAction('start')} disabled={isLoading}>
			Avvia Server
		</button>
		<button class="stop" on:click={() => sendAction('stop')} disabled={isLoading}>
			Stoppa Server
		</button>
		<button class="restart" on:click={() => sendAction('restart')} disabled={isLoading}>
			Riavvia Server
		</button>

		<div class="stats">
			<h2>Statistiche</h2>
			<p>
				Stato:
				<span class:status-Online={stats.status === 'Online'}
					  class:status-Offline={stats.status === 'Offline'}
				>
					{stats.status}
				</span>
			</p>
			<p>
				RAM Processo:
				<span>{stats.process_ram}</span>
			</p>
            <p>
				RAM Sistema:
				<span>{stats.system_ram}</span>
			</p>
		</div>
	</aside>

	<section>
		<h2>Console (ultime 30 righe)</h2>
		<div class="console-wrapper">
			{#each logLines as line}
				<p>{line}</p>
			{/each}
		</div>
	</section>
</main>