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
        placeholder="word"
        @keydown="onKeydown"
        spellcheck="false"
        autocomplete="off"
      />
      <button
        class="btn-go"
        :disabled="wordInput.length !== 5"
        @click="$emit('commit')"
      >
        Go
      </button>
    </div>

    <div v-else class="tiles">
      <button
        v-for="(letter, i) in guess.word.split('')"
        :key="i"
        class="tile"
        :class="colorMap[guess.result[i]]"
        @click="$emit('toggle', i)"
        :title="`Click to cycle: green → yellow → red`"
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
}

.word-input {
  width: 160px;
  padding: 10px 12px;
  background: var(--bg-light);
  border: 2px solid var(--tile-border);
  border-radius: 4px;
  color: var(--text);
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  font-family: inherit;
  outline: none;
}
.word-input:focus {
  border-color: var(--text-dim);
}
.word-input::placeholder {
  color: var(--text-dim);
  letter-spacing: 0.15em;
  font-weight: 400;
}

.btn-go {
  padding: 10px 16px;
  background: var(--green-dark);
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.85rem;
  text-transform: uppercase;
}
.btn-go:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.btn-go:not(:disabled):hover {
  background: var(--green);
}

.tiles {
  display: flex;
  gap: 4px;
  align-items: center;
}

.tile {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  font-weight: 700;
  text-transform: uppercase;
  border: none;
  border-radius: 2px;
  color: white;
  transition: transform 0.1s;
}
.tile:hover {
  transform: scale(1.08);
}
.tile.green {
  background: var(--green);
}
.tile.yellow {
  background: var(--yellow);
}
.tile.red {
  background: var(--red);
}

.btn-x {
  margin-left: 8px;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.4rem;
  padding: 4px 8px;
}
.btn-x:hover {
  color: #ff4444;
}
</style>
