<script setup>
import { ref, computed, watch } from 'vue'
import GuessRow from './components/GuessRow.vue'
import WordCloud from './components/WordCloud.vue'
import ConstraintInfo from './components/ConstraintInfo.vue'

const guesses = ref([])
const candidates = ref([])
const matchKey = ref(null)
const greens = ref('.....')
const yellows = ref('')
const totalRemaining = ref(0)
const loading = ref(false)
const startingWords = ref([])

// Load starting words on mount
fetch('/api/starting-words')
  .then(r => r.json())
  .then(data => {
    startingWords.value = data
  })

// Add a fresh empty guess row
function addGuess() {
  guesses.value.push({ word: '', result: 'rrrrr', committed: false })
}
addGuess()

async function solve() {
  const committed = guesses.value.filter(g => g.committed)
  if (committed.length === 0) return

  loading.value = true
  try {
    const res = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        guesses: committed.map(g => ({ word: g.word, result: g.result })),
      }),
    })
    const data = await res.json()
    candidates.value = data.candidates || []
    matchKey.value = data.match_key || null
    greens.value = data.greens || '.....'
    yellows.value = data.yellows || ''
    totalRemaining.value = data.total_remaining || 0
  } catch (e) {
    console.error('Solve error:', e)
  } finally {
    loading.value = false
  }
}

function commitGuess(index) {
  const g = guesses.value[index]
  if (g.word.length !== 5) return
  g.committed = true
  solve()
  // Add next row if this was the last one
  if (index === guesses.value.length - 1) {
    addGuess()
  }
}

function updateResult(index, pos) {
  const g = guesses.value[index]
  const chars = g.result.split('')
  const cycle = { r: 'y', y: 'g', g: 'r' }
  chars[pos] = cycle[chars[pos]]
  g.result = chars.join('')
  if (g.committed) solve()
}

function removeGuess(index) {
  guesses.value.splice(index, 1)
  if (guesses.value.length === 0) addGuess()
  solve()
}

function reset() {
  guesses.value = []
  candidates.value = []
  matchKey.value = null
  greens.value = '.....'
  yellows.value = ''
  totalRemaining.value = 0
  addGuess()
}

function selectWord(word) {
  // Fill the current empty guess row (or create one if needed)
  let empty = guesses.value.find(g => !g.committed && g.word.length === 0)
  if (!empty) {
    addGuess()
    empty = guesses.value[guesses.value.length - 1]
  }
  empty.word = word

  // Pre-fill result based on known greens and yellows
  const result = []
  for (let i = 0; i < 5; i++) {
    if (greens.value[i] !== '.' && greens.value[i] === word[i]) {
      result.push('g')
    } else if (yellows.value.includes(word[i])) {
      result.push('y')
    } else {
      result.push('r')
    }
  }
  empty.result = result.join('')

  // Auto-commit so tiles are visible (user can click to adjust colors)
  const index = guesses.value.indexOf(empty)
  empty.committed = true
  solve()
  if (index === guesses.value.length - 1) {
    addGuess()
  }
}
</script>

<template>
  <h1>Wordle Solver</h1>

  <div class="layout">
    <div class="input-panel">
      <h2>Your Guesses</h2>
      <div class="guess-list">
        <GuessRow
          v-for="(guess, i) in guesses"
          :key="i"
          :guess="guess"
          :index="i"
          @commit="commitGuess(i)"
          @toggle="updateResult(i, $event)"
          @remove="removeGuess(i)"
        />
      </div>
      <div class="actions">
        <button class="btn btn-reset" @click="reset">Reset</button>
      </div>

      <ConstraintInfo
        v-if="greens !== '.....'"
        :greens="greens"
        :yellows="yellows"
        :total="totalRemaining"
        :matchKey="matchKey"
      />

      <div v-if="candidates.length === 0 && startingWords.length > 0" class="starters">
        <h2>Suggested Starters</h2>
        <div class="starter-chips">
          <button
            v-for="w in startingWords.slice(0, 12)"
            :key="w.word"
            class="chip"
            @click="selectWord(w.word)"
          >
            {{ w.word }}
          </button>
        </div>
      </div>
    </div>

    <div class="cloud-panel">
      <h2 v-if="candidates.length > 0">
        Candidates ({{ totalRemaining }} remaining)
      </h2>
      <h2 v-else>Enter a guess to see candidates</h2>
      <WordCloud :candidates="candidates" :loading="loading" @select="selectWord" />
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 24px;
  align-items: start;
}

@media (max-width: 720px) {
  .layout {
    grid-template-columns: 1fr;
  }
}

.input-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guess-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.btn-reset {
  background: var(--red-dark);
  color: var(--text);
}
.btn-reset:hover {
  background: var(--red);
}

.starters {
  margin-top: 8px;
}

.starter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  padding: 6px 12px;
  border: 1px solid var(--tile-border);
  border-radius: 4px;
  background: var(--bg-light);
  color: var(--text);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.chip:hover {
  border-color: var(--yellow);
  color: var(--yellow);
}

.cloud-panel {
  min-height: 400px;
}
</style>
