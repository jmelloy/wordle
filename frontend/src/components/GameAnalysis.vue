<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  analysis: Object, // { steps, total_words, solved, answer }
})
const emit = defineEmits(['close', 'loadGuesses'])

const expandedStep = ref(null)
const expandedGroups = ref(null)

function toggleStep(idx) {
  expandedStep.value = expandedStep.value === idx ? null : idx
}

function toggleGroups(idx) {
  expandedGroups.value = expandedGroups.value === idx ? null : idx
}

const colorLabel = { g: 'green', y: 'yellow', r: 'gray' }

function patternDisplay(pattern) {
  return pattern.split('').map(c => ({
    char: c,
    cls: colorLabel[c] || 'gray'
  }))
}

function pctBar(pct) {
  return Math.max(2, Math.min(100, pct))
}
</script>

<template>
  <div class="analysis-panel" v-if="analysis">
    <div class="analysis-header">
      <h2>Game Analysis</h2>
      <div class="header-actions">
        <button class="btn-load" @click="$emit('loadGuesses')" title="Load into solver">
          Load into solver
        </button>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>
    </div>

    <div class="summary-bar">
      <span class="stat">
        <span class="stat-label">Dictionary</span>
        <span class="stat-value">{{ analysis.total_words.toLocaleString() }}</span>
      </span>
      <span class="stat">
        <span class="stat-label">Guesses</span>
        <span class="stat-value">{{ analysis.steps.length }}</span>
      </span>
      <span v-if="analysis.solved" class="stat solved">
        <span class="stat-label">Answer</span>
        <span class="stat-value answer">{{ analysis.answer }}</span>
      </span>
    </div>

    <div class="steps">
      <div
        v-for="(step, idx) in analysis.steps"
        :key="idx"
        class="step"
        :class="{ expanded: expandedStep === idx }"
      >
        <!-- Step header -->
        <div class="step-header" @click="toggleStep(idx)">
          <div class="step-number">{{ step.step }}</div>

          <div class="step-tiles">
            <span
              v-for="(ch, i) in step.guess.split('')"
              :key="i"
              class="mini-tile"
              :class="colorLabel[step.result[i]]"
            >{{ ch }}</span>
          </div>

          <div class="step-stats">
            <span class="reduction">
              {{ step.candidates_before.toLocaleString() }}
              <span class="arrow">&rarr;</span>
              {{ step.candidates_after.toLocaleString() }}
            </span>
            <span class="elim-pct">-{{ step.elimination_pct }}%</span>
          </div>

          <span class="expand-icon">{{ expandedStep === idx ? '&#x25B2;' : '&#x25BC;' }}</span>
        </div>

        <!-- Reduction bar -->
        <div class="reduction-bar-track">
          <div
            class="reduction-bar-fill"
            :style="{ width: pctBar(step.elimination_pct) + '%' }"
          ></div>
          <div
            class="reduction-bar-remaining"
            :style="{
              width: pctBar(100 - step.elimination_pct) + '%',
              left: pctBar(step.elimination_pct) + '%'
            }"
          ></div>
        </div>

        <!-- Expanded detail -->
        <div v-if="expandedStep === idx" class="step-detail">
          <!-- Letter analysis -->
          <div class="detail-section">
            <h3>What we learned</h3>
            <div class="letter-insights">
              <div
                v-for="la in step.letter_analysis"
                :key="la.position"
                class="insight"
              >
                <span class="insight-tile" :class="colorLabel[la.color]">{{ la.letter }}</span>
                <span class="insight-text">{{ la.info }}</span>
              </div>
            </div>
          </div>

          <!-- Constraint state -->
          <div class="detail-section">
            <h3>Accumulated constraints</h3>
            <div class="constraints-row">
              <span class="constraint-pattern">
                <span
                  v-for="(ch, i) in step.greens.split('')"
                  :key="i"
                  class="pattern-ch"
                  :class="{ matched: ch !== '.' }"
                >{{ ch }}</span>
              </span>
              <span v-if="step.yellows" class="constraint-yellows">
                must have: <span class="yl-letters">{{ step.yellows }}</span>
              </span>
            </div>
          </div>

          <!-- Group distribution -->
          <div class="detail-section">
            <h3 @click.stop="toggleGroups(idx)" class="clickable-header">
              Pattern groups ({{ step.total_groups }} distinct)
              <span class="expand-icon small">{{ expandedGroups === idx ? '&#x25B2;' : '&#x25BC;' }}</span>
            </h3>
            <p class="group-explanation">
              This guess split the {{ step.candidates_before.toLocaleString() }} candidates
              into {{ step.total_groups }} groups by response pattern.
              {{ step.total_groups > 1 ? 'More groups = more information gained.' : '' }}
            </p>

            <div v-if="expandedGroups === idx" class="group-list">
              <div
                v-for="group in step.group_distribution"
                :key="group.pattern"
                class="group-row"
                :class="{ actual: group.is_actual }"
              >
                <div class="group-pattern">
                  <span
                    v-for="(p, i) in patternDisplay(group.pattern)"
                    :key="i"
                    class="micro-tile"
                    :class="p.cls"
                  ></span>
                </div>
                <div class="group-count">{{ group.count }}</div>
                <div class="group-bar-track">
                  <div
                    class="group-bar-fill"
                    :class="{ actual: group.is_actual }"
                    :style="{ width: Math.max(2, group.count / step.candidates_before * 100) + '%' }"
                  ></div>
                </div>
                <div class="group-words">
                  {{ group.sample_words.join(', ') }}
                  <span v-if="group.count > 5" class="more">+{{ group.count - 5 }}</span>
                </div>
                <span v-if="group.is_actual" class="actual-badge">actual</span>
              </div>
            </div>
          </div>

          <!-- Top remaining -->
          <div v-if="step.top_remaining.length > 0" class="detail-section">
            <h3>Top candidates after this guess</h3>
            <div class="top-words">
              <span
                v-for="w in step.top_remaining"
                :key="w.word"
                class="top-word"
                :title="`freq: ${w.freq}, eliminations: ${w.eliminations}`"
              >{{ w.word }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.analysis-header h2 {
  font-family: 'Syne', sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--accent);
  text-transform: none;
  letter-spacing: 0;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-load {
  font-family: 'Fira Code', monospace;
  font-size: 0.58rem;
  font-weight: 600;
  color: var(--accent);
  background: rgba(0, 212, 170, 0.08);
  border: 1px solid rgba(0, 212, 170, 0.2);
  border-radius: 6px;
  padding: 4px 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: all 0.2s;
}
.btn-load:hover {
  background: rgba(0, 212, 170, 0.15);
  border-color: rgba(0, 212, 170, 0.4);
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.2rem;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.15s;
}
.btn-close:hover {
  color: #ff5252;
  background: rgba(255, 82, 82, 0.1);
}

/* Summary bar */
.summary-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 12px;
  background: rgba(0, 212, 170, 0.04);
  border: 1px solid rgba(0, 212, 170, 0.08);
  border-radius: 8px;
  flex: 1;
}

.stat-label {
  font-family: 'Fira Code', monospace;
  font-size: 0.52rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.stat-value {
  font-family: 'Fira Code', monospace;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text);
}

.stat.solved {
  border-color: rgba(0, 200, 83, 0.25);
  background: rgba(0, 200, 83, 0.06);
}

.stat-value.answer {
  color: var(--green);
  text-transform: uppercase;
  letter-spacing: 0.2em;
}

/* Steps */
.steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step {
  background: rgba(0, 212, 170, 0.02);
  border: 1px solid rgba(0, 212, 170, 0.06);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.step.expanded {
  border-color: rgba(0, 212, 170, 0.15);
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.step-header:hover {
  background: rgba(0, 212, 170, 0.04);
}

.step-number {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 212, 170, 0.1);
  border-radius: 50%;
  font-family: 'Fira Code', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  color: var(--accent);
  flex-shrink: 0;
}

.step-tiles {
  display: flex;
  gap: 2px;
}

.mini-tile {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  border-radius: 3px;
  color: white;
  font-family: 'Fira Code', monospace;
}

.mini-tile.green { background: var(--green); }
.mini-tile.yellow { background: var(--yellow-dark); color: #1a1a1a; }
.mini-tile.gray { background: var(--red-dark); }

.step-stats {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'Fira Code', monospace;
  font-size: 0.58rem;
}

.reduction {
  color: var(--text-dim);
}

.arrow {
  color: rgba(0, 212, 170, 0.4);
  margin: 0 2px;
}

.elim-pct {
  color: #ff5252;
  font-weight: 700;
  font-size: 0.62rem;
}

.expand-icon {
  color: var(--text-dim);
  font-size: 0.5rem;
  flex-shrink: 0;
}

/* Reduction bar */
.reduction-bar-track {
  height: 3px;
  position: relative;
  background: rgba(255, 255, 255, 0.03);
}

.reduction-bar-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, #ff5252, #ff8a80);
  border-radius: 0 2px 2px 0;
  transition: width 0.4s ease;
}

.reduction-bar-remaining {
  position: absolute;
  top: 0;
  height: 100%;
  background: rgba(0, 212, 170, 0.3);
  border-radius: 2px;
  transition: all 0.4s ease;
}

/* Step detail */
.step-detail {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-top: 1px solid rgba(0, 212, 170, 0.06);
}

.detail-section h3 {
  font-family: 'Fira Code', monospace;
  font-size: 0.58rem;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}

.clickable-header {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}

.expand-icon.small {
  font-size: 0.45rem;
}

/* Letter insights */
.letter-insights {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.insight {
  display: flex;
  align-items: center;
  gap: 8px;
}

.insight-tile {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  border-radius: 3px;
  color: white;
  font-family: 'Fira Code', monospace;
  flex-shrink: 0;
}

.insight-tile.green { background: var(--green); }
.insight-tile.yellow { background: var(--yellow-dark); color: #1a1a1a; }
.insight-tile.gray { background: var(--red-dark); }

.insight-text {
  font-family: 'Fira Code', monospace;
  font-size: 0.58rem;
  color: var(--text-dim);
}

/* Constraints */
.constraints-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.constraint-pattern {
  display: flex;
  gap: 2px;
}

.pattern-ch {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 212, 170, 0.1);
  border-radius: 3px;
  font-weight: 700;
  font-size: 0.6rem;
  text-transform: uppercase;
  color: var(--text-dim);
  font-family: 'Fira Code', monospace;
}

.pattern-ch.matched {
  background: rgba(0, 200, 83, 0.2);
  border-color: rgba(0, 200, 83, 0.4);
  color: var(--green);
}

.constraint-yellows {
  font-family: 'Fira Code', monospace;
  font-size: 0.58rem;
  color: var(--text-dim);
}

.yl-letters {
  color: var(--yellow);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
}

/* Groups */
.group-explanation {
  font-family: 'Fira Code', monospace;
  font-size: 0.55rem;
  color: var(--text-dim);
  margin-bottom: 6px;
  line-height: 1.5;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  max-height: 200px;
  overflow-y: auto;
}

.group-list::-webkit-scrollbar {
  width: 3px;
}
.group-list::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 170, 0.15);
  border-radius: 2px;
}

.group-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 0.52rem;
}

.group-row.actual {
  background: rgba(0, 212, 170, 0.06);
  border: 1px solid rgba(0, 212, 170, 0.12);
}

.group-pattern {
  display: flex;
  gap: 1px;
  flex-shrink: 0;
}

.micro-tile {
  width: 8px;
  height: 8px;
  border-radius: 1px;
}
.micro-tile.green { background: var(--green); }
.micro-tile.yellow { background: var(--yellow-dark); }
.micro-tile.gray { background: var(--red-dark); }

.group-count {
  width: 28px;
  text-align: right;
  font-weight: 700;
  color: var(--text);
  flex-shrink: 0;
}

.group-bar-track {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 2px;
  overflow: hidden;
  min-width: 30px;
}

.group-bar-fill {
  height: 100%;
  background: rgba(0, 212, 170, 0.25);
  border-radius: 2px;
  transition: width 0.3s;
}

.group-bar-fill.actual {
  background: var(--accent);
}

.group-words {
  color: var(--text-dim);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.more {
  color: rgba(0, 212, 170, 0.4);
}

.actual-badge {
  font-size: 0.48rem;
  font-weight: 700;
  color: var(--accent);
  background: rgba(0, 212, 170, 0.1);
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
}

/* Top words */
.top-words {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.top-word {
  font-family: 'Fira Code', monospace;
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--text);
  background: rgba(0, 212, 170, 0.06);
  border: 1px solid rgba(0, 212, 170, 0.1);
  border-radius: 4px;
  padding: 2px 8px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
</style>
