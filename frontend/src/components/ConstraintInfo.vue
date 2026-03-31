<script setup>
defineProps({
  greens: String,
  yellows: String,
  total: Number,
  matchKey: Array,
})
</script>

<template>
  <div class="info">
    <div class="constraint-row">
      <span class="label">Pattern:</span>
      <span class="pattern">
        <span
          v-for="(ch, i) in greens.split('')"
          :key="i"
          class="pattern-char"
          :class="{ matched: ch !== '.' }"
        >{{ ch }}</span>
      </span>
    </div>

    <div v-if="yellows" class="constraint-row">
      <span class="label">Contains:</span>
      <span class="yellow-letters">
        <span v-for="ch in yellows.split('')" :key="ch" class="yl">{{ ch }}</span>
      </span>
    </div>

    <div class="constraint-row">
      <span class="label">Remaining:</span>
      <span class="count">{{ total }}</span>
    </div>

    <div v-if="matchKey" class="constraint-row">
      <span class="label">Match:</span>
      <span class="match-badges">
        <span class="badge green">G{{ matchKey[0] }}</span>
        <span class="badge yellow">Y{{ matchKey[1] }}</span>
        <span class="badge red">R{{ matchKey[2] }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--bg-light);
  border-radius: 6px;
  border: 1px solid var(--tile-border);
  font-size: 0.85rem;
}

.constraint-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  color: var(--text-dim);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 80px;
}

.pattern {
  display: flex;
  gap: 3px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  font-size: 1.1rem;
}

.pattern-char {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--tile-border);
  border-radius: 2px;
}
.pattern-char.matched {
  background: var(--green);
  border-color: var(--green);
}

.yellow-letters {
  display: flex;
  gap: 3px;
}

.yl {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--yellow);
  border-radius: 2px;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.9rem;
}

.count {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text);
}

.match-badges {
  display: flex;
  gap: 6px;
}

.badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 3px;
}
.badge.green { background: var(--green-dark); }
.badge.yellow { background: var(--yellow-dark); }
.badge.red { background: var(--red-dark); }
</style>
