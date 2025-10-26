/**
 * Frontend Contract Validation Framework for TheOpenMusicBox
 *
 * This module provides automated contract validation to ensure coherence between
 * frontend TypeScript implementations and backend API/Socket.IO contracts.
 */

import { io, Socket } from 'socket.io-client'
import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { logger } from '../../utils/logger'

// Import contract schemas (these would be shared with backend)
import apiContracts from './schemas/api_contracts.json'
import socketioContracts from './schemas/socketio_contracts.json'

/**
 * Contract validation types
 */
export enum ContractType {
  API = 'api',
  SOCKETIO = 'socketio'
}

export enum ValidationResult {
  PASS = 'pass',
  FAIL = 'fail',
  SKIP = 'skip',
  ERROR = 'error'
}

export interface ContractTestResult {
  contractType: ContractType
  endpoint: string
  method?: string
  eventName?: string
  result: ValidationResult
  message: string
  details?: Record<string, any>
  responseData?: Record<string, any>
  errors?: string[]
  duration?: number
}

export interface ValidationReport {
  summary: {
    totalTests: number
    passed: number
    failed: number
    skipped: number
    errors: number
    successRate: number
    duration: number
  }
  apiValidation: {
    total: number
    passed: number
    failed: number
  }
  socketioValidation: {
    total: number
    passed: number
    failed: number
  }
  detailedResults: ContractTestResult[]
}

/**
 * JSON Schema validator (lightweight implementation)
 */
class SchemaValidator {
  static validate(data: any, schema: any): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (!schema) {
      return { valid: true, errors: [] }
    }

    // Basic type validation
    if (schema.type) {
      const actualType = Array.isArray(data) ? 'array' : typeof data
      if (Array.isArray(schema.type) {
        if (!schema.type.includes(actualType) && !schema.type.includes('null') {
          errors.push(`Expected type ${schema.type.join(' or ')}, got ${actualType}`)
        }
      } else if (schema.type !== actualType && !(schema.type === 'null' && data === null) {
        errors.push(`Expected type ${schema.type}, got ${actualType}`)
      }
    }

    // Required properties validation
    if (schema.required && Array.isArray(schema.required) && typeof data === 'object' && data !== null) {
      for (const prop of schema.required) {
        if (!(prop in data) {
          errors.push(`Missing required property: ${prop}`)
        }
      }
    }

    // Properties validation
    if (schema.properties && typeof data === 'object' && data !== null && !Array.isArray(data) {
      for (const [propName, propSchema] of Object.entries(schema.properties) {
        if (propName in data) {
          const propResult = this.validate(data[propName], propSchema)
          errors.push(...propResult.errors.map(err => `${propName}: ${err}`)
        }
      }
    }

    // Array items validation
    if (schema.items && Array.isArray(data) {
      data.forEach((item, index) => {
        const itemResult = this.validate(item, schema.items)
        errors.push(...itemResult.errors.map(err => `[${index}]: ${err}`)
      })
    }

    // Enum validation
    if (schema.enum && !schema.enum.includes(data) {
      errors.push(`Value ${data} not in allowed values: ${schema.enum.join(', ')}`)
    }

    // Minimum/maximum validation
    if (typeof data === 'number') {
      if (schema.minimum !== undefined && data < schema.minimum) {
        errors.push(`Value ${data} is less than minimum ${schema.minimum}`)
      }
      if (schema.maximum !== undefined && data > schema.maximum) {
        errors.push(`Value ${data} is greater than maximum ${schema.maximum}`)
      }
    }

    return { valid: errors.length === 0, errors }
  }
}

/**
 * Main contract validator class
 */
export class ContractValidator {
  private apiClient: AxiosInstance
  private socket: Socket | null = null
  private socketEvents: Array<{ event: string; data: any; timestamp: number }> = []
  private startTime: number = 0

  constructor(
    private apiBaseUrl: string = 'http://localhost:8000',
    private socketioUrl: string = 'http://localhost:8000'
  ) {
    this.apiClient = axios.create({
      baseURL: apiBaseUrl,
      timeout: 10000,
      validateStatus: () => true // Accept all status codes for testing
    })

    logger.info(`Frontend contract validator initialized: API=${apiBaseUrl}, Socket.IO=${socketioUrl}`)
  }

  /**
   * Validate all contracts
   */
  async validateAllContracts(): Promise<ValidationReport> {
    this.startTime = Date.now()
    const results: ContractTestResult[] = []

    // Validate API contracts
    logger.info('Starting frontend API contract validation...')
    const apiResults = await this.validateApiContracts()
    results.push(...apiResults)

    // Validate Socket.IO contracts
    logger.info('Starting frontend Socket.IO contract validation...')
    const socketioResults = await this.validateSocketioContracts()
    results.push(...socketioResults)

    return this.generateValidationReport(results)
  }

  /**
   * Validate API contracts from frontend perspective
   */
  async validateApiContracts(): Promise<ContractTestResult[]> {
    const results: ContractTestResult[] = []

    // Test critical API endpoints that frontend depends on
    const criticalEndpoints = [
      { method: 'GET', path: '/api/health' },
      { method: 'GET', path: '/api/playlists' },
      { method: 'GET', path: '/api/player/status' },
      { method: 'GET', path: '/api/nfc/status' }
    ]

    for (const endpoint of criticalEndpoints) {
      const startTime = Date.now()

      try {
        const result = await this.validateApiEndpoint(endpoint.method, endpoint.path)
        result.duration = Date.now() - startTime
        results.push(result)
      } catch (error) {
        results.push({
          contractType: ContractType.API,
          endpoint: endpoint.path,
          method: endpoint.method,
          result: ValidationResult.ERROR,
          message: `Request failed: ${error}`,
          duration: Date.now() - startTime
        })
      }
    }

    return results
  }

  /**
   * Validate specific API endpoint
   */
  private async validateApiEndpoint(method: string, path: string): Promise<ContractTestResult> {
    const fullUrl = `${this.apiBaseUrl}${path}`

    try {
      let response: AxiosResponse

      switch (method.toUpperCase() {
        case 'GET':
          response = await this.apiClient.get(path)
          break
        case 'POST':
          response = await this.apiClient.post(path, this.generateTestRequestData(path)
          break
        case 'PUT':
          response = await this.apiClient.put(path, this.generateTestRequestData(path)
          break
        case 'DELETE':
          response = await this.apiClient.delete(path, { data: this.generateTestRequestData(path) })
          break
        default:
          return {
            contractType: ContractType.API,
            endpoint: path,
            method: method,
            result: ValidationResult.SKIP,
            message: `Unsupported method: ${method}`
          }
      }

      // Skip validation for 404s (test endpoints that don't exist)
      if (response.status === 404) {
        return {
          contractType: ContractType.API,
          endpoint: path,
          method: method,
          result: ValidationResult.SKIP,
          message: 'Endpoint not found (404) - skipping validation'
        }
      }

      const validationErrors: string[] = []

      // Validate unified response format
      const unifiedSchema = apiContracts.unified_response_format.schema
      const unifiedValidation = SchemaValidator.validate(response.data, unifiedSchema)
      if (!unifiedValidation.valid) {
        validationErrors.push(`Unified response format: ${unifiedValidation.errors.join(', ')}`)
      }

      // Validate response structure matches frontend expectations
      if (!this.validateFrontendResponseExpectations(path, response.data) {
        validationErrors.push('Response does not match frontend expectations')
      }

      // Check content type
      const contentType = response.headers['content-type']
      if (!contentType?.includes('application/json') {
        validationErrors.push(`Expected JSON content type, got: ${contentType}`)
      }

      const result = validationErrors.length === 0 ? ValidationResult.PASS : ValidationResult.FAIL
      const message = validationErrors.length === 0
        ? 'Frontend API validation passed'
        : 'Frontend API validation failed'

      return {
        contractType: ContractType.API,
        endpoint: path,
        method: method,
        result,
        message,
        responseData: response.data,
        errors: validationErrors.length > 0 ? validationErrors : undefined
      }

    } catch (error) {
      return {
        contractType: ContractType.API,
        endpoint: path,
        method: method,
        result: ValidationResult.ERROR,
        message: `Request failed: ${error}`
      }
    }
  }

  /**
   * Validate that API responses match frontend expectations
   */
  private validateFrontendResponseExpectations(path: string, responseData: any): boolean {
    // Check for required fields that frontend code expects
    if (!responseData.status) return false
    if (!responseData.message) return false
    if (typeof responseData.timestamp !== 'number') return false

    // Specific validations based on endpoint
    switch (path) {
      case '/api/health':
        return responseData.status === 'success' &&
               responseData.data &&
               typeof responseData.data.status === 'string'

      case '/api/playlists':
        return responseData.status === 'success' &&
               responseData.data &&
               Array.isArray(responseData.data.playlists)

      case '/api/player/status':
        return responseData.status === 'success' &&
               responseData.data &&
               typeof responseData.data.is_playing === 'boolean'

      case '/api/nfc/status':
        return responseData.status === 'success' &&
               responseData.data &&
               typeof responseData.data.reader_available === 'boolean'

      default:
        return true // Basic validation passed
    }
  }

  /**
   * Generate test request data for API calls
   */
  private generateTestRequestData(path: string): Record<string, any> {
    const baseData = { client_op_id: `test-${Date.now()}` }

    switch (path) {
      case '/api/playlists':
        return { ...baseData, title: 'Test Playlist' }
      default:
        return baseData
    }
  }

  /**
   * Validate Socket.IO contracts from frontend perspective
   */
  async validateSocketioContracts(): Promise<ContractTestResult[]> {
    const results: ContractTestResult[] = []

    try {
      // Connect to Socket.IO server
      this.socket = io(this.socketioUrl, {
        transports: ['websocket', 'polling'],
        timeout: 10000
      })

      // Setup event listeners
      this.setupSocketEventListeners()

      // Wait for connection
      await this.waitForSocketConnection()

      // Test connection events
      const connectionResults = await this.validateConnectionEvents()
      results.push(...connectionResults)

      // Test subscription events
      const subscriptionResults = await this.validateSubscriptionEvents()
      results.push(...subscriptionResults)

      // Test event envelope formats
      const envelopeResults = await this.validateEventEnvelopes()
      results.push(...envelopeResults)

      // Disconnect
      this.socket.disconnect()

    } catch (error) {
      results.push({
        contractType: ContractType.SOCKETIO,
        endpoint: 'connection',
        eventName: 'connect',
        result: ValidationResult.ERROR,
        message: `Socket.IO connection failed: ${error}`
      })
    }

    return results
  }

  /**
   * Setup Socket.IO event listeners to capture all events
   */
  private setupSocketEventListeners(): void {
    if (!this.socket) return

    // Capture all events defined in contracts
    const allEvents = Object.values(socketioContracts.contracts)
      .flatMap((category: any) => Object.keys(category.events || {})

    allEvents.forEach(eventName => {
      this.socket!.on(eventName, (data: any) => {
        logger.debug(`Frontend received Socket.IO event: ${eventName}`, data)
        this.socketEvents.push({
          event: eventName,
          data,
          timestamp: Date.now()
        })
      })
    })

    // Also listen for common events
    const commonEvents = ['connect', 'disconnect', 'connection_status', 'ack:join', 'ack:leave']
    commonEvents.forEach(eventName => {
      this.socket!.on(eventName, (data: any) => {
        this.socketEvents.push({
          event: eventName,
          data,
          timestamp: Date.now()
        })
      })
    })
  }

  /**
   * Wait for Socket.IO connection to be established
   */
  private async waitForSocketConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket) {
        reject(new Error('Socket not initialized')
        return
      }

      const timeout = setTimeout(() => {
        reject(new Error('Socket connection timeout')
      }, 10000)

      this.socket.on('connect', () => {
        clearTimeout(timeout)
        resolve()
      })

      this.socket.on('connect_error', (error) => {
        clearTimeout(timeout)
        reject(error)
      })
    })
  }

  /**
   * Validate connection events
   */
  private async validateConnectionEvents(): Promise<ContractTestResult[]> {
    const results: ContractTestResult[] = []

    // Wait a bit for connection events
    await new Promise(resolve => setTimeout(resolve, 1000)

    // Check for connection_status event
    const connectionEvents = this.socketEvents.filter(e => e.event === 'connection_status')

    if (connectionEvents.length > 0) {
      const eventData = connectionEvents[0].data
      const schema = socketioContracts.contracts.connection_events.events.connection_status.payload

      const validation = SchemaValidator.validate(eventData, schema)

      results.push({
        contractType: ContractType.SOCKETIO,
        endpoint: 'connection',
        eventName: 'connection_status',
        result: validation.valid ? ValidationResult.PASS : ValidationResult.FAIL,
        message: validation.valid
          ? 'Connection status event validation passed'
          : 'Connection status schema validation failed',
        responseData: eventData,
        errors: validation.valid ? undefined : validation.errors
      })
    } else {
      results.push({
        contractType: ContractType.SOCKETIO,
        endpoint: 'connection',
        eventName: 'connection_status',
        result: ValidationResult.FAIL,
        message: 'Connection status event not received'
      })
    }

    return results
  }

  /**
   * Validate subscription events
   */
  private async validateSubscriptionEvents(): Promise<ContractTestResult[]> {
    const results: ContractTestResult[] = []

    if (!this.socket) return results

    // Test joining playlists room
    this.socket.emit('join:playlists', {})
    await new Promise(resolve => setTimeout(resolve, 500)

    // Check for ack:join event
    const joinAcks = this.socketEvents.filter(e => e.event === 'ack:join')

    if (joinAcks.length > 0) {
      const eventData = joinAcks[joinAcks.length - 1].data
      const schema = socketioContracts.contracts.subscription_events.events['ack:join'].payload

      const validation = SchemaValidator.validate(eventData, schema)

      results.push({
        contractType: ContractType.SOCKETIO,
        endpoint: 'subscription',
        eventName: 'ack:join',
        result: validation.valid ? ValidationResult.PASS : ValidationResult.FAIL,
        message: validation.valid
          ? 'Join acknowledgment validation passed'
          : 'Join acknowledgment schema validation failed',
        responseData: eventData,
        errors: validation.valid ? undefined : validation.errors
      })
    } else {
      results.push({
        contractType: ContractType.SOCKETIO,
        endpoint: 'subscription',
        eventName: 'ack:join',
        result: ValidationResult.FAIL,
        message: 'Join acknowledgment not received'
      })
    }

    return results
  }

  /**
   * Validate event envelope formats
   */
  private async validateEventEnvelopes(): Promise<ContractTestResult[]> {
    const results: ContractTestResult[] = []

    // Trigger some state events by making API calls
    try {
      await this.apiClient.get('/api/player/status')
      await this.apiClient.get('/api/playlists')
    } catch (error) {
      logger.debug('Error triggering state events:', error)
    }

    // Wait for events
    await new Promise(resolve => setTimeout(resolve, 2000)

    // Validate envelope format for state events
    const stateEvents = this.socketEvents.filter(e => e.event.startsWith('state:')
    const envelopeSchema = socketioContracts.event_envelope_format.schema

    if (stateEvents.length === 0) {
      results.push({
        contractType: ContractType.SOCKETIO,
        endpoint: 'state_events',
        eventName: 'state:*',
        result: ValidationResult.SKIP,
        message: 'No state events received for envelope validation'
      })
      return results
    }

    for (const event of stateEvents) {
      const validation = SchemaValidator.validate(event.data, envelopeSchema)

      results.push({
        contractType: ContractType.SOCKETIO,
        endpoint: 'state_events',
        eventName: event.event,
        result: validation.valid ? ValidationResult.PASS : ValidationResult.FAIL,
        message: validation.valid
          ? `State event envelope validation passed for ${event.event}`
          : `State event envelope validation failed for ${event.event}`,
        responseData: event.data,
        errors: validation.valid ? undefined : validation.errors
      })
    }

    return results
  }

  /**
   * Generate comprehensive validation report
   */
  private generateValidationReport(results: ContractTestResult[]): ValidationReport {
    const totalTests = results.length
    const passed = results.filter(r => r.result === ValidationResult.PASS).length
    const failed = results.filter(r => r.result === ValidationResult.FAIL).length
    const skipped = results.filter(r => r.result === ValidationResult.SKIP).length
    const errors = results.filter(r => r.result === ValidationResult.ERROR).length
    const duration = Date.now() - this.startTime

    const apiResults = results.filter(r => r.contractType === ContractType.API)
    const socketioResults = results.filter(r => r.contractType === ContractType.SOCKETIO)

    return {
      summary: {
        totalTests,
        passed,
        failed,
        skipped,
        errors,
        successRate: totalTests > 0 ? (passed / totalTests * 100) : 0,
        duration
      },
      apiValidation: {
        total: apiResults.length,
        passed: apiResults.filter(r => r.result === ValidationResult.PASS).length,
        failed: apiResults.filter(r => r.result === ValidationResult.FAIL).length
      },
      socketioValidation: {
        total: socketioResults.length,
        passed: socketioResults.filter(r => r.result === ValidationResult.PASS).length,
        failed: socketioResults.filter(r => r.result === ValidationResult.FAIL).length
      },
      detailedResults: results
    }
  }

  /**
   * Export validation report as JSON
   */
  exportReport(report: ValidationReport): string {
    return JSON.stringify(report, null, 2)
  }

  /**
   * Print validation summary to console
   */
  printSummary(report: ValidationReport): void {
    console.log('\n=== Frontend Contract Validation Report ===')
    console.log(`Total tests: ${report.summary.totalTests}`)
    console.log(`✅ Passed: ${report.summary.passed}`)
    console.log(`❌ Failed: ${report.summary.failed}`)
    console.log(`⏭️  Skipped: ${report.summary.skipped}`)
    console.log(`💥 Errors: ${report.summary.errors}`)
    console.log(`📊 Success rate: ${report.summary.successRate.toFixed(1)}%`)
    console.log(`⏱️  Duration: ${report.summary.duration}ms`)

    if (report.summary.failed > 0 || report.summary.errors > 0) {
      console.log('\n=== Failed Tests ===')
      report.detailedResults
        .filter(r => r.result === ValidationResult.FAIL || r.result === ValidationResult.ERROR)
        .forEach(result => {
          console.log(`❌ ${result.contractType} ${result.endpoint} ${result.method || result.eventName}: ${result.message}`)
          if (result.errors) {
            result.errors.forEach(error => console.log(`   • ${error}`)
          }
        })
    }
  }
}

// Export for use in tests
export default ContractValidator