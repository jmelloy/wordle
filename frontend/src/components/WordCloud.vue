<script setup>
import { computed } from 'vue'

const props = defineProps({
  candidates: Array,
  loading: Boolean,
})
const emit = defineEmits(['select'])

// Compute font sizes based on rank/frequency
const cloudWords = computed(() => {
  if (!props.candidates || props.candidates.length === 0) return []

  const maxFreq = Math.max(...props.candidates.map(c => c.freq || 1))
  const minFreq = Math.min(...props.candidates.map(c => c.freq || 1))
  const range = Math.max(maxFreq - minFreq, 1)

  return props.candidates.map((c, i) => {
    // Normalize frequency to 0-1, then map to font size
    const norm = (c.freq - minFreq) / range
    const fontSize = 0.65 + norm * 1.8 // 0.65rem to 2.45rem
    const opacity = 0.4 + norm * 0.6 // 0.4 to 1.0

    // Color based on match quality (rank)
    let hue
    if (i < 3) hue = 120 // green for top 3
    else if (i < 10) hue = 55 // yellow-ish
    else hue = 0 // neutral

    const saturation = i < 10 ? 50 : 0
    const lightness = 50 + (1 - norm) * 25

    return {
      ...c,
      fontSize: fontSize + 'rem',
      opacity,
      color: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
    }
  })
})
</script>

<template>
  <div class="cloud-container">
    <div v-if="loading" class="loading">Solving...</div>

    <div v-else-if="cloudWords.length === 0" class="empty">
      <p>No candidates yet.</p>
      <p class="hint">Enter a word and set the colors to see possibilities.</p>
    </div>

    <div v-else class="cloud">
      <button
        v-for="w in cloudWords"
        :key="w.word"
        class="cloud-word"
        :style="{
          fontSize: w.fontSize,
          opacity: w.opacity,
          color: w.color,
        }"
        @click="emit('select', w.word)"
        :title="`${w.word} — rank #${w.rank}, freq: ${w.freq}`"
      >
        {{ w.word }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.cloud-container {
  min-height: 300px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-dim);
  font-size: 1.1rem;
  animation: pulse 1s ease-in-out infinite alternate;
}

@keyframes pulse {
  from { opacity: 0.5; }
  to { opacity: 1; }
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
}
.empty .hint {
  font-size: 0.85rem;
  margin-top: 8px;
}

.cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  align-items: baseline;
  justify-content: center;
  padding: 16px 8px;
  background: var(--bg-light);
  border-radius: 8px;
  border: 1px solid var(--tile-border);
  line-height: 1.4;
}

.cloud-word {
  background: none;
  border: none;
  font-family: inherit;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 3px;
  transition: all 0.15s;
}

.cloud-word:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: scale(1.1);
}
</style>
