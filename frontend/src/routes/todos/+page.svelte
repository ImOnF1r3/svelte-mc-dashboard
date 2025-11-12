<script lang="ts">
	import Button from '$lib/components/ui/button/button.svelte';
	import Separator from '$lib/components/ui/separator/separator.svelte';
	import { io, Socket } from 'socket.io-client';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Trash2, Check, Plus, Calendar } from '@lucide/svelte';

	import { slide } from 'svelte/transition'; // Transizione nativa

	export const data = $props();

	let todos = $state([]);
	let nextId = 1;
	let title = $state('');
	let text = $state('');
	let date = $state(''); // NUOVO: Stato per la data
	let showForm = $state(false);

	let socket: Socket;

	// Gesture tracking per ogni todo
	let dragStates = $state<{ [key: number]: { x: number; startX: number; isDragging: boolean } }>(
		{}
	);

	// NUOVO: Stati per la modifica
	let editingTodoId = $state<number | null>(null);
	let editTitle = $state('');
	let editText = $state('');
	let editDate = $state<string | null>(''); // NUOVO: Stato per la data in modifica
	let markedForDeletionId = $state<number | null>(null);

	function addTodo() {
		if (!title.trim() || !text.trim()) return;
		const newTodo = { id: nextId++, title, text, completed: false, date: date || null };
		socket.emit('add_todo', newTodo);

		// Pulisci gli input
		title = '';
		text = '';
		date = '';

		// Tendina
		showForm = false;

		toast.success('Todo aggiunto!', {
			description: 'Il nuovo elemento è stato aggiunto alla lista',
			duration: 2000
		});
	}

	function deleteTodo(id: number) {
		if (markedForDeletionId === id) markedForDeletionId = null;
		socket.emit('delete_todo', { id });
		toast.success('Todo eliminato!', {
			duration: 2000
		});
	}

	function toggleComplete(id: number) {
		const todo = todos.find((t) => t.id === id);
		if (todo) {
			if (markedForDeletionId === id) markedForDeletionId = null;
			todo.completed = !todo.completed;
			socket.emit('update_todos', { todos });
			toast.success(todo.completed ? 'Todo completato! ✓' : 'Todo riattivato!', {
				duration: 2000
			});
		}
	}

	// NUOVO: Funzioni per la modifica
	function startEditing(todo) {
		// Non permettere di modificare se si sta già modificando un altro todo.
		if (editingTodoId !== null) return;
		// Se un todo era marcato per l'eliminazione, deselezionalo quando si inizia a modificare.
		markedForDeletionId = null;

		editingTodoId = todo.id;
		editTitle = todo.title;
		editText = todo.text;
		editDate = todo.date || '';
	}

	function cancelEdit() {
		if (markedForDeletionId === editingTodoId) markedForDeletionId = null;
		editingTodoId = null;
		editTitle = '';
		editText = '';
		editDate = '';
	}

	function saveEdit() {
		if (!editingTodoId || !editTitle.trim() || !editText.trim()) return;
		if (markedForDeletionId === editingTodoId) markedForDeletionId = null;

		const todo = todos.find((t) => t.id === editingTodoId);
		if (todo) {
			todo.title = editTitle.trim();
			todo.text = editText.trim();
			todo.date = editDate || null;
			socket.emit('update_todos', { todos });
			toast.success('Todo aggiornato!', {
				duration: 2000
			});
		}

		// Resetta lo stato di modifica
		cancelEdit();
	}

	// NUOVO: Funzione per formattare la data
	function formatDate(dateString: string) {
		if (!dateString) return '';
		return new Date(dateString).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
	}

	// Touch gesture handling
	function handleTouchStart(e: TouchEvent, id: number) {
        // Impedisci il drag se si sta modificando
        if (editingTodoId === id) return;
		const touch = e.touches[0];
		dragStates[id] = {
			x: 0,
			startX: touch.clientX,
			isDragging: true
		};
	}

	function handleTouchMove(e: TouchEvent, id: number) {
        // Impedisci il drag se si sta modificando
		if (editingTodoId === id || !dragStates[id]?.isDragging) return;

		const touch = e.touches[0];
		const deltaX = touch.clientX - dragStates[id].startX;
		dragStates[id] = { ...dragStates[id], x: deltaX };
	}

	function handleTouchEnd(e: TouchEvent, id: number) {
        // Impedisci il drag se si sta modificando
		if (editingTodoId === id || !dragStates[id]?.isDragging) return;

		const threshold = 80;
		const x = dragStates[id].x;

		if (x > threshold) {
			// Swipe a destra -> completa/riattiva e deseleziona
			toggleComplete(id);
			markedForDeletionId = null;
		} else if (x < -threshold) {
			// Swipe a sinistra
			if (markedForDeletionId === id) {
				// Secondo swipe -> elimina
				deleteTodo(id);
			} else {
				// Primo swipe -> marca per eliminazione
				markedForDeletionId = id;
				toast.info('Swipe di nuovo a sinistra per eliminare.');
			}
		}

		dragStates[id] = { x: 0, startX: 0, isDragging: false };
	}

	// Mouse drag handling
	let currentDragId: number | null = null;

	function handleMouseDown(e: MouseEvent, id: number) {
        // NUOVO: Impedisci il drag se si sta modificando
        if (editingTodoId === id) return;
		currentDragId = id;
		dragStates[id] = {
			x: 0,
			startX: e.clientX,
			isDragging: true
		};
	}

	function handleMouseMove(e: MouseEvent, id: number) {
		if (currentDragId !== id || editingTodoId === id || !dragStates[id]?.isDragging) return;

		const deltaX = e.clientX - dragStates[id].startX;
		dragStates[id] = { ...dragStates[id], x: deltaX };
	}

	function handleMouseUp(e: MouseEvent, id: number) {
		if (currentDragId !== id) return;
		currentDragId = null;
        
		// C'era un piccolo bug qui: se isDragging non è true, non fare nulla
		if (!dragStates[id]?.isDragging) return;

		const threshold = 80;
		const x = dragStates[id]?.x || 0;

		if (x > threshold) {
			// Swipe a destra -> completa/riattiva e deseleziona
			toggleComplete(id);
			markedForDeletionId = null;
		} else if (x < -threshold) {
			// Swipe a sinistra
			if (markedForDeletionId === id) {
				// Secondo swipe -> elimina
				deleteTodo(id);
			} else {
				// Primo swipe -> marca per eliminazione
				markedForDeletionId = id;
				toast.info('Swipe di nuovo a sinistra per eliminare.');
			}
		}

		dragStates[id] = { x: 0, startX: 0, isDragging: false };
	}

	onMount(() => {
		socket = io('/', { path: '/ws' });

		socket.on('connect', () => {
			console.log('Socket connesso, richiedo i todos...');
			socket.emit('get_todos', {}, (response) => {
				console.log('Todos ricevuti:', response);
				todos = response.todos || [];
				if (todos.length > 0) {
					nextId = Math.max(...todos.map((t) => t.id)) + 1;
				}
			});
		});

		socket.on('update_todos', (data) => {
			console.log('Update todos ricevuto:', data);
			todos = data || [];
			if (todos.length > 0) {
				nextId = Math.max(...todos.map((t) => t.id)) + 1;
			}
		});

		const handleGlobalInteraction = (e: MouseEvent | TouchEvent) => {
			// Se il mouse viene rilasciato, resetta l'ID del drag corrente.
			if (e.type === 'mouseup') {
				if (currentDragId) {
					handleMouseUp(e as MouseEvent, currentDragId);
				}
			}

			// Se c'è un elemento marcato per l'eliminazione...
			if (markedForDeletionId !== null) {
				// ...e il click/tap non è avvenuto su quell'elemento...
				const target = e.target as HTMLElement;
				if (!target.closest('.marked-for-deletion')) {
					// ...allora deselezionalo.
					markedForDeletionId = null;
				}
			}
			currentDragId = null;
		};
		window.addEventListener('mouseup', handleGlobalInteraction);

		return () => {
			socket.disconnect();
			window.removeEventListener('mouseup', handleGlobalInteraction);
		};
	});
</script>

<div class="container">
	<h1>📝 TO DO LIST</h1>

	<div class="hint">
		💡 Swipe → per completare • Doppio swipe ← per eliminare • Doppio click per modificare
	</div>

	<br />

	<button class="toggle-btn" on:click={() => (showForm = !showForm)}>
		<Plus size={20} />
		{showForm ? 'Chiudi' : 'Aggiungi Todo'}
	</button>

	<br />

	{#if showForm}
		<form on:submit|preventDefault={addTodo} transition:slide>
			<input type="text" placeholder="Titolo" bind:value={title} required />
			<textarea placeholder="Testo" bind:value={text} required></textarea>
			<input type="date" bind:value={date} />
			<button type="submit" class="add-btn">Aggiungi</button>
		</form>
	{/if}

	{#if todos.length === 0}
		<div class="empty-state">
			<p>✨ Nessun elemento nella lista</p>
			<span>Aggiungi il tuo primo todo!</span>
		</div>
	{:else}
		<ul>
			{#each todos as todo (todo.id)}
				<li
					class="todo-item"
					class:completed={todo.completed}
                    class:editing={editingTodoId === todo.id}
                    class:marked-for-deletion={markedForDeletionId === todo.id}
                    style="transform: translateX({dragStates[todo.id]?.x || 0}px)"
					on:touchstart={(e) => handleTouchStart(e, todo.id)}
					on:touchmove={(e) => handleTouchMove(e, todo.id)}
					on:touchend={(e) => handleTouchEnd(e, todo.id)}
					on:mousedown={(e) => handleMouseDown(e, todo.id)}
					on:mousemove={(e) => handleMouseMove(e, todo.id)}
					on:mouseup={(e) => handleMouseUp(e, todo.id)}
				>
					<div class="swipe-bg left">
						<Trash2 size={28} />
						<span>Elimina</span>
					</div>
					<div class="swipe-bg right">
						<Check size={28} />
						<span>{todo.completed ? 'Riattiva' : 'Completa'}</span>
					</div>

                    {#if editingTodoId === todo.id}
                        <form class="edit-form" on:submit|preventDefault={saveEdit}>
                            <input 
                                type="text" 
                                bind:value={editTitle} 
                                required 
                                on:mousedown|stopPropagation on:touchstart|stopPropagation />
                            <textarea 
                                bind:value={editText} 
                                required
                                on:mousedown|stopPropagation
                                on:touchstart|stopPropagation
                            ></textarea>
                            <input 
                                type="date" 
                                bind:value={editDate}
                                on:mousedown|stopPropagation
                                on:touchstart|stopPropagation
                            />
                            <div class="edit-actions">
                                <button 
                                    type="button" 
                                    class="cancel-btn" 
                                    on:click|stopPropagation={cancelEdit}
                                >
                                    Annulla
                                </button>
                                <button 
                                    type="submit" 
                                    class="save-btn"
                                    on:click|stopPropagation
                                >
                                    Salva
                                </button>
                            </div>
                        </form>
                    {:else}
                        <div class="todo-content" on:dblclick={() => startEditing(todo)}>
                            <div class="todo-header">
                                <h3>{todo.title}</h3>
                                {#if todo.completed}
                                    <span class="badge completed-badge">✓ Completato</span>
                                {/if}
                                {#if todo.date}
                                    <div class="date-display">
                                        <Calendar size={14} />
                                        <span>{formatDate(todo.date)}</span>
                                    </div>
                                {/if}
                            </div>
                            <p>{todo.text}</p>
                        </div>
                    {/if}
					</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	@import '../../styles.css';
	@import './todos.css';
</style>