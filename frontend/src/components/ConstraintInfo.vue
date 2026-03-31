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
      <span class="pattern">
        <span
          v-for="(ch, i) in greens.split('')"
          :key="i"
          class="pattern-char"
          :class="{ matched: ch !== '.' }"
        >{{ ch }}</span>
      </span>

      <span v-if="yellows" class="yellow-letters">
        <span v-for="ch in yellows.split('')" :key="ch" class="yl">{{ ch }}</span>
      </span>

      <span v-if="matchKey" class="match-badges">
        <span class="badge green">{{ matchKey[0] }}</span>
        <span class="badge yellow">{{ matchKey[1] }}</span>
        <span class="badge red">{{ matchKey[2] }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.info {
  padding: 10px 0 0;
  border-top: 1px solid rgba(0, 212, 170, 0.08);
}

.constraint-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pattern {
  display: flex;
  gap: 3px;
}

.pattern-char {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 212, 170, 0.1);
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-dim);
  font-family: 'Fira Code', monospace;
}
.pattern-char.matched {
  background: rgba(0, 200, 83, 0.2);
  border-color: rgba(0, 200, 83, 0.4);
  color: var(--green);
}

.yellow-letters {
  display: flex;
  gap: 3px;
}

.yl {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(200, 164, 21, 0.2);
  border: 1px solid rgba(200, 164, 21, 0.3);
  border-radius: 4px;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.7rem;
  color: var(--yellow);
  font-family: 'Fira Code', monospace;
}

.match-badges {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.badge {
  font-family: 'Fira Code', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}
.badge.green {
  background: rgba(0, 200, 83, 0.2);
  color: var(--green);
}
.badge.yellow {
  background: rgba(200, 164, 21, 0.15);
  color: var(--yellow);
}
.badge.red {
  background: rgba(84, 110, 122, 0.2);
  color: var(--red);
}
</style>
