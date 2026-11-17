import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

const storedValues = new Map<string, string>()
const testStorage: Storage = {
  get length() { return storedValues.size },
  clear: () => storedValues.clear(),
  getItem: (key) => storedValues.get(key) ?? null,
  key: (index) => [...storedValues.keys()][index] ?? null,
  removeItem: (key) => { storedValues.delete(key) },
  setItem: (key, value) => { storedValues.set(key, value) },
}

vi.stubGlobal('localStorage', testStorage)

beforeEach(() => {
  storedValues.clear()
})

afterEach(() => {
  cleanup()
})
