<script setup>
import { ref } from 'vue'

const emit = defineEmits(['parsed'])
const dragging = ref(false)
const uploading = ref(false)
const error = ref('')

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) uploadFile(file)
}

async function uploadFile(file) {
  if (!file.type.startsWith('image/')) {
    error.value = 'Please upload an image file'
    return
  }

  error.value = ''
  uploading.value = true

  try {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch('/api/upload-screenshot', {
      method: 'POST',
      body: formData,
    })
    const data = await res.json()

    if (data.guesses && data.guesses.length > 0) {
      emit('parsed', data.guesses)
    } else {
      error.value = 'Could not detect any guesses in the image. Try a clearer screenshot.'
    }
  } catch (e) {
    error.value = 'Upload failed. Please try again.'
    console.error('Upload error:', e)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="upload-section">
    <div
      class="drop-zone"
      :class="{ dragging, uploading }"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="onDrop"
      @click="$refs.fileInput.click()"
    >
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="file-input"
        @change="onFileSelect"
      />

      <div v-if="uploading" class="upload-status">
        <div class="spinner"></div>
        <span>Analyzing screenshot...</span>
      </div>

      <div v-else class="upload-prompt">
        <span class="upload-icon">&#x1F4F7;</span>
        <span class="upload-text">Drop screenshot or click to upload</span>
        <span class="upload-hint">Wordle game screenshot</span>
      </div>
    </div>

    <div v-if="error" class="upload-error">{{ error }}</div>
  </div>
</template>

<style scoped>
.upload-section {
  width: 100%;
}

.drop-zone {
  position: relative;
  border: 1.5px dashed rgba(0, 212, 170, 0.25);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(0, 212, 170, 0.03);
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: rgba(0, 212, 170, 0.5);
  background: rgba(0, 212, 170, 0.06);
}

.drop-zone.uploading {
  border-color: rgba(0, 212, 170, 0.3);
  pointer-events: none;
}

.file-input {
  display: none;
}

.upload-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.upload-icon {
  font-size: 1.3rem;
  opacity: 0.7;
}

.upload-text {
  font-family: 'Fira Code', monospace;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.03em;
}

.upload-hint {
  font-family: 'Fira Code', monospace;
  font-size: 0.58rem;
  color: var(--text-dim);
}

.upload-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--accent);
  font-family: 'Fira Code', monospace;
  font-size: 0.68rem;
  font-weight: 600;
}

.spinner {
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

.upload-error {
  margin-top: 6px;
  font-family: 'Fira Code', monospace;
  font-size: 0.62rem;
  color: #ff5252;
  text-align: center;
}
</style>
