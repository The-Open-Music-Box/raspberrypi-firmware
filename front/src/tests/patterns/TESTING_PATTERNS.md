# Patterns de Tests Frontend - The Open Music Box

## Vue d'ensemble

Ce document présente les patterns de test standardisés pour maintenir la cohérence et la qualité des tests dans l'application frontend Vue.js/TypeScript.

## Patterns Généraux

### Structure de Fichier de Test

```typescript
/**
 * Unit tests for [ComponentName].vue component
 *
 * Tests [description of component responsibility]:
 * - [Key functionality 1]
 * - [Key functionality 2]
 * - [Key functionality 3]
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import Component from '@/path/to/Component.vue'
import { testHelpers } from '@/tests/utils/testHelpers'

// Mocks section
vi.mock(...)

describe('ComponentName.vue', () => {
  let wrapper: VueWrapper<any>

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Group 1', () => {
    it('should do something specific', () => {
      // Test implementation
    })
  })
})
```

## Patterns de Mocking

### 1. Composants Enfants

```typescript
// Pattern simple pour composants sans logique
vi.mock('@/components/child/ChildComponent.vue', () => ({
  default: {
    name: 'ChildComponent',
    template: '<div data-testid="child-component">Mocked Child</div>',
    props: ['prop1', 'prop2'],
    emits: ['event1', 'event2']
  }
}))

// Pattern avancé pour composants avec interactions
vi.mock('@/components/child/InteractiveChild.vue', () => ({
  default: {
    name: 'InteractiveChild',
    template: `
      <div data-testid="interactive-child">
        <button @click="$emit('action', 'test-data')">Action</button>
        <span>{{ prop1 }}</span>
      </div>
    `,
    props: ['prop1', 'prop2'],
    emits: ['action', 'update']
  }
}))
```

### 2. Stores Pinia

```typescript
// Pattern pour stores composition API
const createMockStore = () => ({
  // State
  items: [],
  isLoading: false,
  error: null,

  // Getters (computed que retournent des fonctions)
  getItemById: vi.fn((id) => null),
  getAllItems: [],
  hasItems: vi.fn(() => false),

  // Actions
  loadItems: vi.fn().mockResolvedValue(undefined),
  createItem: vi.fn().mockResolvedValue(undefined),
  updateItem: vi.fn().mockResolvedValue(undefined),
  deleteItem: vi.fn().mockResolvedValue(undefined),

  // Helper pour les tests
  _setItems: (items) => { /* logic to update mock */ }
})

vi.mock('@/stores/exampleStore', () => ({
  useExampleStore: () => createMockStore()
}))
```

### 3. Services API

```typescript
// Pattern pour services
const createMockApiService = () => ({
  endpoint: {
    get: vi.fn().mockResolvedValue({ status: 'success', data: {} }),
    post: vi.fn().mockResolvedValue({ status: 'success', data: {} }),
    put: vi.fn().mockResolvedValue({ status: 'success', data: {} }),
    delete: vi.fn().mockResolvedValue({ status: 'success' })
  }
})

vi.mock('@/services/apiService', () => ({
  default: createMockApiService()
}))
```

### 4. Utilitaires et Composables

```typescript
// Pattern pour utilitaires
vi.mock('@/utils/utility', () => ({
  utilityFunction: vi.fn((input) => `mocked-${input}`),
  formatData: vi.fn((data) => ({ formatted: true, data }))
}))

// Pattern pour composables
vi.mock('@/composables/useExample', () => ({
  useExample: () => ({
    data: ref(null),
    loading: ref(false),
    error: ref(null),
    fetchData: vi.fn().mockResolvedValue(undefined)
  })
}))
```

## Patterns de Test par Type de Composant

### 1. Composants de Présentation

```typescript
describe('PresentationComponent.vue', () => {
  const defaultProps = {
    title: 'Test Title',
    items: [{ id: 1, name: 'Item 1' }]
  }

  it('should render with default props', () => {
    wrapper = mount(Component, {
      props: defaultProps
    })

    expect(wrapper.find('h1').text()).toBe('Test Title')
    expect(wrapper.findAll('.item')).toHaveLength(1)
  })

  it('should handle empty state', () => {
    wrapper = mount(Component, {
      props: { ...defaultProps, items: [] }
    })

    expect(wrapper.find('[data-testid="empty-state"]').exists()).toBe(true)
  })
})
```

### 2. Composants avec État Local

```typescript
describe('StatefulComponent.vue', () => {
  it('should manage local state correctly', async () => {
    wrapper = mount(Component)

    expect(wrapper.vm.isOpen).toBe(false)

    await wrapper.find('[data-testid="toggle-button"]').trigger('click')

    expect(wrapper.vm.isOpen).toBe(true)
    expect(wrapper.find('[data-testid="content"]').isVisible()).toBe(true)
  })
})
```

### 3. Composants avec Stores

```typescript
describe('StoreConnectedComponent.vue', () => {
  it('should interact with store correctly', async () => {
    const mockStore = createMockStore()

    wrapper = mount(Component)

    await wrapper.find('[data-testid="load-button"]').trigger('click')

    expect(mockStore.loadItems).toHaveBeenCalled()
  })

  it('should react to store changes', async () => {
    const mockStore = createMockStore()
    mockStore._setItems([{ id: 1, name: 'Test Item' }])

    wrapper = mount(Component)

    expect(wrapper.findAll('.item')).toHaveLength(1)
  })
})
```

### 4. Composants avec Événements

```typescript
describe('EventEmittingComponent.vue', () => {
  it('should emit events with correct payload', async () => {
    wrapper = mount(Component)

    await wrapper.find('[data-testid="action-button"]').trigger('click')

    const emittedEvents = wrapper.emitted('action')
    expect(emittedEvents).toBeTruthy()
    expect(emittedEvents![0]).toEqual(['expected-payload'])
  })

  it('should handle parent event listeners', async () => {
    const onAction = vi.fn()

    wrapper = mount(Component, {
      attrs: {
        onAction
      }
    })

    await wrapper.find('[data-testid="action-button"]').trigger('click')

    expect(onAction).toHaveBeenCalledWith('expected-payload')
  })
})
```

## Patterns d'Assertion

### 1. Vérifications de Rendu

```typescript
// Existence d'éléments
expect(wrapper.find('[data-testid="element"]').exists()).toBe(true)

// Contenu textuel
expect(wrapper.find('h1').text()).toBe('Expected Text')

// Classes CSS
expect(wrapper.find('.element').classes()).toContain('active')

// Attributs
expect(wrapper.find('input').attributes('disabled')).toBeDefined()

// Visibilité
expect(wrapper.find('.element').isVisible()).toBe(true)
```

### 2. Vérifications d'Événements

```typescript
// Événements émis
const emittedEvents = wrapper.emitted('event-name')
expect(emittedEvents).toBeTruthy()
expect(emittedEvents![0]).toEqual(['expected', 'payload'])

// Nombre d'appels
expect(emittedEvents).toHaveLength(2)

// Dernier appel
expect(emittedEvents![emittedEvents!.length - 1]).toEqual(['last', 'call'])
```

### 3. Vérifications de Props

```typescript
// Props passées aux composants enfants
const childComponent = wrapper.findComponent({ name: 'ChildComponent' })
expect(childComponent.props('propName')).toBe('expected-value')

// Props multiples
expect(childComponent.props()).toEqual({
  prop1: 'value1',
  prop2: 'value2'
})
```

### 4. Vérifications de Mocks

```typescript
// Appels de fonctions
expect(mockFunction).toHaveBeenCalled()
expect(mockFunction).toHaveBeenCalledWith('expected', 'arguments')
expect(mockFunction).toHaveBeenCalledTimes(1)

// Store actions
expect(mockStore.action).toHaveBeenCalledWith(expectedPayload)
```

## Patterns de Configuration

### 1. Configuration de Mount

```typescript
const createMountOptions = (overrides = {}) => ({
  props: {
    // default props
    ...overrides.props
  },
  global: {
    stubs: createComponentStubs(),
    mocks: {
      $t: (key: string) => key,
      $route: { path: '/', params: {}, query: {} },
      $router: { push: vi.fn(), replace: vi.fn() }
    },
    ...overrides.global
  },
  ...overrides
})

// Usage
wrapper = mount(Component, createMountOptions({
  props: { customProp: 'value' }
}))
```

### 2. Configuration avec Stores

```typescript
const mountWithStores = (component, options = {}) => {
  const mockStores = setupMockStores(options.storeState)

  return mount(component, {
    ...createMountOptions(),
    ...options
  })
}
```

## Patterns de Gestion d'État Asynchrone

### 1. Tests avec Promesses

```typescript
it('should handle async operations', async () => {
  const mockAsyncFunction = vi.fn().mockResolvedValue('result')

  wrapper = mount(Component)

  await wrapper.find('[data-testid="async-button"]').trigger('click')
  await flushPromises() // Wait for all promises to resolve

  expect(mockAsyncFunction).toHaveBeenCalled()
  expect(wrapper.text()).toContain('result')
})
```

### 2. Tests avec Délais

```typescript
it('should handle timing operations', async () => {
  vi.useFakeTimers()

  wrapper = mount(Component)

  await wrapper.find('[data-testid="timer-button"]').trigger('click')

  // Fast-forward time
  vi.advanceTimersByTime(1000)

  expect(wrapper.find('[data-testid="timer-result"]').text()).toBe('Timer done')

  vi.useRealTimers()
})
```

## Patterns de Gestion d'Erreurs

### 1. Tests d'Erreurs

```typescript
it('should handle errors gracefully', async () => {
  const mockFunction = vi.fn().mockRejectedValue(new Error('Test error'))

  wrapper = mount(Component)

  await wrapper.find('[data-testid="error-trigger"]').trigger('click')
  await flushPromises()

  expect(wrapper.find('[data-testid="error-message"]').exists()).toBe(true)
})
```

### 2. Tests de Validation

```typescript
it('should validate input and show errors', async () => {
  wrapper = mount(Component)

  const input = wrapper.find('input[type="text"]')
  await input.setValue('invalid-value')
  await input.trigger('blur')

  expect(wrapper.find('.error-message').text()).toContain('Invalid input')
})
```

## Bonnes Pratiques

### 1. Organisation des Tests

- **Grouper** les tests par fonctionnalité avec `describe()`
- **Nommer** clairement avec des descriptions spécifiques
- **Ordre** logique : setup → action → assertion

### 2. Isolation

- **Reset** tous les mocks dans `beforeEach()`
- **Unmount** les composants dans `afterEach()`
- **Éviter** les dépendances entre tests

### 3. Lisibilité

- **Utiliser** `data-testid` pour les sélecteurs
- **Créer** des helpers pour les patterns répétitifs
- **Commenter** les tests complexes

### 4. Performance

- **Mock** toutes les dépendances externes
- **Éviter** les appels réseau réels
- **Utiliser** `createMountOptions()` pour éviter la duplication

## Exemples d'Usage des Helpers

```typescript
import {
  createMockTrack,
  createMockPlaylist,
  createMockPlayerState,
  setupMockStores,
  flushPromises,
  triggerAndWait,
  expectEmitted
} from '@/tests/utils/testHelpers'

// Factory usage
const track = createMockTrack({ title: 'Custom Track' })
const playlist = createMockPlaylist({ tracks: [track] })

// Store setup
const { mockServerStateStore, mockUnifiedPlaylistStore } = setupMockStores({
  playerState: { is_playing: true }
})

// Event testing
await triggerAndWait(wrapper, '[data-testid="button"]', 'click')
expectEmitted(wrapper, 'event-name', ['expected', 'payload'])
```

---

*Document mis à jour le: 2025-01-28*
*Version: 1.0*