<script setup>
defineProps({
  greens: String,
  yellows: String,
  total: Number,
  groups: Array,
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

    <div v-if="groups && groups.length > 1" class="groups">
      <h2>Match Groups</h2>
      <div
        v-for="(g, i) in groups.slice(0, 8)"
        :key="i"
        class="group"
      >
        <div class="group-header">
          <span class="g-badge green">G{{ g.green }}</span>
          <span class="g-badge yellow">Y{{ g.yellow }}</span>
          <span class="g-badge red">R{{ g.red }}</span>
          <span class="g-count">{{ g.count }} words</span>
        </div>
        <div class="group-words">
          {{ g.top_words.slice(0, 6).join(', ') }}
          <span v-if="g.count > 6" class="more">+{{ g.count - 6 }} more</span>
        </div>
      </div>
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

.groups {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.group {
  padding: 6px 8px;
  border: 1px solid var(--tile-border);
  border-radius: 4px;
}

.group-header {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
}

.g-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
}
.g-badge.green { background: var(--green-dark); }
.g-badge.yellow { background: var(--yellow-dark); }
.g-badge.red { background: var(--red-dark); }

.g-count {
  margin-left: auto;
  color: var(--text-dim);
  font-size: 0.75rem;
}

.group-words {
  font-size: 0.8rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.more {
  color: var(--text-dim);
  opacity: 0.6;
}
</style>
