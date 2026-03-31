<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps({
  candidates: Array,
  loading: Boolean,
  startingWords: Array,
})
const emit = defineEmits(['select'])

const container = ref(null)
const canvasRef = ref(null)
const width = ref(window.innerWidth)
const height = ref(window.innerHeight)
const hoveredWord = ref(null)
const time = ref(0)
let animFrame = null
let resizeObserver = null

// Use candidates if available, otherwise starting words
// Cap at 60 nodes max for readability in the web layout
const MAX_WEB_NODES = 60

const activeWords = computed(() => {
  if (props.candidates && props.candidates.length > 0) {
    return props.candidates.slice(0, MAX_WEB_NODES).map((c, i) => ({
      word: c.word,
      rank: c.rank || i + 1,
      eliminations: c.eliminations || 0,
      freq: c.freq || 0,
      score: c.score || 0,
      isStarter: false,
    }))
  }
  if (props.startingWords && props.startingWords.length > 0) {
    return props.startingWords.slice(0, 16).map((w, i) => ({
      word: w.word,
      rank: i + 1,
      eliminations: 100 - i * 5,
      freq: 1000,
      score: w.score || 0,
      isStarter: true,
    }))
  }
  return []
})

// Compute node positions in concentric rings
const webNodes = computed(() => {
  const words = activeWords.value
  if (words.length === 0) return []

  const cx = width.value / 2
  const cy = height.value / 2
  // Ensure inner ring clears the center panel (~340x450px) and outer ring stays in viewport
  const panelClearance = 260
  const viewportLimit = Math.min(width.value, height.value) * 0.44
  const minR = Math.max(panelClearance, viewportLimit * 0.52)
  const maxR = Math.max(minR + 120, viewportLimit)

  // Determine elimination range for sizing
  const elims = words.map(w => w.eliminations || 1)
  const maxElim = Math.max(...elims)
  const minElim = Math.min(...elims)
  const elimRange = Math.max(maxElim - minElim, 1)

  // Ring definitions — 4 tiers by rank
  const ringDefs = [
    { maxRank: 5, radiusFrac: 0.0, fontBase: 1.05 },
    { maxRank: 15, radiusFrac: 0.33, fontBase: 0.85 },
    { maxRank: 35, radiusFrac: 0.66, fontBase: 0.72 },
    { maxRank: Infinity, radiusFrac: 1.0, fontBase: 0.6 },
  ]

  const rings = ringDefs.map(r => ({
    ...r,
    radius: minR + (maxR - minR) * r.radiusFrac,
    members: [],
  }))

  words.forEach(w => {
    const ring = rings.find(r => w.rank <= r.maxRank)
    ring.members.push(w)
  })

  const result = []
  let nodeId = 0
  rings.forEach((ring, ringIdx) => {
    const count = ring.members.length
    if (count === 0) return
    // Offset each ring slightly so nodes don't align radially
    const angleOffset = ringIdx * 0.4 + 0.2
    ring.members.forEach((w, i) => {
      const angle = (i / count) * Math.PI * 2 - Math.PI / 2 + angleOffset
      const elimNorm = (w.eliminations - minElim) / elimRange

      // Color by rank tier
      let color, glowColor
      if (w.rank <= 3) {
        color = '#00e5b0'
        glowColor = 'rgba(0, 229, 176, 0.6)'
      } else if (w.rank <= 10) {
        color = '#5ee8c5'
        glowColor = 'rgba(94, 232, 197, 0.35)'
      } else if (w.rank <= 25) {
        color = '#c8a832'
        glowColor = 'rgba(200, 168, 50, 0.25)'
      } else {
        color = '#6b7a8d'
        glowColor = 'rgba(107, 122, 141, 0.15)'
      }

      result.push({
        id: nodeId++,
        word: w.word,
        rank: w.rank,
        eliminations: w.eliminations,
        freq: w.freq,
        isStarter: w.isStarter,
        x: cx + ring.radius * Math.cos(angle),
        y: cy + ring.radius * Math.sin(angle),
        angle,
        ringRadius: ring.radius,
        ringIndex: ringIdx,
        fontSize: ring.fontBase + elimNorm * 0.3,
        opacity: 0.4 + elimNorm * 0.6,
        color,
        glowColor,
        floatDelay: Math.random() * -10,
        floatDuration: 8 + Math.random() * 6,
        floatAmplitude: 2 + Math.random() * 3,
      })
    })
  })

  return result
})

// Precompute connections between nodes
const connections = computed(() => {
  const nodes = webNodes.value
  if (nodes.length < 2) return []

  const conns = []
  const connected = new Set()

  // Connect each node to its 2 nearest neighbors
  nodes.forEach(node => {
    const nearest = [...nodes]
      .filter(n => n.id !== node.id)
      .map(n => ({
        node: n,
        dist: Math.hypot(n.x - node.x, n.y - node.y),
      }))
      .sort((a, b) => a.dist - b.dist)
      .slice(0, 2)

    nearest.forEach(({ node: n, dist }) => {
      const key = [Math.min(node.id, n.id), Math.max(node.id, n.id)].join('-')
      if (!connected.has(key) && dist < 400) {
        connected.add(key)
        conns.push({ from: node, to: n })
      }
    })
  })

  // Also connect adjacent nodes on same ring
  const ringGroups = {}
  nodes.forEach(n => {
    if (!ringGroups[n.ringIndex]) ringGroups[n.ringIndex] = []
    ringGroups[n.ringIndex].push(n)
  })
  Object.values(ringGroups).forEach(group => {
    // Sort by angle
    group.sort((a, b) => a.angle - b.angle)
    for (let i = 0; i < group.length; i++) {
      const next = group[(i + 1) % group.length]
      const key = [Math.min(group[i].id, next.id), Math.max(group[i].id, next.id)].join('-')
      if (!connected.has(key)) {
        connected.add(key)
        conns.push({ from: group[i], to: next })
      }
    }
  })

  return conns
})

// Canvas drawing
function drawCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const w = width.value
  const h = height.value

  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = w + 'px'
  canvas.style.height = h + 'px'
  ctx.scale(dpr, dpr)

  ctx.clearRect(0, 0, w, h)

  const cx = w / 2
  const cy = h / 2
  const panelClear = 260
  const viewLimit = Math.min(w, h) * 0.44
  const minR = Math.max(panelClear, viewLimit * 0.52)
  const maxR = Math.max(minR + 120, viewLimit)
  const t = time.value

  // Subtle center glow
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR * 1.3)
  grad.addColorStop(0, 'rgba(0, 212, 170, 0.05)')
  grad.addColorStop(0.4, 'rgba(0, 212, 170, 0.02)')
  grad.addColorStop(1, 'transparent')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, w, h)

  // Concentric ring guides — more visible
  const ringCount = 6
  for (let i = 0; i < ringCount; i++) {
    const r = minR * 0.7 + (maxR * 1.1 - minR * 0.7) * (i / (ringCount - 1))
    const pulse = Math.sin(t * 0.0008 + i * 0.5) * 0.03 + 0.08
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.strokeStyle = `rgba(0, 212, 170, ${pulse})`
    ctx.lineWidth = 0.7
    ctx.stroke()
  }

  // Radial threads
  const radialCount = 24
  for (let i = 0; i < radialCount; i++) {
    const angle = (i / radialCount) * Math.PI * 2
    const pulse = Math.sin(t * 0.0006 + i * 0.8) * 0.02 + 0.055
    ctx.beginPath()
    ctx.moveTo(cx + (minR * 0.6) * Math.cos(angle), cy + (minR * 0.6) * Math.sin(angle))
    ctx.lineTo(cx + (maxR * 1.15) * Math.cos(angle), cy + (maxR * 1.15) * Math.sin(angle))
    ctx.strokeStyle = `rgba(0, 212, 170, ${pulse})`
    ctx.lineWidth = 0.5
    ctx.stroke()
  }

  // Node connections (web threads between words) — brighter
  connections.value.forEach(({ from, to }) => {
    const pulse = Math.sin(t * 0.001 + from.id * 0.3) * 0.04 + 0.12
    const midX = (from.x + to.x) / 2 + (cx - (from.x + to.x) / 2) * 0.1
    const midY = (from.y + to.y) / 2 + (cy - (from.y + to.y) / 2) * 0.1

    ctx.beginPath()
    ctx.moveTo(from.x, from.y)
    ctx.quadraticCurveTo(midX, midY, to.x, to.y)
    ctx.strokeStyle = `rgba(0, 212, 170, ${pulse})`
    ctx.lineWidth = 0.8
    ctx.stroke()
  })

  // Radial lines from center to each node
  webNodes.value.forEach(node => {
    const pulse = Math.sin(t * 0.0007 + node.id * 0.5) * 0.02 + 0.05
    ctx.beginPath()
    ctx.moveTo(cx + (minR * 0.6) * Math.cos(node.angle), cy + (minR * 0.6) * Math.sin(node.angle))
    ctx.lineTo(node.x, node.y)
    ctx.strokeStyle = `rgba(0, 212, 170, ${pulse})`
    ctx.lineWidth = 0.4
    ctx.stroke()
  })

  // Glow dots at node positions
  webNodes.value.forEach(node => {
    const pulse = Math.sin(t * 0.002 + node.id) * 0.3 + 0.7
    const isHovered = hoveredWord.value === node.word
    const dotR = isHovered ? 4 : 2
    ctx.beginPath()
    ctx.arc(node.x, node.y, dotR, 0, Math.PI * 2)
    ctx.fillStyle = isHovered
      ? 'rgba(0, 229, 176, 0.8)'
      : `rgba(0, 212, 170, ${0.15 * pulse})`
    ctx.fill()
  })
}

function animate(timestamp) {
  time.value = timestamp
  drawCanvas()
  animFrame = requestAnimationFrame(animate)
}

function handleResize() {
  if (container.value) {
    width.value = container.value.clientWidth
    height.value = container.value.clientHeight
  }
}

onMounted(() => {
  handleResize()
  resizeObserver = new ResizeObserver(handleResize)
  if (container.value) resizeObserver.observe(container.value)
  animFrame = requestAnimationFrame(animate)
})

onUnmounted(() => {
  if (animFrame) cancelAnimationFrame(animFrame)
  if (resizeObserver) resizeObserver.disconnect()
})

// Redraw when nodes change
watch(webNodes, () => nextTick(drawCanvas), { deep: false })
</script>

<template>
  <div ref="container" class="web-container">
    <canvas ref="canvasRef" class="web-canvas" />

    <div class="words-layer">
      <button
        v-for="node in webNodes"
        :key="node.word"
        class="web-word"
        :class="{
          hovered: hoveredWord === node.word,
          'rank-top': node.rank <= 3,
          'rank-mid': node.rank > 3 && node.rank <= 10,
          starter: node.isStarter,
        }"
        :style="{
          left: node.x + 'px',
          top: node.y + 'px',
          fontSize: node.fontSize + 'rem',
          color: node.color,
          opacity: node.opacity,
          '--float-delay': node.floatDelay + 's',
          '--float-duration': node.floatDuration + 's',
          '--float-x': node.floatAmplitude + 'px',
          '--float-y': (node.floatAmplitude * 0.7) + 'px',
          '--glow-color': node.glowColor,
        }"
        @click="emit('select', node.word)"
        @mouseenter="hoveredWord = node.word"
        @mouseleave="hoveredWord = null"
        :title="node.isStarter
          ? `${node.word} — suggested starter`
          : `${node.word} — #${node.rank}, eliminates ${node.eliminations} patterns`"
      >
        {{ node.word }}
      </button>
    </div>

    <transition name="fade">
      <div v-if="loading" class="loading-overlay">
        <div class="loading-ring" />
        <span class="loading-text">Weaving...</span>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.web-container {
  position: fixed;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}

.web-canvas {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.words-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

.web-word {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: auto;
  background: none;
  border: none;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
  transition: transform 0.2s ease, opacity 0.2s ease, text-shadow 0.2s ease;
  animation: webGlow var(--float-duration) ease-in-out infinite;
  animation-delay: var(--float-delay);
  text-shadow: 0 0 8px var(--glow-color);
}

.web-word:hover,
.web-word.hovered {
  transform: translate(-50%, -50%) scale(1.25);
  opacity: 1 !important;
  text-shadow: 0 0 20px var(--glow-color), 0 0 40px var(--glow-color);
  z-index: 10;
  background: rgba(0, 212, 170, 0.08);
}

.web-word.rank-top {
  font-weight: 700;
}

@keyframes webGlow {
  0%, 100% {
    text-shadow: 0 0 8px var(--glow-color);
    filter: brightness(1);
  }
  50% {
    text-shadow: 0 0 16px var(--glow-color), 0 0 24px var(--glow-color);
    filter: brightness(1.15);
  }
}

/* Loading overlay */
.loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(6, 10, 16, 0.6);
  gap: 16px;
}

.loading-ring {
  width: 48px;
  height: 48px;
  border: 2px solid rgba(0, 212, 170, 0.15);
  border-top-color: #00d4aa;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-family: 'Fira Code', monospace;
  font-size: 0.85rem;
  color: #00d4aa;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
