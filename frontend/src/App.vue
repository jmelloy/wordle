<script setup>
import { ref } from 'vue'
import GuessRow from './components/GuessRow.vue'
import WordWeb from './components/WordWeb.vue'
import ConstraintInfo from './components/ConstraintInfo.vue'
import ScreenshotUpload from './components/ScreenshotUpload.vue'
import GameAnalysis from './components/GameAnalysis.vue'

const guesses = ref([])
const candidates = ref([])
const matchKey = ref(null)
const greens = ref('.....')
const yellows = ref('')
const totalRemaining = ref(0)
const loading = ref(false)
const startingWords = ref([])
const analysis = ref(null)
const showUpload = ref(true)
const analyzingGame = ref(false)

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
  analysis.value = null
  showUpload.value = true
  addGuess()
}

async function handleScreenshotParsed(parsedGuesses) {
  // Run analysis on the parsed game
  analyzingGame.value = true
  showUpload.value = false
  try {
    const res = await fetch('/api/analyze-game', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guesses: parsedGuesses }),
    })
    analysis.value = await res.json()
    // Store parsed guesses for loading into solver
    analysis.value._parsedGuesses = parsedGuesses
  } catch (e) {
    console.error('Analysis error:', e)
  } finally {
    analyzingGame.value = false
  }
}

function loadAnalysisGuesses() {
  if (!analysis.value?._parsedGuesses) return
  // Reset solver state and load the parsed guesses
  guesses.value = []
  candidates.value = []
  matchKey.value = null
  greens.value = '.....'
  yellows.value = ''
  totalRemaining.value = 0

  for (const g of analysis.value._parsedGuesses) {
    guesses.value.push({ word: g.word, result: g.result, committed: true })
  }
  addGuess()
  analysis.value = null
  solve()
}

function closeAnalysis() {
  analysis.value = null
  showUpload.value = true
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
  <!-- Full-viewport web background -->
  <WordWeb
    :candidates="candidates"
    :loading="loading"
    :startingWords="startingWords"
    @select="selectWord"
  />

  <!-- Floating center panel -->
  <div class="center-panel">
    <header class="panel-header">
      <h1>Wordle<span class="accent">.</span></h1>
      <div v-if="candidates.length > 0" class="remaining-badge">
        {{ totalRemaining }} left
      </div>
      <div v-else class="remaining-badge dim">
        pick a word
      </div>
    </header>

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

    <ConstraintInfo
      v-if="greens !== '.....'"
      :greens="greens"
      :yellows="yellows"
      :total="totalRemaining"
      :matchKey="matchKey"
    />

    <!-- Screenshot upload -->
    <ScreenshotUpload
      v-if="showUpload && !analysis && candidates.length === 0"
      @parsed="handleScreenshotParsed"
    />

    <!-- Game analysis results -->
    <GameAnalysis
      v-if="analysis"
      :analysis="analysis"
      @close="closeAnalysis"
      @loadGuesses="loadAnalysisGuesses"
    />

    <!-- Loading indicator for analysis -->
    <div v-if="analyzingGame" class="analyzing-indicator">
      <div class="analyzing-spinner"></div>
      <span>Analyzing game...</span>
    </div>

    <div class="panel-footer">
      <button class="btn-reset" @click="reset">
        <span class="reset-icon">↺</span> Reset
      </button>
    </div>
  </div>

  <!-- Instruction hint (bottom) -->
  <div v-if="candidates.length === 0 && !loading && !analysis && !analyzingGame" class="hint-bar">
    Click a word in the web to begin — or upload a screenshot to analyze
  </div>
</template>

<style scoped>
.center-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  width: 340px;
  max-height: 80vh;
  overflow-y: auto;
  padding: 24px 28px;
  background: rgba(8, 14, 24, 0.88);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(0, 212, 170, 0.12);
  border-radius: 16px;
  box-shadow:
    0 0 60px rgba(0, 212, 170, 0.04),
    0 20px 60px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Scrollbar styling */
.center-panel::-webkit-scrollbar {
  width: 4px;
}
.center-panel::-webkit-scrollbar-track {
  background: transparent;
}
.center-panel::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 170, 0.2);
  border-radius: 2px;
}

.panel-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.panel-header h1 {
  font-family: 'Syne', sans-serif;
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-transform: none;
  color: #e0e4e8;
  border: none;
  padding: 0;
  margin: 0;
}

.accent {
  color: #00d4aa;
}

.remaining-badge {
  font-family: 'Fira Code', monospace;
  font-size: 0.72rem;
  font-weight: 600;
  color: #00d4aa;
  background: rgba(0, 212, 170, 0.08);
  border: 1px solid rgba(0, 212, 170, 0.15);
  border-radius: 20px;
  padding: 4px 12px;
  letter-spacing: 0.05em;
}
.remaining-badge.dim {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.08);
  border-color: rgba(107, 114, 128, 0.15);
}

.guess-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-footer {
  display: flex;
  justify-content: center;
  padding-top: 4px;
}

.btn-reset {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 18px;
  background: rgba(84, 110, 122, 0.15);
  border: 1px solid rgba(84, 110, 122, 0.25);
  border-radius: 8px;
  color: #6b7a8d;
  font-family: 'Fira Code', monospace;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-reset:hover {
  color: #e0e4e8;
  background: rgba(84, 110, 122, 0.25);
  border-color: rgba(84, 110, 122, 0.4);
}
.reset-icon {
  font-size: 0.9rem;
}

.hint-bar {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  font-family: 'Fira Code', monospace;
  font-size: 0.72rem;
  color: rgba(0, 212, 170, 0.45);
  letter-spacing: 0.06em;
  padding: 8px 20px;
  background: rgba(8, 14, 24, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 212, 170, 0.08);
  border-radius: 20px;
  white-space: nowrap;
  animation: hintPulse 3s ease-in-out infinite;
}

@keyframes hintPulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.analyzing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px;
  color: var(--accent);
  font-family: 'Fira Code', monospace;
  font-size: 0.7rem;
  font-weight: 600;
}

.analyzing-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(0, 212, 170, 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 720px) {
  .center-panel {
    width: 90vw;
    max-width: 340px;
    padding: 18px 20px;
  }
}
</style>
