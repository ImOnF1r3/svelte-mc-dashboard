<script lang="ts">
    import Button from '$lib/components/ui/button/button.svelte';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { io, Socket } from 'socket.io-client';
    import { onMount } from 'svelte';
    import { toast } from 'svelte-sonner';
    import * as Card from '$lib/components/ui/card/index.js';
    import { ArrowBigUpDash, ArrowBigDownDash, Trash2, Check, Plus } from '@lucide/svelte';
    import * as InputOtp from '$lib/components/ui/input-otp/index';

	import { slide } from 'svelte/transition'; // Transizione nativa
    
    export const data = $props();
    
    let todos = $state([]);
    let nextId = 1;
    let title = $state('');
	let text = $state('');
	let showForm = $state(false);

    let socket: Socket;
    
    // Gesture tracking per ogni todo
    let dragStates = $state<{[key: number]: {x: number, startX: number, isDragging: boolean}}>({});
    
    function addTodo() {
        if (!title.trim() || !text.trim()) return;
        const newTodo = { id: nextId++, title, text, completed: false };
        socket.emit("add_todo", newTodo);
        
        // Pulisci gli input
        title = '';
        text = '';

		// Tendina
		showForm = false;
        
        toast.success('Todo aggiunto!', {
            description: 'Il nuovo elemento è stato aggiunto alla lista',
            duration: 2000
        });
    }
    
    function deleteTodo(id: number) {
        socket.emit("delete_todo", { id });
        toast.success('Todo eliminato!', {
            duration: 2000
        });
    }
    
    function toggleComplete(id: number) {
        const todo = todos.find(t => t.id === id);
        if (todo) {
            todo.completed = !todo.completed;
            socket.emit("update_todos", { todos });
            toast.success(todo.completed ? 'Todo completato! ✓' : 'Todo riattivato!', {
                duration: 2000
            });
        }
    }

    // Touch gesture handling
    function handleTouchStart(e: TouchEvent, id: number) {
        const touch = e.touches[0];
        dragStates[id] = { 
            x: 0, 
            startX: touch.clientX, 
            isDragging: true 
        };
    }
    
    function handleTouchMove(e: TouchEvent, id: number) {
        if (!dragStates[id]?.isDragging) return;
        
        const touch = e.touches[0];
        const deltaX = touch.clientX - dragStates[id].startX;
        dragStates[id] = { ...dragStates[id], x: deltaX };
    }
    
    function handleTouchEnd(e: TouchEvent, id: number) {
        if (!dragStates[id]?.isDragging) return;
        
        const threshold = 80;
        const x = dragStates[id].x;
        
        if (x > threshold) {
            // Swipe a destra -> completa/riattiva
            toggleComplete(id);
        } else if (x < -threshold) {
            // Swipe a sinistra -> elimina
            deleteTodo(id);
        }
        
        dragStates[id] = { x: 0, startX: 0, isDragging: false };
    }
    
    // Mouse drag handling
    let currentDragId: number | null = null;
    
    function handleMouseDown(e: MouseEvent, id: number) {
        currentDragId = id;
        dragStates[id] = { 
            x: 0, 
            startX: e.clientX, 
            isDragging: true 
        };
    }
    
    function handleMouseMove(e: MouseEvent, id: number) {
        if (currentDragId !== id || !dragStates[id]?.isDragging) return;
        
        const deltaX = e.clientX - dragStates[id].startX;
        dragStates[id] = { ...dragStates[id], x: deltaX };
    }
    
    function handleMouseUp(e: MouseEvent, id: number) {
        if (currentDragId !== id) return;
        currentDragId = null;
        
        const threshold = 80;
        const x = dragStates[id]?.x || 0;
        
        if (x > threshold) {
            toggleComplete(id);
        } else if (x < -threshold) {
            deleteTodo(id);
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
                    nextId = Math.max(...todos.map(t => t.id)) + 1;
                }
            });
        });
        
        socket.on('update_todos', (data) => {
            console.log('Update todos ricevuto:', data);
            todos = data || [];
            if (todos.length > 0) {
                nextId = Math.max(...todos.map(t => t.id)) + 1;
            }
        });
        
        const handleGlobalMouseUp = () => {
            currentDragId = null;
        };
        window.addEventListener('mouseup', handleGlobalMouseUp);
        
        return () => {
            socket.disconnect();
            window.removeEventListener('mouseup', handleGlobalMouseUp);
        };
    });
</script>



<div class="container">
    <h1>📝 TO DO LIST</h1>

    <!-- Bottone che apre/chiude -->
	<button class="toggle-btn" on:click={() => (showForm = !showForm)}>
		<Plus size={20} />
		{showForm ? 'Chiudi' : 'Aggiungi Todo'}
	</button>

    <br>

	<!-- Contenitore della tendina -->
	{#if showForm}
		<form on:submit|preventDefault={addTodo} transition:slide>
			<input type="text" placeholder="Titolo" bind:value={title} required />
			<textarea placeholder="Testo" bind:value={text} required></textarea>
			<button type="submit" class="add-btn">Aggiungi</button>
		</form>
	{/if}


    <div class="hint">
        💡 Swipe → per completare • Swipe ← per eliminare
    </div>

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
                    
                    <div class="todo-content">
                        <div class="todo-header">
                            <h3>{todo.title}</h3>
                            {#if todo.completed}
                                <span class="badge completed-badge">✓ Completato</span>
                            {/if}
                        </div>
                        <p>{todo.text}</p>
                        
						<!--
                        <div class="todo-actions">
                            <button 
                                class="action-btn complete-btn" 
                                on:click|stopPropagation={() => toggleComplete(todo.id)}
                                title={todo.completed ? "Segna come non completato" : "Segna come completato"}
                            >
                                {#if todo.completed}
                                    <span>↩️</span>
                                {:else}
                                    <span>✓</span>
                                {/if}
                            </button>
                            <button 
                                class="action-btn delete-btn" 
                                on:click|stopPropagation={() => deleteTodo(todo.id)}
                                title="Elimina"
                            >
                                <span>🗑️</span>
                            </button>
                        </div> -->
                    </div>
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
	@import "../../styles.css"
</style>



	.container {
		max-width: 800px;
		margin: 0 auto;
		padding: 1rem;
		width: 100%;
	}

	h1 {
		font-size: clamp(2rem, 5vw, 2.5rem);
		font-weight: 800;
		text-align: center;
		margin-bottom: 2rem;
		background: linear-gradient(135deg, #818cf8 0%, #ec4899 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		animation: fadeInDown 0.6s ease-out;
	}

	form {
		background: #1e293b;
		padding: clamp(1rem, 3vw, 2rem);
		border-radius: 16px;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
		margin-bottom: 2rem;
		border: 1px solid rgba(99, 102, 241, 0.2);
		animation: fadeInUp 0.6s ease-out;
	}

	input[type='text'],
	textarea {
		width: 100%;
		padding: 1rem;
		margin-bottom: 1rem;
		background: #334155;
		border: 2px solid transparent;
		border-radius: 10px;
		color: #f1f5f9;
		font-size: clamp(0.9rem, 2vw, 1rem);
		transition: all 0.3s ease;
		font-family: inherit;
	}

	input[type='text']:focus,
	textarea:focus {
		outline: none;
		border-color: #6366f1;
		background: #0f172a;
		box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
	}

	textarea {
		min-height: 100px;
		resize: vertical;
	}

	form button[type='submit'] {
		width: 100%;
		padding: 1rem;
		background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
		color: white;
		border: none;
		border-radius: 10px;
		font-size: clamp(0.9rem, 2vw, 1rem);
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	form button[type='submit']:hover {
		transform: translateY(-2px);
		box-shadow: 0 6px 25px rgba(236, 72, 153, 0.6);
	}

	.hint {
		text-align: center;
		color: #94a3b8;
		font-size: clamp(0.8rem, 2vw, 0.9rem);
		margin-bottom: 1.5rem;
		opacity: 0.8;
		animation: fadeIn 1s ease-out;
	}

	.empty-state {
		text-align: center;
		padding: 4rem 2rem;
		animation: fadeIn 0.6s ease-out;
	}

	.empty-state p {
		font-size: clamp(1.2rem, 3vw, 1.5rem);
		color: #94a3b8;
		margin-bottom: 0.5rem;
	}

	.empty-state span {
		color: #64748b;
		font-size: clamp(0.9rem, 2vw, 1rem);
	}

	ul {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		animation: fadeIn 0.8s ease-out;
	}

	.todo-item {
		position: relative;
		cursor: grab;
		user-select: none;
		transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
		touch-action: pan-y;
		overflow: hidden;
		border-radius: 16px;
	}

	.todo-item:active {
		cursor: grabbing;
	}

	.todo-item.completed {
		opacity: 0.85;
	}

	.todo-item.completed .todo-content {
		background: linear-gradient(135deg, #117d59 0%, #059669 100%);
		border-color: #117d59;
	}

	.todo-item.completed h3 {
		text-decoration: line-through;
		opacity: 0.8;
	}

	.todo-item.completed p {
		opacity: 0.7;
	}

	.toggle-btn {
		display: flex;
		align-items: center;
		gap: 8px;
		/* Ho aggiornato i colori per abbinarli al tuo tema pink/purple */
		background: #818cf8;
		color: white;
		border: none;
		padding: 10px 16px;
		border-radius: 10px;
		cursor: pointer;
		font-weight: 600;
		transition: all 0.2s ease;
		margin-bottom: 10px;
		box-shadow: 0 4px 15px rgba(129, 140, 248, 0.3);
	}

	.toggle-btn:hover {
		background: #6366f1;
		transform: translateY(-1px);
		box-shadow: 0 6px 20px rgba(129, 140, 248, 0.4);
	}

	/* Ho corretto il selettore per il tuo form 'add' */
	form .add-btn {
		width: 100%;
		padding: 1rem;
		background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
		color: white;
		border: none;
		border-radius: 10px;
		font-size: clamp(0.9rem, 2vw, 1rem);
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	form .add-btn:hover {
		transform: translateY(-2px);
		box-shadow: 0 6px 25px rgba(236, 72, 153, 0.6);
	}

	.swipe-bg {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 100%;
		display: flex;
		align-items: center;
		padding: 0 2rem;
		gap: 0.75rem;
		font-weight: 600;
		font-size: clamp(0.9rem, 2vw, 1rem);
		z-index: 0;
		opacity: 0;
		transition: opacity 0.2s ease;
	}

	.swipe-bg.left {
		left: 0;
		background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
		color: white;
		justify-content: flex-start;
	}

	.swipe-bg.right {
		right: 0;
		background: linear-gradient(90deg, #059669 0%, #117d59 100%);
		color: white;
		justify-content: flex-end;
	}

	.todo-item[style*='translateX'] .swipe-bg {
		opacity: 1;
	}

	.todo-content {
		position: relative;
		z-index: 1;
		background: #1e293b;
		border: 1px solid rgba(99, 102, 241, 0.2);
		border-radius: 16px;
		padding: clamp(1.25rem, 3vw, 1.75rem);
		/* Rimuovo il padding-bottom fisso, gestito ora dal form di modifica */
		/* padding-bottom: 4rem; */
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		transition: all 0.3s ease;
	}

	.todo-item:hover .todo-content {
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
		transform: translateY(-2px);
	}

	.todo-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 0.75rem;
		flex-wrap: wrap;
	}

	h3 {
		font-size: clamp(1.1rem, 3vw, 1.4rem);
		font-weight: 700;
		color: #818cf8;
		margin: 0;
		flex: 1;
		min-width: 0;
		word-break: break-word;
	}

	.badge {
		padding: 0.35rem 0.75rem;
		border-radius: 20px;
		font-size: clamp(0.75rem, 2vw, 0.85rem);
		font-weight: 600;
		white-space: nowrap;
	}

	.completed-badge {
		background: rgba(16, 185, 129, 0.2);
		color: #117d59;
		border: 1px solid rgba(16, 185, 129, 0.3);
	}

	p {
		color: #cbd5e1;
		margin: 0;
		line-height: 1.6;
		font-size: clamp(0.9rem, 2vw, 1rem);
		word-break: break-word;
	}

	.form-wrapper {
		overflow: hidden;
		max-height: 0;
		opacity: 0;
		transform: translateY(-10px);
		transition: all 0.4s ease;
	}

	.form-wrapper.open {
		max-height: 400px; /* Aumentato per sicurezza */
		opacity: 1;
		transform: translateY(0);
	}

	.todo-actions {
		position: absolute;
		bottom: 0;
		right: 0;
		display: flex;
		gap: 0.5rem;
		padding: 0.75rem;
		opacity: 0;
		transform: translateY(10px);
		transition: all 0.3s ease;
	}

	.todo-item:hover .todo-actions {
		opacity: 1;
		transform: translateY(0);
	}

	.action-btn {
		padding: 0.6rem 1rem;
		font-size: clamp(1rem, 3vw, 1.2rem);
		border-radius: 8px;
		border: none;
		cursor: pointer;
		transition: all 0.2s ease;
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.action-btn:hover {
		transform: scale(1.15);
	}

	.action-btn:active {
		transform: scale(0.95);
	}

	.complete-btn {
		background: linear-gradient(135deg, #117d59 0%, #059669 100%);
	}

	.complete-btn:hover {
		box-shadow: 0 4px 12px rgba(16, 185, 129, 0.5);
	}

	.delete-btn {
		background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
	}

	.delete-btn:hover {
		box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5);
	}

	/* Animazioni */
	@keyframes fadeIn {
		from {
			opacity: 0;
		}

		to {
			opacity: 1;
		}
	}

	@keyframes fadeInDown {
		from {
			opacity: 0;
			transform: translateY(-20px);
		}

		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(20px);
		}

		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* Mobile */
	@media (max-width: 768px) {
		.container {
			padding: 0.5rem;
		}

		.todo-actions {
			opacity: 1;
			transform: translateY(0);
			background: rgba(15, 23, 42, 0.9);
			backdrop-filter: blur(8px);
			border-radius: 8px 0 16px 0;
		}

		.swipe-bg {
			padding: 0 1.5rem;
		}

		.swipe-bg span {
			display: none;
		}
	}

	/* Tablet */
	@media (min-width: 769px) and (max-width: 1024px) {
		.container {
			max-width: 700px;
		}
	}

	/* --- NUOVI STILI PER LA MODIFICA (ADATTATI AL DARK THEME) --- */

	/* Disabilita l'effetto hover sul todo-content quando si modifica */
	.todo-item.editing:hover .todo-content {
		transform: translateY(0);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	/* Il form di modifica eredita lo stile del .todo-content */
	.edit-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		position: relative;
		z-index: 1;
		background: #1e293b;
		/* Usa il colore viola del titolo per indicare la modifica */
		border: 1px solid #818cf8;
		border-radius: 16px;
		padding: clamp(1.25rem, 3vw, 1.75rem);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	/* Stili per gli input dentro il form di modifica */
	.edit-form input[type='text'],
	.edit-form textarea {
		width: 100%;
		padding: 1rem;
		margin-bottom: 0; /* Gestito dal gap del form */
		background: #334155;
		border: 2px solid transparent;
		border-radius: 10px;
		color: #f1f5f9;
		transition: all 0.3s ease;
		font-family: inherit;
	}

	.edit-form input[type='text']:focus,
	.edit-form textarea:focus {
		outline: none;
		border-color: #6366f1;
		background: #0f172a;
		box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
	}

	/* Fai assomigliare l'input del titolo al H3 */
	.edit-form input[type='text'] {
		font-size: clamp(1.1rem, 3vw, 1.4rem);
		font-weight: 700;
		color: #818cf8;
		padding: 0; /* Rimuovi padding per farlo sembrare testo */
		background: transparent;
		border-color: transparent;
		border-radius: 0;
	}
	.edit-form input[type='text']:focus {
		background: #334155; /* Mostra lo sfondo solo al focus */
		border-color: #6366f1;
		padding: 1rem;
		border-radius: 10px;
	}

	/* Fai assomigliare la textarea al P */
	.edit-form textarea {
		color: #cbd5e1;
		line-height: 1.6;
		font-size: clamp(0.9rem, 2vw, 1rem);
		min-height: 100px;
		resize: vertical;
	}

	/* Contenitore per i bottoni Salva/Annulla */
	.edit-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem; /* 12px */
		margin-top: 0.5rem;
	}

	/* Stile base per i bottoni di modifica */
	.edit-actions button {
		padding: 0.5rem 1rem;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		font-weight: 600;
		font-size: 0.9rem;
		transition: all 0.2s ease;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	/* Bottone Salva (usa lo stile pink del tuo tema) */
	.save-btn {
		background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
		color: white;
		box-shadow: 0 4px 15px rgba(236, 72, 153, 0.3);
	}

	.save-btn:hover {
		transform: translateY(-1px);
		box-shadow: 0 6px 20px rgba(236, 72, 153, 0.5);
	}

	/* Bottone Annulla (stile secondario dark) */
	.cancel-btn {
		background-color: #334155; /* Colore input */
		color: #cbd5e1; /* Colore testo */
	}

	.cancel-btn:hover {
		background-color: #475569; /* Più chiaro al hover */
	}