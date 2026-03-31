<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  guess: Object,
  index: Number,
})
const emit = defineEmits(['commit', 'toggle', 'remove'])

const wordInput = ref(props.guess.word)

watch(wordInput, (val) => {
  props.guess.word = val.toLowerCase().replace(/[^a-z]/g, '').slice(0, 5)
  wordInput.value = props.guess.word
})

// Sync external changes (e.g., selectWord filling in the word)
watch(() => props.guess.word, (val) => {
  if (val !== wordInput.value) wordInput.value = val
})

function onKeydown(e) {
  if (e.key === 'Enter' && wordInput.value.length === 5) {
    emit('commit')
  }
}

const colorMap = { g: 'green', y: 'yellow', r: 'red' }
</script>

<template>
  <div class="guess-row" :class="{ committed: guess.committed }">
    <div v-if="!guess.committed" class="input-wrap">
      <input
        v-model="wordInput"
        class="word-input"
        maxlength="5"
        placeholder="type..."
        @keydown="onKeydown"
        spellcheck="false"
        autocomplete="off"
      />
      <button
        class="btn-go"
        :disabled="wordInput.length !== 5"
        @click="$emit('commit')"
      >
        ↵
      </button>
    </div>

    <div v-else class="tiles">
      <button
        v-for="(letter, i) in guess.word.split('')"
        :key="i"
        class="tile"
        :class="colorMap[guess.result[i]]"
        @click="$emit('toggle', i)"
        :title="`Click to cycle color`"
      >
        {{ letter }}
      </button>
      <button class="btn-x" @click="$emit('remove')" title="Remove guess">×</button>
    </div>
  </div>
</template>

<style scoped>
.guess-row {
  display: flex;
  align-items: center;
}

.input-wrap {
  display: flex;
  gap: 6px;
  align-items: center;
  width: 100%;
}

.word-input {
  flex: 1;
  padding: 10px 12px;
  background: rgba(0, 212, 170, 0.04);
  border: 1px solid rgba(0, 212, 170, 0.12);
  border-radius: 8px;
  color: var(--text);
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  font-family: 'Fira Code', monospace;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}
.word-input:focus {
  border-color: rgba(0, 212, 170, 0.35);
  background: rgba(0, 212, 170, 0.06);
}
.word-input::placeholder {
  color: var(--text-dim);
  letter-spacing: 0.1em;
  font-weight: 400;
  font-size: 0.85rem;
}

.btn-go {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 200, 83, 0.15);
  color: var(--green);
  border: 1px solid rgba(0, 200, 83, 0.25);
  border-radius: 8px;
  font-weight: 700;
  font-size: 1.1rem;
  transition: all 0.2s;
}
.btn-go:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}
.btn-go:not(:disabled):hover {
  background: rgba(0, 200, 83, 0.25);
  border-color: rgba(0, 200, 83, 0.5);
}

.tiles {
  display: flex;
  gap: 4px;
  align-items: center;
}

.tile {
  width: 46px;
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: 700;
  text-transform: uppercase;
  border: none;
  border-radius: 6px;
  color: white;
  transition: transform 0.12s, box-shadow 0.12s;
  font-family: 'Fira Code', monospace;
}
.tile:hover {
  transform: scale(1.08);
}

.tile.green {
  background: var(--green);
  box-shadow: 0 0 12px rgba(0, 200, 83, 0.3);
}
.tile.yellow {
  background: var(--yellow-dark);
  color: #1a1a1a;
  box-shadow: 0 0 12px rgba(255, 215, 64, 0.2);
}
.tile.red {
  background: var(--red-dark);
  box-shadow: 0 0 8px rgba(84, 110, 122, 0.2);
}

.btn-x {
  margin-left: 6px;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.2rem;
  padding: 4px 6px;
  border-radius: 4px;
  transition: all 0.15s;
}
.btn-x:hover {
  color: #ff5252;
  background: rgba(255, 82, 82, 0.1);
}
</style>
